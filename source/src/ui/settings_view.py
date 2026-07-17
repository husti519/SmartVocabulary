from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog,
                             QLineEdit, QPushButton, QFrame, QMessageBox, QComboBox, 
                             QRadioButton, QButtonGroup, QTextEdit, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, Signal, QTimer
import os
import re
from google import genai
from ..utils.config_manager import ConfigManager
from ..backend.crawler import GeminiWorker
from ..utils.logger import log_exception
from .components.focus_button import FocusButton
from ..backend.supabase_client import SupabaseManager

class ShortcutLineEdit(QLineEdit):
    """A QLineEdit that captures key presses and displays the key name with visual feedback."""
    BASE_STYLE = "padding: 10px; border: 1px solid #ced4da; border-radius: 4px; background-color: white; color: black; font-size: 14px;"
    ACTIVE_STYLE = "padding: 10px; border: 2px solid #add8e6; border-radius: 4px; background-color: white; color: black; font-size: 14px; font-weight: bold;"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignCenter)
        self.setPlaceholderText("키 입력...")
        self.setStyleSheet(self.BASE_STYLE)
        self.key_name = ""
        self.key_code = 0

    def focusInEvent(self, event):
        self.setStyleSheet(self.ACTIVE_STYLE)
        self.selectAll()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setStyleSheet(self.BASE_STYLE)
        self.deselect()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        
        # Ignore modifier keys alone
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return

        # Special case: Delete or Backspace to clear shortcut
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.key_name = "None"
            self.key_code = 0
            self.setText(self.key_name)
            self.clearFocus()
            return

        self.key_code = key
        self.key_name = ConfigManager.key_to_string(key)
        
        if self.key_name:
            self.setText(self.key_name)
            self.clearFocus()

