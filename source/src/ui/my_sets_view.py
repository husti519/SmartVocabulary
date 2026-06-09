from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QGridLayout, QStackedWidget, 
                             QMessageBox, QLineEdit, QComboBox, QRadioButton, QDialog)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QPropertyAnimation, QEasingCurve, QSize
from ..backend.supabase_client import SupabaseManager
from ..backend.tts import TTSManager
from .components.set_card import SetCardWidget
from .components.loading_dialog import LoadingDialog
from ..utils.config_manager import ConfigManager
from ..utils.asset_manager import AssetManager

class StudyLoadingWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, db, set_id):
        super().__init__()
        self.db = db
        self.set_id = set_id

    def run(self):
        try:
            cards = self.db.get_cards(self.set_id)
            if cards:
                self.finished.emit(cards)
            else:
                self.finished.emit([])
        except Exception as e:
            self.error.emit(str(e))

class WordSearchResultWidget(QFrame):
    clicked = Signal(dict, str) # set_data, word

    def __init__(self, card_data, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.set_data = card_data.get('card_sets', {})
        self.word = card_data.get('word', '')
        self.setup_ui()

    def setup_ui(self):
        # Remove fixed height to allow vertical growth for long definitions
        self.setMinimumHeight(100)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E6E8EB;
                border-radius: 12px;
            }
            QFrame:hover {
                border: 2px solid #3498db;
                background-color: #F8FBFF;
            }
            QLabel {
                background: transparent;
                color: #2c3e50;
            }
            QLabel#word_label {
                font-size: 18px;
                font-weight: 800;
                color: #2c3e50;
            }
            QLabel#set_label {
                font-size: 13px;
                color: #3498db;
                font-weight: 700;
            }
            QLabel#def_label {
                font-size: 14px;
                color: #586380;
                line-height: 1.3;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.word_label = QLabel(self.word)
        self.word_label.setObjectName("word_label")
        top_row.addWidget(self.word_label)
        
        top_row.addStretch()
        
        set_title = self.set_data.get('title', 'Unknown Set')
        self.set_label = QLabel(f"in {set_title}")
        self.set_label.setObjectName("set_label")
        top_row.addWidget(self.set_label)
        layout.addLayout(top_row)

        definition = self.card_data.get('definition', '')
        self.def_label = QLabel(definition)
        self.def_label.setObjectName("def_label")
        self.def_label.setWordWrap(True) # Enable vertical wrapping
        layout.addWidget(self.def_label)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            if self.set_data:
                self.clicked.emit(self.set_data, self.word)
        super().mouseReleaseEvent(event)