class SettingsView(QWidget):
    request_logout = Signal()
    request_change_password = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self.is_busy = False # True when AI tasks are running
        self.setup_ui()
        #self.load_settings()

    def set_busy(self, busy):
        self.is_busy = busy
        self.btn_save_global.setEnabled(not busy)

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Title Container with Global Save Button
        self.title_container = QWidget()
        self.title_container.setStyleSheet("background-color: #F7F8FA;")
        self.title_layout = QHBoxLayout(self.title_container)
        self.title_layout.setContentsMargins(40, 30, 40, 30)
        self.title_layout.setSpacing(10)

        title = QLabel("환경설정")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        self.title_layout.addWidget(title)
        
        self.title_layout.addStretch()
        
        self.btn_save_global = QPushButton("설정 저장")
        self.btn_save_global.setFixedSize(120, 45)
        self.btn_save_global.setCursor(Qt.PointingHandCursor)
        self.btn_save_global.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.btn_save_global.clicked.connect(self.handle_global_save)
        self.title_layout.addWidget(self.btn_save_global)

        self.main_layout.addWidget(self.title_container)

        # Central Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #F7F8FA; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #F7F8FA;")

        # Central Layout
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(40, 0, 40, 20)
        self.layout.setSpacing(20)

        # SECTION 1: AI API & Model Settings
        self.api_group_frame = QFrame()
        self.api_group_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #e9ecef; }
            QLabel { color: #2c3e50; border: none; background: transparent; font-weight: bold; }
        """)
        api_group_layout = QVBoxLayout(self.api_group_frame)
        api_group_layout.setContentsMargins(25, 25, 25, 25)
        api_group_layout.setSpacing(20)

        section1_title = QLabel("🤖 Gemini API Key 설정")
        section1_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #3498db;")
        api_group_layout.addWidget(section1_title)

        common_info_desc = QLabel("영단어 입력 시 단어 뜻, 발음기호, 예문을 자동으로 생성하는 Auto-fill 기능을 사용하려면 "
                                  "Google AI Studio에서 발급받은 API Key가 필요합니다.")
        common_info_desc.setStyleSheet("color: #34495e; font-size: 14px; font-weight: 500;")
        common_info_desc.setWordWrap(True)
        api_group_layout.addWidget(common_info_desc)

        help_label = QLabel("<a href='https://aistudio.google.com/app/apikey' style='color: #3498db;'>API Key 발급받으러 가기 (Google AI Studio)</a>")
        help_label.setOpenExternalLinks(True)
        help_label.setStyleSheet("border: none; font-size: 13px; background: transparent;")
        help_label.setMinimumHeight(25)
        api_group_layout.addWidget(help_label)

        mode_layout = QHBoxLayout()
        self.radio_personal = QRadioButton("개인용 컴퓨터 (환경변수 사용)")
        self.radio_shared = QRadioButton("공용 컴퓨터 (수동 입력/휘발성)")
        radio_style = """
            QRadioButton { font-size: 15px; font-weight: bold; color: #2c3e50; spacing: 10px; background: transparent; }
            QRadioButton::indicator { width: 18px; height: 18px; }
            QRadioButton::indicator:unchecked { border: 2px solid #bdc3c7; border-radius: 9px; background-color: white; }
            QRadioButton::indicator:checked { border: 2px solid #3498db; border-radius: 9px; background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #3498db, stop:0.4 #3498db, stop:0.5 white, stop:1.0 white); }
        """
        self.radio_personal.setStyleSheet(radio_style)
        self.radio_shared.setStyleSheet(radio_style)
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.addButton(self.radio_personal)
        self.mode_button_group.addButton(self.radio_shared)
        mode_layout.addWidget(self.radio_personal)
        mode_layout.addWidget(self.radio_shared)
        mode_layout.addStretch()
        api_group_layout.addLayout(mode_layout)

        self.api_inputs_widget = QWidget()
        api_inputs_layout = QVBoxLayout(self.api_inputs_widget)
        api_inputs_layout.setContentsMargins(0, 0, 0, 0)
        api_inputs_layout.setSpacing(10)
        input_style = "QLineEdit { padding: 10px; border: 1px solid #ced4da; border-radius: 4px; background-color: white; color: black; font-size: 14px; }"
        
        self.personal_input_container = QWidget()
        self.personal_input_container.setStyleSheet("QWidget { background-color: white; }")
        p_layout = QVBoxLayout(self.personal_input_container)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.addWidget(QLabel("환경변수 이름 (기본값: GOOGLE_API_KEY):"))
        self.env_name_input = QLineEdit()
        self.env_name_input.setPlaceholderText("예: GOOGLE_API_KEY")
        self.env_name_input.setStyleSheet(input_style)
        p_layout.addWidget(self.env_name_input)
        api_inputs_layout.addWidget(self.personal_input_container)

        self.shared_input_container = QWidget()
        self.shared_input_container.setStyleSheet("QWidget { background-color: white; }")
        s_layout = QVBoxLayout(self.shared_input_container)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.addWidget(QLabel("프로그램 메모리에만 저장되는 휘발성 설정입니다. 프로그램 재실행 시 다시 설정해야 합니다."))
        
        key_hbox = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("API Key를 입력하세요")
        self.key_input.setStyleSheet(input_style)
        key_hbox.addWidget(self.key_input)

        self.btn_toggle_key = QPushButton("보기")
        self.btn_toggle_key.setCheckable(True)
        self.btn_toggle_key.clicked.connect(self.toggle_key_visibility)
        self.btn_toggle_key.setStyleSheet("QPushButton { padding: 8px 15px; background-color: #3498db; border: 1px solid #ced4da; border-radius: 4px; font-weight: bold; }")
        key_hbox.addWidget(self.btn_toggle_key)
        s_layout.addLayout(key_hbox)
        api_inputs_layout.addWidget(self.shared_input_container)
        api_group_layout.addWidget(self.api_inputs_widget)

        model_vbox = QVBoxLayout()
        model_vbox.setSpacing(5)
        model_vbox.addWidget(QLabel("사용할 AI 모델 선택:"))
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #E6E8EB;
                border-radius: 8px;
                padding: 5px 30px 5px 10px; 
                background-color: white;
                color: #2c3e50;
                min-height: 30px;
            }
        """)
        model_vbox.addWidget(self.model_combo)

        self.btn_test_conn = FocusButton("연결 테스트")
        self.btn_test_conn.setStyleSheet("QPushButton { padding: 12px; background-color: #f39c12; color: white; border-radius: 6px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #cf840e; }")
        self.btn_test_conn.clicked.connect(self.test_api_key)
        self.btn_test_conn.enter_pressed.connect(self.test_api_key)
        api_group_layout.addWidget(self.btn_test_conn)

        # Guidance text
        guidance_label = QLabel("# Auto-fill 기능에는 경량 모델인 flash-lite나 flash 모델을 권장합니다. 더 높은 생성 품질을 원한다면 고성능 모델을 선택하세요.")
        guidance_label.setStyleSheet("color: #7f8c8d; font-size: 12px; padding-top: 5px;")
        model_vbox.addWidget(guidance_label)

        api_group_layout.addLayout(model_vbox)

        self.layout.addWidget(self.api_group_frame)

        # SECTION 2: Prompt Tool
        self.prompt_group_frame = QFrame()
        self.prompt_group_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #e9ecef; }
            QLabel { color: #2c3e50; border: none; background: transparent; font-weight: bold; }
        """)
        prompt_group_layout = QVBoxLayout(self.prompt_group_frame)
        prompt_group_layout.setContentsMargins(25, 25, 25, 25)
        prompt_group_layout.setSpacing(20)

        section2_title = QLabel("✨ Auto-fill 프롬프트 커스터마이징")
        section2_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #27ae60;")
        prompt_group_layout.addWidget(section2_title)
        prompt_group_layout.addWidget(QLabel("Auto-fill 기능 사용시 단어 뜻, 예문, 발음 기호 등의 생성 결과를 자신이 원하는 형식대로 나오도록 수정할 수 있습니다."))
        
        prompt_filename_layout = QHBoxLayout()                
        prompt_filename_layout.addWidget(QLabel("프롬프트 템플릿 수정"))
        self.prompt_filename_edit = QLineEdit()
        self.prompt_filename_edit.setPlaceholderText("ex) gemini_prompt.txt")
        self.prompt_filename_edit.setStyleSheet(input_style)
        prompt_filename_layout.addWidget(self.prompt_filename_edit)
        
        self.btn_prompt_file_explorer = QPushButton("...")
        self.btn_prompt_file_explorer.setFixedSize(45, 30)
        self.btn_prompt_file_explorer.clicked.connect(self.on_prompt_file_explorer)
        self.btn_prompt_file_explorer.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        prompt_filename_layout.addWidget(self.btn_prompt_file_explorer)
        prompt_group_layout.addLayout(prompt_filename_layout)
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setStyleSheet("QTextEdit { padding: 12px; border: 1px solid #ced4da; border-radius: 6px; font-family: 'Consolas', monospace; font-size: 13px; color: #333; background-color: #fff; }")
        self.prompt_edit.setMinimumHeight(250)
        prompt_group_layout.addWidget(self.prompt_edit)

        test_input_layout = QHBoxLayout()
        self.test_word_input = QLineEdit()
        self.test_word_input.setPlaceholderText("테스트할 영단어 입력")
        self.test_word_input.setStyleSheet(input_style)
        self.test_word_input.returnPressed.connect(self.run_prompt_test)
        test_input_layout.addWidget(self.test_word_input, 3)
        
        self.btn_run_test = FocusButton("테스트 실행")
        self.btn_run_test.setStyleSheet("QPushButton { padding: 12px 20px; background-color: #9b59b6; color: white; border-radius: 6px; font-weight: bold; } QPushButton:hover { background-color: #8e44ad; }")
        self.btn_run_test.clicked.connect(self.run_prompt_test)
        self.btn_run_test.enter_pressed.connect(self.run_prompt_test)
        test_input_layout.addWidget(self.btn_run_test, 1)
        prompt_group_layout.addLayout(test_input_layout)

        prompt_group_layout.addWidget(QLabel("테스트 결과:"))
        self.test_result_output = QTextEdit()
        self.test_result_output.setReadOnly(True)
        self.test_result_output.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: black;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                padding: 10px;                                              
            }
        """)
        
        self.test_result_output.setMinimumHeight(150)
        prompt_group_layout.addWidget(self.test_result_output)

        self.layout.addWidget(self.prompt_group_frame)

        # SECTION 3: Keyboard Shortcuts
        self.shortcut_group_frame = QFrame()
        self.shortcut_group_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #e9ecef; }
            QLabel { color: #2c3e50; border: none; background: transparent; font-weight: bold; }
        """)
        shortcut_group_layout = QVBoxLayout(self.shortcut_group_frame)
        shortcut_group_layout.setContentsMargins(25, 25, 25, 25)
        shortcut_group_layout.setSpacing(15)

        section_shortcuts_title = QLabel("⌨️ 학습 단축키 설정")
        section_shortcuts_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #34495e;")
        shortcut_group_layout.addWidget(section_shortcuts_title)

        shortcut_desc = QLabel("학습 모드(단어 암기 Test)에서 사용할 단축키를 설정합니다.(Del 키를 누르면 해당 단축키를 사용하지 않습니다.)")
        shortcut_desc.setStyleSheet("color: #7f8c8d; font-size: 14px; font-weight: 500;")
        shortcut_group_layout.addWidget(shortcut_desc)

        self.shortcut_group_widget = QWidget()
        self.shortcut_group_widget.setStyleSheet("QWidget { background-color: transparent; }")
        self.shortcut_group_widget.setFixedWidth(700)
        shortcut_input_grid = QGridLayout(self.shortcut_group_widget)
        shortcut_input_grid.setSpacing(20)

        # Prev Shortcut
        prev_hbox = QHBoxLayout()
        prev_hbox.addWidget(QLabel("이전 카드 (Prev):"))
        self.shortcut_prev_input = ShortcutLineEdit()
        self.shortcut_prev_input.setFixedWidth(80)
        self.shortcut_prev_input.setStyleSheet(input_style)
        prev_hbox.addWidget(self.shortcut_prev_input)
        shortcut_input_grid.addLayout(prev_hbox, 0, 0)

        # Next Shortcut
        next_hbox = QHBoxLayout()
        next_hbox.addWidget(QLabel("다음 카드 (Next):"))
        self.shortcut_next_input = ShortcutLineEdit()
        self.shortcut_next_input.setFixedWidth(80)
        self.shortcut_next_input.setStyleSheet(input_style)
        next_hbox.addWidget(self.shortcut_next_input)
        shortcut_input_grid.addLayout(next_hbox, 0, 1)

        # Flip Shortcut
        flip_hbox = QHBoxLayout()
        flip_hbox.addWidget(QLabel("카드 뒤집기 (Flip):"))
        self.shortcut_flip_input = ShortcutLineEdit()
        self.shortcut_flip_input.setFixedWidth(80)
        self.shortcut_flip_input.setStyleSheet(input_style)
        flip_hbox.addWidget(self.shortcut_flip_input)
        shortcut_input_grid.addLayout(flip_hbox, 0, 2)

        # TTS Shortcut
        tts_hbox = QHBoxLayout()
        tts_hbox.addWidget(QLabel("발음 듣기 (TTS):"))
        self.shortcut_tts_input = ShortcutLineEdit()
        self.shortcut_tts_input.setFixedWidth(80)
        self.shortcut_tts_input.setStyleSheet(input_style)
        tts_hbox.addWidget(self.shortcut_tts_input)
        shortcut_input_grid.addLayout(tts_hbox, 1, 0)

        # Star Shortcut
        star_hbox = QHBoxLayout()
        star_hbox.addWidget(QLabel("중요 표시 (Star):"))
        self.shortcut_star_input = ShortcutLineEdit()
        self.shortcut_star_input.setFixedWidth(80)
        self.shortcut_star_input.setStyleSheet(input_style)
        star_hbox.addWidget(self.shortcut_star_input)
        shortcut_input_grid.addLayout(star_hbox, 1, 1)

        #shortcut_group_layout.addLayout(shortcut_input_grid)
        shortcut_group_layout.addWidget(self.shortcut_group_widget)
        self.layout.addWidget(self.shortcut_group_frame)

        # SECTION 4: Account Management
        self.account_group_frame = QFrame()
        self.account_group_frame.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #e9ecef; }
            QLabel { color: #2c3e50; border: none; background: transparent; font-weight: bold; }
        """)
        account_group_layout = QVBoxLayout(self.account_group_frame)
        account_group_layout.setContentsMargins(25, 25, 25, 25)
        account_group_layout.setSpacing(15)

        section3_title = QLabel("🔒 계정 관리")
        section3_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c;")
        account_group_layout.addWidget(section3_title)

        withdrawal_desc = QLabel("회원 탈퇴 시 모든 단어장과 학습 데이터가 영구히 삭제되며 복구할 수 없습니다.")
        withdrawal_desc.setStyleSheet("color: #7f8c8d; font-size: 13px; font-weight: 500;")
        account_group_layout.addWidget(withdrawal_desc)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_change_pw = QPushButton("비밀번호 변경")
        self.btn_change_pw.setFixedWidth(150)
        self.btn_change_pw.setCursor(Qt.PointingHandCursor)
        self.btn_change_pw.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #3498db;
                border: 1px solid #3498db;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f7ff;
            }
        """)
        self.btn_change_pw.clicked.connect(self.request_change_password.emit)
        btn_layout.addWidget(self.btn_change_pw)

        self.btn_withdraw = QPushButton("회원 탈퇴")
        self.btn_withdraw.setFixedWidth(150)
        self.btn_withdraw.setCursor(Qt.PointingHandCursor)
        self.btn_withdraw.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #e74c3c;
                border: 1px solid #e74c3c;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fdf2f2;
            }
        """)
        self.btn_withdraw.clicked.connect(self.handle_withdraw)
        btn_layout.addWidget(self.btn_withdraw)
        
        btn_layout.addStretch()
        account_group_layout.addLayout(btn_layout)

        self.layout.addWidget(self.account_group_frame)

        self.layout.addStretch()
        
        self.scroll.setWidget(self.container)
        self.main_layout.addWidget(self.scroll)

        self.radio_personal.toggled.connect(self.update_view_visibility)
        self.radio_shared.toggled.connect(self.update_view_visibility)

    def handle_withdraw(self):
        reply = QMessageBox.question(
            self, "회원 탈퇴",
            "정말로 탈퇴하시겠습니까?\n모든 데이터가 삭제되며 이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            res = self.db.withdraw_user()
            if res.get("success"):
                QMessageBox.information(self, "탈퇴 완료", "회원 탈퇴가 완료되었습니다. 이용해 주셔서 감사합니다.")
                self.request_logout.emit()
            else:
                QMessageBox.critical(self, "오류", f"탈퇴 처리 중 오류가 발생했습니다: {res.get('error')}")

    def handle_global_save(self):
        if self.is_busy:
            QMessageBox.warning(self, "Action Disabled", "Please wait for the current AI task to complete.")
            return
        
        # Unified save for API settings, prompt file, and shortcuts.
        model_name = self.model_combo.currentText()
        
        # Save API Settings
        if self.radio_personal.isChecked():
            env_name = self.env_name_input.text().strip()
            api_key = os.environ.get(env_name, "")
            ConfigManager.save_env_var_name(env_name, sync=False)
            ConfigManager.save_app_mode('personal', sync=False)
            ConfigManager.set_api_key(api_key)
            if model_name:
                ConfigManager.save_model_name(model_name, persist=True, sync=False)
        else:
            api_key = self.key_input.text().strip()
            ConfigManager.save_app_mode('shared', sync=False)
            ConfigManager.set_api_key(api_key)
            if model_name:
                ConfigManager.save_model_name(model_name, persist=False, sync=False)

        # Save Shortcuts
        tts_key = self.shortcut_tts_input.key_code
        star_key = self.shortcut_star_input.key_code
        prev_key = self.shortcut_prev_input.key_code
        next_key = self.shortcut_next_input.key_code
        flip_key = self.shortcut_flip_input.key_code
        
        ConfigManager.save_shortcuts({
            'tts': tts_key, 
            'star': star_key,
            'prev': prev_key,
            'next': next_key,
            'flip': flip_key
        }, sync=False)

        # Sync all changes to disk
        ConfigManager.sync()

        # Save Prompt File
        prompt_success = False
        prompt_path = self.prompt_filename_edit.text().strip()
        
        if prompt_path:
            prompt_path = ConfigManager.get_resolved_prompt_filepath(prompt_path)
            
            try:
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(self.prompt_edit.toPlainText())
                    
                ConfigManager.save_prompt_filepath(prompt_path, sync=True)
                prompt_success = True
            except Exception as e:
                log_exception("SettingsView.handle_global_save", "Failed to save prompt", e)
                QMessageBox.critical(self, "오류", f"프롬프트 저장 실패: {e}")
        else:
            prompt_success = True

        if prompt_success:
            QMessageBox.information(self, "성공", "모든 설정이 저장되었습니다.")

    def load_prompt_file(self, filepath: str = ""):
        configured_path = filepath or ConfigManager.get_prompt_filepath()
        prompt_path = ConfigManager.get_resolved_prompt_filepath(configured_path)
        
        self.prompt_filename_edit.setText(
            filepath or ConfigManager.get_prompt_filepath() or ConfigManager.DEFAULT_PROMPT_FILENAME
        )
        
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    self.prompt_edit.setPlainText(f.read())
            except Exception as e:
                log_exception("SettingsView.load_prompt_file", "Failed to load prompt", e)
                QMessageBox.critical(self, "오류", f"프롬프트 로드 실패: {e}")

    def run_prompt_test(self):
        word = self.test_word_input.text().strip()
        if not word:
            QMessageBox.warning(self, "경고", "테스트할 단어를 입력하세요.")
            return
        
        api_key = ""
        if self.radio_personal.isChecked():
            env_name = self.env_name_input.text().strip()
            api_key = os.environ.get(env_name, "")
            if not api_key:
                QMessageBox.warning(self, "경고", f"환경변수 '{env_name}'을(를) 찾을 수 없습니다.")
                return
        else:
            api_key = self.key_input.text().strip()
            if not api_key:
                QMessageBox.warning(self, "경고", "API Key를 입력해주세요.")
                return
        model_name = self.model_combo.currentText()
        if not model_name:
            QMessageBox.warning(self, "경고", "연결 테스트 후 사용할 모델을 선택해주세요.")
            return

        self.set_busy(True)
        self.btn_run_test.setEnabled(False)
        self.test_result_output.setPlainText("AI 응답을 생성하는 중입니다...")

        # Setup Animation
        self.test_dot_count = 0
        self.btn_run_test.setText("생성 중")
        self.test_timer = QTimer(self)
        self.test_timer.timeout.connect(self.animate_test_button)
        self.test_timer.start(500)

        self.test_worker = GeminiWorker(word, self.prompt_edit.toPlainText(), api_key, model_name)
        self.test_worker.finished.connect(self.on_test_finished)
        self.test_worker.error.connect(self.on_test_error)
        self.test_worker.start()

    def animate_test_button(self):
        self.test_dot_count = (self.test_dot_count + 1) % 4
        dots = "." * self.test_dot_count
        self.btn_run_test.setText(f"생성 중{dots}")

    def stop_test_animation(self):
        if hasattr(self, 'test_timer') and self.test_timer.isActive():
            self.test_timer.stop()
        self.btn_run_test.setText("테스트 실행")
        self.btn_run_test.setEnabled(True)
        self.set_busy(False)

    def on_test_finished(self, result):
        self.stop_test_animation()
        self.test_result_output.setPlainText(result)

    def on_test_error(self, error):
        self.stop_test_animation()
        self.test_result_output.setPlainText(f"테스트 중 에러 발생:\n{error}")
        QMessageBox.critical(self, "Auto-fill Test Error", f"AI response generation failed:\n{error}")

    def update_view_visibility(self):
        is_personal = self.radio_personal.isChecked()
        self.personal_input_container.setVisible(is_personal)
        self.shared_input_container.setVisible(not is_personal)

    def load_settings(self):
        app_mode = ConfigManager.get_app_mode() or 'shared'
        self.model_combo.clear()
        saved_model_name = ConfigManager.get_model_name()
        if saved_model_name:
            self.model_combo.addItem(saved_model_name)

        if app_mode == 'personal':
            self.radio_personal.setChecked(True)
            env_var_name = ConfigManager.get_env_var_name()
            if env_var_name:
                self.env_name_input.setText(env_var_name)

            api_key = os.environ.get(env_var_name)
            if api_key:
                ConfigManager.set_api_key(api_key)
        else:
            self.radio_shared.setChecked(True)
            self.key_input.clear()
            
        self.load_prompt_file()
        
        # Load shortcuts
        shortcuts = ConfigManager.get_shortcuts()
        
        tts_key = shortcuts.get('tts', Qt.Key_Up)
        self.shortcut_tts_input.key_code = tts_key
        self.shortcut_tts_input.setText(ConfigManager.key_to_string(tts_key))
        
        star_key = shortcuts.get('star', Qt.Key_Down)
        self.shortcut_star_input.key_code = star_key
        self.shortcut_star_input.setText(ConfigManager.key_to_string(star_key))

        prev_key = shortcuts.get('prev', Qt.Key_Left)
        self.shortcut_prev_input.key_code = prev_key
        self.shortcut_prev_input.setText(ConfigManager.key_to_string(prev_key))

        next_key = shortcuts.get('next', Qt.Key_Right)
        self.shortcut_next_input.key_code = next_key
        self.shortcut_next_input.setText(ConfigManager.key_to_string(next_key))

        flip_key = shortcuts.get('flip', Qt.Key_Space)
        self.shortcut_flip_input.key_code = flip_key
        self.shortcut_flip_input.setText(ConfigManager.key_to_string(flip_key))

        self.update_view_visibility()

    def toggle_key_visibility(self, checked):
        self.key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.btn_toggle_key.setText("숨기기" if checked else "보기")

    def test_api_key(self):
        if self.radio_personal.isChecked():
            env_name = self.env_name_input.text().strip()
            api_key = os.environ.get(env_name)
            if not api_key:
                QMessageBox.warning(self, "경고", f"환경변수 '{env_name}'을(를) 찾을 수 없습니다.")
                return
        else:
            api_key = self.key_input.text().strip()
            if not api_key:
                QMessageBox.warning(self, "경고", "API Key를 입력해주세요.")
                return
            
        self.btn_test_conn.setEnabled(False)
        self.btn_test_conn.setText("테스트 중...")
        self.set_busy(True)
        try:
            client = genai.Client(api_key=api_key)
            models_iterable = client.models.list()
            flash_lite_models, flash_models, other_models = [], [], []
            for m in models_iterable:
                full_name = getattr(m, 'name', str(m))
                name_lower = full_name.lower()

                # Filter: Gemini only, no previews, and NO versioned suffixes (like -001, -002)
                if 'gemini' in name_lower and 'preview' not in name_lower:
                    # Skip models that end with a version number like -001
                    if re.search(r'-\d{3}$', name_lower):
                        continue

                    display_name = full_name.replace('models/', '')

                    if 'flash-lite' in name_lower:
                        flash_lite_models.append(display_name)
                    elif 'flash' in name_lower:
                        flash_models.append(display_name)
                    else:
                        other_models.append(display_name)

            def version_key(name):
                numbers = re.findall(r'\d+\.?\d*', name)
                return [float(n) for n in numbers] if numbers else [0.0]
            flash_lite_models.sort(key=version_key, reverse=True)
            flash_models.sort(key=version_key, reverse=True)
            other_models.sort()
            final_models = flash_lite_models + flash_models + other_models
            if final_models:
                self.model_combo.clear()
                self.model_combo.addItems(final_models)
                self.model_combo.setCurrentIndex(0)
                QMessageBox.information(self, "성공", f"{len(final_models)}개의 사용 가능한 모델을 찾았습니다.")
            else:
                QMessageBox.warning(self, "주의", "Gemini 모델을 찾을 수 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "실패", f"연결 테스트 실패: {e}")
        finally:
            self.btn_test_conn.setEnabled(True)
            self.btn_test_conn.setText("연결 테스트")
            self.set_busy(False)

    def on_prompt_file_explorer(self):
        prompt_path, _ = QFileDialog.getOpenFileName(self,
            "Select txt File", "", "txt File (*.txt);;All Files (*)")        
        if not prompt_path:
            return
        
        self.load_prompt_file(prompt_path)