class MoveCardsDialog(QDialog):
    """Dialog to select a target set to move cards to."""
    def __init__(self, current_set_id, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_set_id = current_set_id
        self.selected_set_id = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Move to Set")
        self.setFixedSize(400, 500)
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Select Target Set")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        desc = QLabel("Choose the set where you want to move the selected cards.")
        desc.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Scroll Area for sets
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: 1px solid #E6E8EB; border-radius: 8px;")
        
        content = QWidget()
        self.sets_layout = QVBoxLayout(content)
        self.sets_layout.setAlignment(Qt.AlignTop)
        
        # Load sets and sort alphabetically by title
        sets = self.db.get_card_sets()
        sets.sort(key=lambda x: x.get('title', '').lower())
        
        self.btn_group = []
        
        for s in sets:
            if s['id'] == self.current_set_id:
                continue
            
            btn = QPushButton(s['title'])
            btn.setCheckable(True)
            btn.setFixedHeight(45)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left; padding: 0 15px; border: none; border-radius: 6px;
                    background-color: #f8f9fa; color: #2c3e50; font-size: 14px;
                }
                QPushButton:hover { background-color: #e9ecef; }
                QPushButton:checked { background-color: #3498db; color: white; font-weight: bold; }
            """)
            btn.clicked.connect(lambda checked, sid=s['id'], b=btn: self.on_set_selected(sid, b))
            self.sets_layout.addWidget(btn)
            self.btn_group.append(btn)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(100, 40)
        self.btn_cancel.setStyleSheet("""
            QPushButton { border: 1px solid #ced4da; border-radius: 8px; font-weight: bold; color: #495057; }
            QPushButton:hover { background-color: #f8f9fa; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)

        self.btn_move = QPushButton("Move Cards")
        self.btn_move.setFixedSize(120, 40)
        self.btn_move.setEnabled(False)
        self.btn_move.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #BDC3C7; }
        """)
        self.btn_move.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_move)
        
        layout.addLayout(btn_row)

    def on_set_selected(self, set_id, clicked_btn):
        for btn in self.btn_group:
            if btn != clicked_btn:
                btn.setChecked(False)
        
        self.selected_set_id = set_id if clicked_btn.isChecked() else None
        self.btn_move.setEnabled(self.selected_set_id is not None)

class TermRowWidget(QFrame):
    star_toggled = Signal(str, bool) # card_id, is_starred
    tts_requested = Signal(str) # word
    long_pressed = Signal(dict) # card_data
    selection_changed = Signal()

    def __init__(self, card_data, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.card_id = card_data.get('id')
        self.word = card_data.get('word', '')
        self.definition = card_data.get('definition', '')
        self.is_starred = card_data.get('starred', False)
        
        self.is_selection_mode = False
        self.is_selected = False
        self._long_press_triggered = False
        
        # Long press timer
        self.press_timer = QTimer()
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self.on_long_press_timeout)
        
        self.setup_ui()

    def setup_ui(self):
        # Remove fixed height to allow vertical growth
        self.setMinimumHeight(70)
        self.setStyleSheet("""
            TermRowWidget {
                background-color: white;
                border-bottom: 1px solid #F0F2F5;
            }
            TermRowWidget:hover {
                background-color: #FBFCFE;
            }
            TermRowWidget[selected="true"] {
                background-color: #F0F7FF;
            }
            QLabel#word_label {
                font-size: 17px;
                font-weight: 700;
                color: #2c3e50;
                background-color: transparent;
            }
            QLabel#definition_label {
                font-size: 15px;
                color: #586380;
                line-height: 1.5;
                background-color: transparent;
            }
            QPushButton#icon_btn {
                background-color: #F6F7F9;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                color: #7F8C8D;
            }
            QPushButton#icon_btn:hover {
                background-color: #EDEFF4;
                color: #3498db;
            }
            QPushButton#star_btn {
                background: none;
                border: none;
                font-size: 20px;
                color: #BDC3C7;
            }
            QPushButton#star_btn[starred="true"] {
                color: #f1c40f;
            }
            QPushButton#star_btn:hover {
                color: #f39c12;
            }
            QRadioButton#select_radio {
                spacing: 0px;
            }
            QRadioButton#select_radio::indicator {
                width: 22px;
                height: 22px;
            }
        """)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 30, 15)
        self.main_layout.setSpacing(20)

        # 0. Selection RadioButton (Hidden by default)
        self.checkbox = QRadioButton()
        self.checkbox.setStyleSheet("""
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                spacing: 10px;
                background: transparent;
            }
        """)
        self.checkbox.setAutoExclusive(False)
        self.checkbox.setObjectName("select_radio")
        self.checkbox.setFixedSize(30, 30)
        self.checkbox.setCursor(Qt.PointingHandCursor)
        self.checkbox.hide()
        self.checkbox.clicked.connect(self.on_checkbox_clicked)
        self.main_layout.addWidget(self.checkbox)

        # 1. Word + TTS
        word_container = QWidget()
        word_container.setStyleSheet("background-color: transparent;")
        word_layout = QHBoxLayout(word_container)
        word_layout.setContentsMargins(0, 0, 0, 0)
        word_layout.setSpacing(12)
        word_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.word_label = QLabel(self.word)
        self.word_label.setObjectName("word_label")
        word_layout.addWidget(self.word_label)

        tts_icon = AssetManager.get_icon("icons8-volume-48.png")
        self.btn_tts = QPushButton(tts_icon, "")
        self.btn_tts.setObjectName("icon_btn")
        self.btn_tts.setFixedSize(40, 40)
        self.btn_tts.setIconSize(QSize(22, 22))
        self.btn_tts.setCursor(Qt.PointingHandCursor)
        self.btn_tts.clicked.connect(lambda: self.tts_requested.emit(self.word))
        word_layout.addWidget(self.btn_tts)
        word_layout.addStretch()

        self.main_layout.addWidget(word_container, 2)

        # 2. Definition
        self.def_label = QLabel(self.definition)
        self.def_label.setObjectName("definition_label")
        self.def_label.setWordWrap(True)
        self.def_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.main_layout.addWidget(self.def_label, 4)

        # 3. Star Button
        self.btn_star = QPushButton("★")
        self.btn_star.setObjectName("star_btn")
        self.btn_star.setProperty("starred", "true" if self.is_starred else "false")
        self.btn_star.setFixedSize(40, 40)
        self.btn_star.setCursor(Qt.PointingHandCursor)
        self.btn_star.clicked.connect(self.toggle_star)
        self.main_layout.addWidget(self.btn_star, 0, Qt.AlignTop)

    def on_long_press_timeout(self):
        if not self.is_selection_mode:
            self._long_press_triggered = True
            self.long_pressed.emit(self.card_data)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_selection_mode:
            self._long_press_triggered = False
            self.press_timer.start(1200) # 1.2 seconds
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.press_timer.stop()
        if event.button() == Qt.LeftButton and self.is_selection_mode:
            # Only toggle if this wasn't the release of the click that triggered the mode
            if not self._long_press_triggered:
                if not self.checkbox.underMouse(): # Avoid double toggle if checkbox itself was clicked
                    self.set_selected(not self.is_selected)
        
        self._long_press_triggered = False
        super().mouseReleaseEvent(event)

    def on_checkbox_clicked(self):
        self.set_selected(self.checkbox.isChecked())

    def set_selection_mode(self, enabled):
        self.is_selection_mode = enabled
        self.checkbox.setVisible(enabled)
        if not enabled:
            self.set_selected(False)

    def set_selected(self, selected):
        self.is_selected = selected
        self.checkbox.setChecked(selected)
        self.setProperty("selected", "true" if selected else "false")
        self.setStyle(self.style())
        self.selection_changed.emit()

    def toggle_star(self):
        self.is_starred = not self.is_starred
        self.btn_star.setProperty("starred", "true" if self.is_starred else "false")
        self.btn_star.setStyle(self.btn_star.style())
        self.star_toggled.emit(self.card_id, self.is_starred)

class SetDetailView(QWidget):
    back_requested = Signal()
    study_requested = Signal(dict) # set_data
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    export_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self.tts = TTSManager()
        self.set_data = None
        self.all_cards_original = [] # Store original order from DB
        self.all_cards_raw = [] # Store raw card data for sorting
        self.all_rows = [] # Store references to TermRowWidgets for filtering
        
        self.is_selection_mode = False
        
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(50, 30, 50, 30)
        self.layout.setSpacing(10)

        # Header: Back Button
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Back to My Sets")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #3498db;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        self.btn_back.clicked.connect(self.on_back_clicked)
        header_layout.addWidget(self.btn_back)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Set Title and Study Button Row
        title_row = QHBoxLayout()
        self.title_label = QLabel("Set Title")
        self.title_label.setStyleSheet("font-size: 34px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px;")
        title_row.addWidget(self.title_label)
        
        title_row.addStretch()
        
        self.btn_study = QPushButton("Test")
        self.btn_study.setFixedSize(180, 54)
        self.btn_study.setCursor(Qt.PointingHandCursor)
        self.btn_study.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 27px;
                font-size: 24px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_study.clicked.connect(lambda: self.study_requested.emit(self.set_data))
        title_row.addWidget(self.btn_study)
        self.layout.addLayout(title_row)

        # Header Row for Terms and Management Buttons
        terms_header_layout = QHBoxLayout()
                
        # Sort Row
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("font-size: 13px; color: #7f8c8d; font-weight: 600;")
        terms_header_layout.addWidget(sort_label)

        self.sort_box = QComboBox()
        self.sort_box.addItems(["Original", "Alphabetical (A-Z)", "Alphabetical (Z-A)"])
        self.sort_box.setFixedSize(170, 36)
        self.sort_box.setStyleSheet("""
            QComboBox {
                border: 1px solid #E6E8EB;
                border-radius: 6px;
                padding: 2px 25px 2px 10px;
                background-color: white;
                color: #2c3e50;
            }
        """)
        
        self.sort_box.currentIndexChanged.connect(self.on_sort_changed)
        terms_header_layout.addWidget(self.sort_box)
        terms_header_layout.addStretch()
        
        self.count_label = QLabel("0 terms")
        self.count_label.setStyleSheet("color: black; font-size: 16px; font-weight: 500;")
        terms_header_layout.addWidget(self.count_label)
        terms_header_layout.addStretch()

        self.btn_edit_set = QPushButton("✏️ Edit")
        self.btn_edit_set.setCursor(Qt.PointingHandCursor)
        self.btn_edit_set.setStyleSheet("""
            QPushButton { 
                background: none; border: 1px solid #ced4da; border-radius: 6px; 
                padding: 5px 12px; color: #2c3e50; font-weight: bold; font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover { background-color: #f8f9fa; border-color: #3498db; color: #3498db; }
        """)
        self.btn_edit_set.clicked.connect(lambda: self.edit_requested.emit(self.set_data))
        terms_header_layout.addWidget(self.btn_edit_set)

        # Export, Edit and Delete buttons for the set
        self.btn_export_set = QPushButton("📤 Export")
        self.btn_export_set.setCursor(Qt.PointingHandCursor)
        self.btn_export_set.setStyleSheet("""
            QPushButton { 
                background: none; border: 1px solid #ced4da; border-radius: 6px; 
                padding: 5px 12px; color: #2c3e50; font-weight: bold; font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover { background-color: #f8f9fa; border-color: #3498db; color: #3498db; }
        """)
        self.btn_export_set.clicked.connect(lambda: self.export_requested.emit(self.set_data))
        terms_header_layout.addWidget(self.btn_export_set)

        self.btn_delete_set = QPushButton("🗑️ Delete")
        self.btn_delete_set.setCursor(Qt.PointingHandCursor)
        self.btn_delete_set.setStyleSheet("""
            QPushButton { 
                background: none; border: 1px solid #ced4da; border-radius: 6px; 
                padding: 5px 12px; color: #7f8c8d; font-weight: bold; font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover { background-color: #fff5f5; border-color: #e74c3c; color: #e74c3c; }
        """)
        self.btn_delete_set.clicked.connect(lambda: self.delete_requested.emit(self.set_data))
        terms_header_layout.addWidget(self.btn_delete_set)

        self.layout.addLayout(terms_header_layout)

        # Local Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find a term in this set...")
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E6E8EB;
                border-radius: 8px;
                padding: 0 15px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
            }
            QLineEdit:focus { border: 1px solid #3498db; }
        """)
        self.search_input.textChanged.connect(self.filter_terms)
        self.layout.addWidget(self.search_input)

        # # Sort Row
        # sort_row = QHBoxLayout()
        # sort_label = QLabel("Sort by:")
        # sort_label.setStyleSheet("font-size: 13px; color: #7f8c8d; font-weight: 600;")
        # sort_row.addWidget(sort_label)

        # self.sort_box = QComboBox()
        # self.sort_box.addItems(["Original", "Alphabetical (A-Z)", "Alphabetical (Z-A)"])
        # self.sort_box.setFixedSize(180, 36)
        # self.sort_box.setStyleSheet("""
        #     QComboBox {
        #         border: 1px solid #E6E8EB;
        #         border-radius: 6px;
        #         padding: 2px 25px 2px 10px;
        #         background-color: white;
        #         color: #2c3e50;
        #         font-size: 13px;
        #     }
        # """)
        
        # self.sort_box.currentIndexChanged.connect(self.on_sort_changed)
        # sort_row.addWidget(self.sort_box)
        # sort_row.addStretch()
        # self.layout.addLayout(sort_row)

        # Setup Multi-Select Toolbar (Shared logic from MySetsView)
        self.setup_multi_select_toolbar()

        # Terms List Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: 1px solid #E6E8EB; border-radius: 16px; background-color: white; }
            QScrollBar:vertical { border: none; background: #F6F7F9; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #D0D7DE; border-radius: 5px; }
        """)
        
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background-color: white;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 10, 0, 10)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()
        
        self.scroll_area.setWidget(self.list_container)
        self.layout.addWidget(self.scroll_area)

    def setup_multi_select_toolbar(self):
        self.multi_select_bar = QFrame()
        self.multi_select_bar.setObjectName("MultiSelectBar")
        self.multi_select_bar.setFrameShape(QFrame.NoFrame)
        self.toolbar_height = 60
        self.multi_select_bar.setMaximumHeight(0)
        self.multi_select_bar.setStyleSheet("""
            QFrame#MultiSelectBar {
                background-color: white;
                border: 1px solid #E6E8EB;
                border-radius: 8px;
            }
        """)
        self.multi_select_bar.hide()
        
        toolbar_layout = QHBoxLayout(self.multi_select_bar)
        toolbar_layout.setContentsMargins(20, 5, 20, 5)
        toolbar_layout.setSpacing(20)

        self.radio_select_all = QRadioButton("Select All")
        self.radio_select_all.setStyleSheet("""
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                spacing: 10px;
                background: transparent;
            }
        """)
        self.radio_select_all.clicked.connect(self.toggle_select_all)
        toolbar_layout.addWidget(self.radio_select_all)

        self.selection_count_label = QLabel("0 / 0 selected")
        self.selection_count_label.setStyleSheet("color: #586380; background-color: transparent; border: none; font-size: 14px;")
        toolbar_layout.addWidget(self.selection_count_label)
        
        toolbar_layout.addStretch()

        self.btn_bulk_move = QPushButton("📦 Move")
        self.btn_bulk_move.setFixedSize(95, 36)
        self.btn_bulk_move.setCursor(Qt.PointingHandCursor)
        self.btn_bulk_move.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_bulk_move.clicked.connect(self.handle_bulk_move)
        toolbar_layout.addWidget(self.btn_bulk_move)

        self.btn_bulk_delete_cards = QPushButton("🗑️ Delete")
        self.btn_bulk_delete_cards.setFixedSize(95, 36)
        self.btn_bulk_delete_cards.setCursor(Qt.PointingHandCursor)
        self.btn_bulk_delete_cards.setStyleSheet("""
            QPushButton { background-color: #FF4D4D; color: white; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #E60000; }
        """)
        self.btn_bulk_delete_cards.clicked.connect(self.handle_bulk_delete_cards)
        toolbar_layout.addWidget(self.btn_bulk_delete_cards)

        self.btn_cancel_select = QPushButton("Cancel")
        self.btn_cancel_select.setFixedSize(90, 36)
        self.btn_cancel_select.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_select.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid black;
                color: black;
                border-radius: 6px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: lightgray; }
        """)
        self.btn_cancel_select.clicked.connect(self.exit_selection_mode)
        toolbar_layout.addWidget(self.btn_cancel_select)

        self.layout.addWidget(self.multi_select_bar)
        
        self.toolbar_animation = QPropertyAnimation(self.multi_select_bar, b"maximumHeight")
        self.toolbar_animation.setDuration(300)
        self.toolbar_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.toolbar_animation.finished.connect(self.on_animation_finished)

    def on_back_clicked(self):
        """Cleans up selection mode and requests navigation back."""
        self.exit_selection_mode()
        self.back_requested.emit()

    def on_animation_finished(self):
        if not self.is_selection_mode and self.multi_select_bar.maximumHeight() == 0:
            self.multi_select_bar.hide()

    def enter_selection_mode(self, initial_card_data=None):
        if self.is_selection_mode: return
        self.is_selection_mode = True
        self.multi_select_bar.show()
        
        self.toolbar_animation.stop()
        self.toolbar_animation.setStartValue(self.multi_select_bar.maximumHeight())
        self.toolbar_animation.setEndValue(self.toolbar_height)
        self.toolbar_animation.start()
        
        for row in self.all_rows:
            row.set_selection_mode(True)
            if initial_card_data and row.card_id == initial_card_data['id']:
                row.set_selected(True)
        
        self.update_selection_count()

    def exit_selection_mode(self):
        if not self.is_selection_mode: return
        self.is_selection_mode = False
        
        self.toolbar_animation.stop()
        self.toolbar_animation.setStartValue(self.multi_select_bar.height())
        self.toolbar_animation.setEndValue(0)
        self.toolbar_animation.start()
        
        self.radio_select_all.setChecked(False)
        for row in self.all_rows:
            row.set_selection_mode(False)
        self.update_selection_count()

    def toggle_select_all(self):
        checked = self.radio_select_all.isChecked()
        for row in self.all_rows:
            if row.isVisible():
                row.set_selected(checked)
        self.update_selection_count()

    def update_selection_count(self):
        visible_rows = [r for r in self.all_rows if r.isVisible()]
        total = len(visible_rows)
        selected = sum(1 for r in visible_rows if r.is_selected)
        self.selection_count_label.setText(f"{selected} / {total} selected")
        
        if total > 0 and selected == total:
            self.radio_select_all.setChecked(True)
        else:
            self.radio_select_all.setChecked(False)

    def handle_bulk_move(self):
        selected_ids = [r.card_id for r in self.all_rows if r.is_selected]
        if not selected_ids:
            QMessageBox.warning(self, "No Selection", "Please select cards to move.")
            return

        dialog = MoveCardsDialog(self.set_data['id'], self.db, self)
        if dialog.exec():
            target_set_id = dialog.selected_set_id
            success = self.db.move_cards(selected_ids, target_set_id)
            if success:
                QMessageBox.information(self, "Success", f"Moved {len(selected_ids)} cards successfully.")
                self.exit_selection_mode()
                self.load_set(self.set_data) # Refresh current set
            else:
                QMessageBox.critical(self, "Error", "Failed to move cards.")

    def handle_bulk_delete_cards(self):
        selected_ids = [r.card_id for r in self.all_rows if r.is_selected]
        if not selected_ids:
            QMessageBox.warning(self, "No Selection", "Please select cards to delete.")
            return

        reply = QMessageBox.question(
            self, "Delete Cards", f"Are you sure you want to delete {len(selected_ids)} selected cards?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.db.delete_cards_bulk(selected_ids)
            if success:
                QMessageBox.information(self, "Deleted", f"Deleted {len(selected_ids)} cards.")
                self.exit_selection_mode()
                self.load_set(self.set_data)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete cards.")

    def on_sort_changed(self, index):
        """Saves sort preference and applies sorting."""
        if self.is_selection_mode:
            # Revert the index change
            self.sort_box.blockSignals(True)
            saved_sort = ConfigManager.get_sort_preference("detail", 0)
            self.sort_box.setCurrentIndex(saved_sort)
            self.sort_box.blockSignals(False)        
            QMessageBox.warning(self, "Sort Disabled", "You cannot change the sort order while in multi-selection mode.")
            return
        
        ConfigManager.save_sort_preference("detail", index)
        self.apply_sorting()

    def apply_sorting(self, target_word=None):
        """Sorts the raw card data and re-renders the list."""
        sort_index = self.sort_box.currentIndex()
        if sort_index == 1: # A-Z
            self.all_cards_raw.sort(key=lambda x: x.get('word', '').lower())
        elif sort_index == 2: # Z-A
            self.all_cards_raw.sort(key=lambda x: x.get('word', '').lower(), reverse=True)
        else: # Original (DB order)
            # Restore from original list
            self.all_cards_raw = list(self.all_cards_original)

        self.render_card_rows(target_word)

    def render_card_rows(self, target_word=None):
        """Clears and re-renders card rows based on all_cards_raw."""
        # Clear existing rows
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.all_rows = []
        target_widget = None
        
        for card in self.all_cards_raw:
            row = TermRowWidget(card)
            row.star_toggled.connect(self.db.update_card_star)
            row.tts_requested.connect(self.handle_tts)
            row.long_pressed.connect(self.enter_selection_mode)
            row.selection_changed.connect(self.update_selection_count)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            self.all_rows.append(row)
            
            # Preserve selection mode if re-rendering while active
            if self.is_selection_mode:
                row.set_selection_mode(True)
            
            if target_word and card['word'].lower() == target_word.lower():
                target_widget = row

        # Re-apply current search filter
        self.filter_terms(self.search_input.text())

        # Scroll to target if found
        if target_widget:
            QTimer.singleShot(200, lambda: self.scroll_area.ensureWidgetVisible(target_widget))

    def filter_terms(self, text):
        if self.is_selection_mode:
            QMessageBox.warning(self, "Search Disabled", "You cannot search while in multi-selection mode.")
            return
        
        query = text.strip().lower()
        for row in self.all_rows:
            row.setVisible(query in row.word.lower() or query in row.definition.lower())

    def load_set(self, set_data, target_word=None):
        self.exit_selection_mode()
        self.set_data = set_data
        self.title_label.setText(set_data['title'])
        self.search_input.clear()

        saved_sort = ConfigManager.get_sort_preference("detail", 0)
        self.sort_box.blockSignals(True)
        self.sort_box.setCurrentIndex(saved_sort)
        self.sort_box.blockSignals(False)
        
        self.all_cards_original = self.db.get_cards(set_data['id'])
        self.all_cards_raw = list(self.all_cards_original)
        self.count_label.setText(f"Terms in this set ({len(self.all_cards_raw)})")
        
        # Apply sorting (which will call render_card_rows)
        self.apply_sorting(target_word)

    def handle_tts(self, word):
        self.tts.speak(word)

class MySetsView(QWidget):
    study_requested = Signal(dict)
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    create_requested = Signal()
    export_requested = Signal(dict)
    bulk_export_requested = Signal(list)
    bulk_delete_requested = Signal(list)
    start_study = Signal(list) # Emitted when cards are loaded and shuffled

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self.all_sets_data = [] # Cache for local set filtering
        self._columns = 3
        self.setup_ui()

    def setup_ui(self):
        # ... existing setup_ui code ...
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # 1. Main List View
        self.list_view = QWidget()
        list_layout = QVBoxLayout(self.list_view)
        list_layout.setContentsMargins(50, 40, 50, 40)
        list_layout.setSpacing(20)
        
        # Header Row
        header = QHBoxLayout()
        title = QLabel("My Sets")
        title.setStyleSheet("font-size: 32px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px;")
        header.addWidget(title)
        header.addStretch()
        
        self.btn_add_set = QPushButton("Create Set")
        self.btn_add_set.setFixedSize(160, 48)
        self.btn_add_set.setCursor(Qt.PointingHandCursor)
        self.btn_add_set.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_add_set.clicked.connect(self.create_requested.emit)
        header.addWidget(self.btn_add_set)
        list_layout.addLayout(header)

        # Sort Row
        sort_row = QHBoxLayout()
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        sort_row.addWidget(sort_label)        

        self.sort_box = QComboBox()
        self.sort_box.addItems(["Latest", "Oldest", "Alphabetical (A-Z)", "Alphabetical (Z-A)"])
        self.sort_box.setFixedSize(200, 40)
        self.sort_box.setStyleSheet("""
            QComboBox {
                border: 1px solid #E6E8EB;
                border-radius: 8px;
                padding: 5px 30px 5px 10px;
                background-color: white;
                color: #2c3e50;
            }
        """)
        self.sort_box.currentIndexChanged.connect(self.on_sort_changed)
        sort_row.addWidget(self.sort_box)
        sort_row.addStretch()
        multi_select_label = QLabel("Press and hold a set widget to enter multi-select mode.")
        multi_select_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        sort_row.addWidget(multi_select_label)
        list_layout.addLayout(sort_row)

        # Restore sort preference
        saved_sort = ConfigManager.get_sort_preference("mysets", 0)
        self.sort_box.blockSignals(True)
        self.sort_box.setCurrentIndex(saved_sort)
        self.sort_box.blockSignals(False)

        # Search Bar Row
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        
        self.search_mode = QComboBox()
        self.search_mode.addItems(["Search Sets", "Search Words"])
        self.search_mode.setFixedSize(160, 40)
        self.search_mode.setStyleSheet("""
            QComboBox {
                border: 1px solid #E6E8EB;
                border-radius: 8px;
                padding: 5px 30px 5px 10px;
                background-color: white;
                color: #2c3e50;
            }
        """)

        self.search_mode.currentIndexChanged.connect(self.on_search_mode_changed)
        search_row.addWidget(self.search_mode)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search your study sets...")
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E6E8EB;
                border-radius: 8px;
                padding: 0 15px;
                font-size: 14px;
                background-color: white;
                color: #2c3e50;
            }
            QLineEdit:focus { border: 1px solid #3498db; }
        """)
        self.search_input.returnPressed.connect(self.perform_search)
        search_row.addWidget(self.search_input)

        self.btn_search = QPushButton("🔍 Search")
        self.btn_search.setAutoDefault(True)
        self.btn_search.setFixedSize(100, 40)
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_search.clicked.connect(self.perform_search)
        search_row.addWidget(self.btn_search)

        self.btn_clear_search = QPushButton("🔄 Reset")
        self.btn_clear_search.setFixedSize(100, 40)
        self.btn_clear_search.setCursor(Qt.PointingHandCursor)
        self.btn_clear_search.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #ced4da;
                color: #2c3e50;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #f8f9fa; border-color: #3498db; color: #3498db; }
        """)
        self.btn_clear_search.clicked.connect(self.clear_search)
        search_row.addWidget(self.btn_clear_search)

        list_layout.addLayout(search_row)

        # Multi-select toolbar (Hidden by default)
        self.setup_multi_select_toolbar(list_layout)

        # Stack for Grid vs Search Results
        self.content_stack = QStackedWidget()
        
        # Grid View (for sets)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("border: none; background: transparent;")
        grid_content = QWidget()
        grid_content.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(grid_content)
        self.grid_layout.setSpacing(25)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid_scroll.setWidget(grid_content)
        self.content_stack.addWidget(self.grid_scroll)

        # Word Search Result View
        self.word_scroll = QScrollArea()
        self.word_scroll.setWidgetResizable(True)
        self.word_scroll.setStyleSheet("border: none; background: transparent;")
        word_content = QWidget()
        word_content.setStyleSheet("background: transparent;")
        self.word_results_layout = QVBoxLayout(word_content)
        self.word_results_layout.setSpacing(10)
        self.word_results_layout.setAlignment(Qt.AlignTop)
        self.word_scroll.setWidget(word_content)
        self.content_stack.addWidget(self.word_scroll)

        list_layout.addWidget(self.content_stack)

        # 2. Detail View
        self.detail_view = SetDetailView()
        self.detail_view.back_requested.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.detail_view.study_requested.connect(self.start_study_session)
        self.detail_view.edit_requested.connect(self.edit_requested.emit)
        self.detail_view.delete_requested.connect(self.delete_requested.emit)
        self.detail_view.export_requested.connect(self.export_requested.emit)

        self.stacked_widget.addWidget(self.list_view)
        self.stacked_widget.addWidget(self.detail_view)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Set card width is ~300px + spacing
        new_cols = max(2, self.width() // SetCardWidget.cardset_width)
        if new_cols != self._columns:
            self._columns = new_cols
            self.update_grid_display()

    def on_sort_changed(self, index):
        """Saves sort preference and updates grid."""
        if self.is_selection_mode:
            # Revert the index change
            self.sort_box.blockSignals(True)
            saved_sort = ConfigManager.get_sort_preference("mysets", 0)
            self.sort_box.setCurrentIndex(saved_sort)
            self.sort_box.blockSignals(False)
            QMessageBox.warning(self, "Sort Disabled", "You cannot change the sort order while in multi-selection mode.")
            return
        
        ConfigManager.save_sort_preference("mysets", index)
        self.update_grid_display()

    def start_study_session(self, set_data):
        """Initializes and starts a study session for a given card set with a loading popup."""
        set_id = set_data.get('id')
        if not set_id: return

        self.loading_dialog = LoadingDialog("Loading cards", self)
        self.loading_dialog.show()
        
        self.study_worker = StudyLoadingWorker(self.db, set_id)
        self.study_worker.finished.connect(lambda cards: self.on_study_cards_loaded(cards, set_id))
        self.study_worker.error.connect(self.on_study_load_error)
        self.study_worker.start()

    def on_study_cards_loaded(self, cards, set_id):
        self.loading_dialog.close()
        if not cards:
            QMessageBox.warning(self, "Empty Set", "This set has no cards to study.")
            return

        # Update last studied time in DB
        self.db.update_last_studied(set_id)
        
        # Signal MainWindow to show StudyView with set info
        self.start_study.emit(cards)

    def on_study_load_error(self, err_msg):
        self.loading_dialog.close()
        QMessageBox.critical(self, "Error", f"Failed to load cards: {err_msg}")

    def on_search_mode_changed(self, index):
        if index == 0:
            self.search_input.setPlaceholderText("Search your study sets...")
        else:
            self.search_input.setPlaceholderText("Search for specific words...")

    def perform_search(self):
        if self.is_selection_mode:
            QMessageBox.warning(self, "Search Disabled", "You cannot search while in multi-selection mode.")
            return
        if not self.search_input.text().strip():
            QMessageBox.warning(self, "Empty Search", "Please enter a search term.")
            return

        if self.search_mode.currentIndex() == 0:
            # Set Search: Re-render the grid with filter
            self.content_stack.setCurrentIndex(0)
            self.update_grid_display()
        else:
            # Word Search: Keep existing logic (index 1)
            query = self.search_input.text().strip().lower()
            if not query:
                self.content_stack.setCurrentIndex(0)
                self.update_grid_display()
            else:
                self.content_stack.setCurrentIndex(1)
                self.search_db_words(query)

    def search_db_words(self, query):
        self.clear_word_results()
        results = self.db.search_words(query)
        if not results:
            label = QLabel("No matching words found.")
            label.setStyleSheet("color: #586380; font-size: 16px; padding: 20px;")
            self.word_results_layout.addWidget(label)
        else:
            for card in results:
                res_widget = WordSearchResultWidget(card)
                res_widget.clicked.connect(self.open_detail)
                self.word_results_layout.addWidget(res_widget)

    def clear_word_results(self):
        while self.word_results_layout.count():
            item = self.word_results_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def setup_multi_select_toolbar(self, parent_layout):
        self.multi_select_bar = QFrame()
        self.multi_select_bar.setObjectName("MultiSelectBar")
        self.multi_select_bar.setFrameShape(QFrame.NoFrame)
        # We will animate maximumHeight for the sliding effect
        self.toolbar_height = 60
        self.multi_select_bar.setMaximumHeight(0)
        self.multi_select_bar.setStyleSheet("""
            QFrame#MultiSelectBar {
                background-color: white;
                border: 1px solid #E6E8EB;
                border-radius: 8px;
            }
        """)
        self.multi_select_bar.hide()
        
        toolbar_layout = QHBoxLayout(self.multi_select_bar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(15)

        # 1. RadioButton for Select All
        self.radio_select_all = QRadioButton("Select All")
        self.radio_select_all.setStyleSheet("""
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                spacing: 10px;
                background: transparent;
            }
        """)
        self.radio_select_all.clicked.connect(self.toggle_select_all)
        toolbar_layout.addWidget(self.radio_select_all)

        # 2. Count Label
        self.selection_count_label = QLabel("0 / 0 selected")
        self.selection_count_label.setStyleSheet("color: #586380; background-color: transparent; border: none; font-size: 14px;")
        toolbar_layout.addWidget(self.selection_count_label)
        
        toolbar_layout.addStretch()

        # 3. Action Buttons
        self.btn_bulk_export = QPushButton("📤 Export")
        self.btn_bulk_export.setFixedSize(90, 32)
        self.btn_bulk_export.setStyleSheet("""
            QPushButton { 
                background-color: #3498db;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_bulk_export.clicked.connect(self.handle_bulk_export)
        toolbar_layout.addWidget(self.btn_bulk_export)

        self.btn_bulk_delete = QPushButton("🗑️ Delete")
        self.btn_bulk_delete.setFixedSize(90, 32)
        self.btn_bulk_delete.setStyleSheet("""
            QPushButton {
                background-color: #FF4D4D;
                color: white;
                border-radius: 6px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E60000; }
        """)
        self.btn_bulk_delete.clicked.connect(self.handle_bulk_delete)
        toolbar_layout.addWidget(self.btn_bulk_delete)

        self.btn_cancel_select = QPushButton("Cancel")
        self.btn_cancel_select.setFixedSize(80, 32)
        self.btn_cancel_select.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid black;
                color: black;
                border-radius: 6px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: lightgray; }
        """)
        self.btn_cancel_select.clicked.connect(self.exit_selection_mode)
        toolbar_layout.addWidget(self.btn_cancel_select)

        parent_layout.addWidget(self.multi_select_bar)
        
        # Animation setup
        self.toolbar_animation = QPropertyAnimation(self.multi_select_bar, b"maximumHeight")
        self.toolbar_animation.setDuration(300)
        self.toolbar_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.toolbar_animation.finished.connect(self.on_animation_finished)

        self.is_selection_mode = False
        self.active_cards = [] # Store references to visible SetCardWidgets

    def on_animation_finished(self):
        if not self.is_selection_mode and self.multi_select_bar.maximumHeight() == 0:
            self.multi_select_bar.hide()

    def enter_selection_mode(self, initial_set_data=None):
        if self.is_selection_mode: return
        
        self.is_selection_mode = True
        self.multi_select_bar.show()
        
        # Animate sliding down
        self.toolbar_animation.stop()
        self.toolbar_animation.setStartValue(self.multi_select_bar.maximumHeight())
        self.toolbar_animation.setEndValue(self.toolbar_height)
        self.toolbar_animation.start()
        
        # Enable selection mode on all visible cards
        for card in self.active_cards:
            card.set_selection_mode(True)
            # If triggered by a specific card, select it
            if initial_set_data and card.set_data['id'] == initial_set_data['id']:
                card.set_selected(True)
        
        self.update_selection_count()

    def exit_selection_mode(self):
        if not self.is_selection_mode: return
        self.is_selection_mode = False
        
        # Animate sliding up
        self.toolbar_animation.stop()
        self.toolbar_animation.setStartValue(self.multi_select_bar.height())
        self.toolbar_animation.setEndValue(0)
        self.toolbar_animation.start()
        
        self.radio_select_all.setChecked(False)
        
        for card in self.active_cards:
            card.set_selection_mode(False)
        
        self.update_selection_count()

    def toggle_select_all(self):
        checked = self.radio_select_all.isChecked()
        for card in self.active_cards:
            card.set_selected(checked)
        self.update_selection_count()

    def update_selection_count(self):
        total = len(self.active_cards)
        selected = sum(1 for card in self.active_cards if card.is_selected)
        self.selection_count_label.setText(f"{selected} / {total} selected")
        
        # Auto-check radio if all selected
        if total > 0 and selected == total:
            self.radio_select_all.setChecked(True)
        else:
            self.radio_select_all.setChecked(False)

    def handle_bulk_export(self):
        selected_sets = [card.set_data for card in self.active_cards if card.is_selected]
        if not selected_sets:
            QMessageBox.warning(self, "No Selection", "Please select at least one card set to export.")
            return
        self.bulk_export_requested.emit(selected_sets)

    def handle_bulk_delete(self):
        selected_sets = [card.set_data for card in self.active_cards if card.is_selected]
        if not selected_sets:
            QMessageBox.warning(self, "No Selection", "Please select at least one card set to delete.")
            return
        self.bulk_delete_requested.emit(selected_sets)

    def handle_card_clicked(self, set_data):
        if self.is_selection_mode:
            # Updating count after the card toggles itself
            self.update_selection_count()
        else:
            self.open_detail(set_data)

    def refresh_sets(self):
        self.all_sets_data = self.db.get_card_sets()
        self.update_grid_display()

    def update_grid_display(self):
        # 1. Clear existing grid items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        self.active_cards = []

        if not self.all_sets_data:
            placeholder = QLabel("You haven't created any sets yet.")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #95a5a6; font-style: italic; font-size: 18px; padding-top: 40px;")
            self.grid_layout.addWidget(placeholder, 0, 0)
            return

        # 2. Filter data
        query = self.search_input.text().strip().lower()
        display_data = [s for s in self.all_sets_data if query in s.get('title', '').lower()]

        # 3. Sort filtered data
        sort_index = self.sort_box.currentIndex()
        if sort_index == 0: # Latest
            display_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_index == 1: # Oldest
            display_data.sort(key=lambda x: x.get('created_at', ''), reverse=False)
        elif sort_index == 2: # Alphabetical (A-Z)
            display_data.sort(key=lambda x: x.get('title', '').lower(), reverse=False)
        elif sort_index == 3: # Alphabetical (Z-A)
            display_data.sort(key=lambda x: x.get('title', '').lower(), reverse=True)
            
        # 4. Re-render the grid
        if not display_data:
            placeholder = QLabel("No sets match your search.")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #95a5a6; font-style: italic; font-size: 18px; padding-top: 40px;")
            self.grid_layout.addWidget(placeholder, 0, 0)
        else:
            for i, set_data in enumerate(display_data):
                card = SetCardWidget(set_data)
                card.clicked.connect(self.handle_card_clicked)
                card.long_pressed.connect(self.enter_selection_mode)
                card.edit_requested.connect(self.edit_requested.emit)
                card.delete_requested.connect(self.delete_requested.emit)
                card.export_requested.connect(self.export_requested.emit)
                self.grid_layout.addWidget(card, i // self._columns, i % self._columns)
                self.active_cards.append(card)
                
                # If we refresh while in selection mode, preserve it
                if self.is_selection_mode:
                    card.set_selection_mode(True)
            
            # Reset stretches and add a spacer column to keep cards left-aligned
            for col in range(self.grid_layout.columnCount()):
                self.grid_layout.setColumnStretch(col, 0)
                
            self.grid_layout.setColumnStretch(self._columns, 1)

    def create_new_set(self):
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        title, ok = QInputDialog.getText(self, "Create Set", "Set Title:", QLineEdit.Normal, "New Vocabulary Set")
        if ok and title.strip():
            self.db.create_card_set(title.strip(), "Created from UI")
            self.refresh_sets()

    def open_detail(self, set_data, target_word=None):
        self.detail_view.load_set(set_data, target_word)
        self.stacked_widget.setCurrentIndex(1)

    def clear_search(self):
        """Clears the search input and resets the view to show all sets."""
        self.search_input.clear()
        self.search_mode.setCurrentIndex(0)
        self.content_stack.setCurrentIndex(0)
        self.update_grid_display()

    def reset_view(self):
        """Resets the view to the main list view and clears selection mode."""
        self.exit_selection_mode()
        self.detail_view.exit_selection_mode()
        self.stacked_widget.setCurrentIndex(0)
        self.all_sets_data = []
        self.clear_search()
        self.clear_word_results()
