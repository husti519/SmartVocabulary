from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QGraphicsDropShadowEffect, QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QEvent
from PySide6.QtGui import QColor
from ..backend.supabase_client import SupabaseManager
from ..backend.tts import TTSManager
from ..utils.asset_manager import AssetManager
from ..utils.config_manager import ConfigManager
import random

class CardWidget(QFrame):
    star_toggled = Signal(bool)
    tts_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setMaximumSize(1000, 600)
        self.setObjectName("MainCard")
        
        # Add Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)

        self.setStyleSheet("""
            QFrame#MainCard {
                background-color: white;
                border: 1px solid #E6E8EB;
                border-radius: 24px;
            }
        """)
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Top Bar for Buttons
        self.top_bar = QWidget()
        self.top_bar.setStyleSheet("""
            QWidget {
                background-color: white; 
                border-top-left-radius: 24px; 
                border-top-right-radius: 24px;
                border: none;
            }
        """)
        self.top_bar_layout = QHBoxLayout(self.top_bar)
        self.top_bar_layout.setContentsMargins(25, 20, 25, 0)
        
        # Use centralized AssetManager for icons
        tts_icon = AssetManager.get_icon("icons8-volume-48.png")
        self.btn_tts = QPushButton(tts_icon, "")
        self.btn_tts.setFixedSize(44, 44)
        self.btn_tts.setIconSize(QSize(24, 24))
        self.btn_tts.setCursor(Qt.PointingHandCursor)
        self.btn_tts.setFocusPolicy(Qt.NoFocus)
        self.btn_tts.setStyleSheet("""
            QPushButton {
                background-color: #F6F7F9;
                border: none;
                border-radius: 22px;
                color: #586380;
            }
            QPushButton:hover { background-color: #EDEFF4; color: #2c3e50; }
        """)
        self.btn_tts.clicked.connect(lambda: self.tts_requested.emit())
        self.top_bar_layout.addWidget(self.btn_tts)

        self.top_bar_layout.addStretch()
        
        self.btn_star = QPushButton("★")
        self.btn_star.setFixedSize(44, 44)
        self.btn_star.setCursor(Qt.PointingHandCursor)
        self.btn_star.setFocusPolicy(Qt.NoFocus)
        self.btn_star.setStyleSheet("""
            QPushButton {
                background-color: #F6F7F9;
                border: none;
                border-radius: 22px;
                font-size: 22px;
                color: #BDC3C7;
            }
            QPushButton[starred="true"] { color: #F1C40F; background-color: #FFFDF0; }
            QPushButton:hover { background-color: #EDEFF4; }
        """)
        self.btn_star.clicked.connect(self.toggle_star)
        self.top_bar_layout.addWidget(self.btn_star)
        
        # Content Layout
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        # Disable automatic scroll via focus to let parent handle arrow keys
        self.scroll_area.setFocusPolicy(Qt.NoFocus)
        self.scroll_area.verticalScrollBar().setFocusPolicy(Qt.NoFocus)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 20, 40, 40)
        
        # term & definition QLabel.
        self.text_label = QLabel("Front")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_layout.addWidget(self.text_label)
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addWidget(self.scroll_area, 1)
        
        # Click timer for flip logic
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        
        # Use event filter to capture clicks even on selectable labels
        self.content_widget.installEventFilter(self)
        self.text_label.installEventFilter(self)

        self.is_front = True
        self.is_starred = False
        self.front_text = ""
        self.back_text = ""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.click_timer.start(200) # 짧은 클릭일 경우에만 filp 수행하도록 타이머 설정.
        elif event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                if self.click_timer.isActive():
                    self.click_timer.stop()
                    self.flip()
                    return True # Flip 완료 시 이벤트를 소모하여 라벨의 선택 해제 방지
        elif event.type() == QEvent.KeyPress:
            # Ctrl 조합키(복사, 전체선택 등)는 라벨이 처리하도록 통과시킴
            if event.modifiers() & Qt.ControlModifier:
                return False
                
            # 순수 방향키나 단축키만 StudyView로 전달
            p = self.parentWidget()
            while p:
                if p.__class__.__name__ == "StudyView":
                    p.keyPressEvent(event)
                    return True
                p = p.parentWidget()
        return super().eventFilter(obj, event)

    def scroll_up(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.value() - 20)

    def scroll_down(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.value() + 20)

    def flip(self, event=None):
        """Instantly toggles between front and back."""
        if self.is_front:
            self.show_back()
        else:
            self.show_front()
        
        # Reset scroll when flipping
        self.scroll_area.verticalScrollBar().setValue(0)
        
        # Maintain focus in StudyView for immediate shortcut use
        self._refocus_parent()

    def _refocus_parent(self):
        p = self.parentWidget()
        while p:
            if p.__class__.__name__ == "StudyView":
                p.setFocus()
                break
            p = p.parentWidget()

    def set_data(self, front, back, is_starred):
        self.front_text = front
        self.back_text = back
        self.is_starred = is_starred
        self.update_star_ui()
        self.show_front()
        self.scroll_area.verticalScrollBar().setValue(0)

    def toggle_star(self):
        self.is_starred = not self.is_starred
        self.update_star_ui()
        self.star_toggled.emit(self.is_starred)
        self._refocus_parent()

    def update_star_ui(self):
        self.btn_star.setProperty("starred", "true" if self.is_starred else "false")
        self.btn_star.setStyle(self.btn_star.style())

    def show_front(self):
        self.text_label.setText(self.front_text)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("font-size: 42px; font-weight: 800; color: #2c3e50;")
        self.is_front = True
        self.setStyleSheet("QFrame#MainCard { background-color: white; border: 1px solid #E6E8EB; border-radius: 24px; }")

    def show_back(self):
        self.text_label.setText(self.back_text)
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.text_label.setStyleSheet("font-size: 26px; font-weight: 500; color: #2c3e50; line-height: 1.4;")
        self.is_front = False
        self.setStyleSheet("QFrame#MainCard { background-color: #FDFDFD; border: 1px solid #3498db; border-radius: 24px; }")

class StudyView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self.tts = TTSManager()
        self.original_cards = []
        self.cards = []
        self.current_index = 0
        self.starred_only = False
        self.shortcuts = {}
        
        self.setup_ui()
        self.refresh_settings()
        self.setFocusPolicy(Qt.StrongFocus)

    def refresh_settings(self):
        """Fetches the latest shortcuts and updates UI hints."""
        self.shortcuts = ConfigManager.get_shortcuts()
        self.update_card_display()

    def setup_ui(self):
        self.main_v_layout = QVBoxLayout(self)
        self.main_v_layout.setContentsMargins(40, 40, 40, 40)
        self.main_v_layout.setAlignment(Qt.AlignCenter)

        # Header
        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Exit Study")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #7f8c8d;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { color: #2c3e50; }
        """)

        header_layout.addWidget(self.btn_back)
        header_layout.addStretch()
        self.main_v_layout.addLayout(header_layout)

        self.main_v_layout.addSpacing(10)

        # Progress Layout with QLineEdit for jumping
        self.progress_layout = QHBoxLayout()
        self.progress_layout.setAlignment(Qt.AlignCenter)
        self.progress_layout.setSpacing(5)

        progress_text_pre = QLabel("Card")
        progress_text_pre.setStyleSheet("font-size: 18px; color: #95a5a6; font-weight: bold;")
        self.progress_layout.addWidget(progress_text_pre)

        from PySide6.QtWidgets import QLineEdit
        from PySide6.QtGui import QIntValidator
        self.progress_input = QLineEdit()
        self.progress_input.setFixedSize(50, 30)
        self.progress_input.setAlignment(Qt.AlignCenter)
        self.progress_input.setValidator(QIntValidator(1, 9999, self))
        self.progress_input.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                color: #2c3e50;
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        self.progress_input.editingFinished.connect(self.jump_to_card)
        self.progress_layout.addWidget(self.progress_input)

        self.total_label = QLabel("of 0")
        self.total_label.setStyleSheet("font-size: 18px; color: #95a5a6; font-weight: bold;")
        self.progress_layout.addWidget(self.total_label)

        self.main_v_layout.addLayout(self.progress_layout)

        self.main_v_layout.addSpacing(10)

        # Card Container for horizontal centering and expansion
        self.card_container = QWidget()
        self.card_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_h_layout = QHBoxLayout(self.card_container)
        card_h_layout.setContentsMargins(0, 0, 0, 0)
        
        self.card_widget = CardWidget()
        self.card_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.card_widget.star_toggled.connect(self.handle_card_star_toggled)
        self.card_widget.tts_requested.connect(self.play_current_tts)
        
        card_h_layout.addStretch(1)
        card_h_layout.addWidget(self.card_widget, 8) # High stretch to prioritize expansion over side margins
        card_h_layout.addStretch(1)
        
        self.main_v_layout.addWidget(self.card_container, 10) # High stretch to prioritize vertical expansion
        
        # Bottom Bar
        self.bottom_bar_container = QWidget()
        self.bottom_bar_container.setMinimumWidth(600)
        self.bottom_bar_container.setMaximumWidth(1000)
        # Use QGridLayout for precise centering
        bottom_bar_layout = QGridLayout(self.bottom_bar_container)
        bottom_bar_layout.setContentsMargins(0, 10, 0, 0)
        
        # Left Side: Starred Only Filter
        self.starred_filter_container = QWidget()
        starred_filter_layout = QHBoxLayout(self.starred_filter_container)
        starred_filter_layout.setContentsMargins(0, 0, 0, 0)
        starred_filter_layout.setSpacing(8)

        self.btn_filter_star = QPushButton("★")
        self.btn_filter_star.setCheckable(True)
        self.btn_filter_star.setFixedSize(36, 36)
        self.btn_filter_star.setCursor(Qt.PointingHandCursor)
        self.btn_filter_star.setFocusPolicy(Qt.NoFocus)
        self.btn_filter_star.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 18px;
                color: #BDC3C7;
                font-size: 18px;
            }
            QPushButton:checked {
                background-color: #FFFDF0;
                border: 1px solid #F1C40F;
                color: #F1C40F;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
            }
        """)
        self.btn_filter_star.clicked.connect(self.toggle_star_filter)
        starred_filter_layout.addWidget(self.btn_filter_star)

        self.filter_label = QLabel("Study starred only")
        self.filter_label.setStyleSheet("font-size: 13px; color: #586380; font-weight: 600;")
        starred_filter_layout.addWidget(self.filter_label)
        
        bottom_bar_layout.addWidget(self.starred_filter_container, 0, 0, Qt.AlignLeft)
        
        # Center: Vertical Shortcut Hints
        self.hint_container = QWidget()
        hint_layout = QVBoxLayout(self.hint_container)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        hint_layout.setSpacing(2)
        hint_layout.setAlignment(Qt.AlignCenter)
        
        self.tts_hint = QLabel("Press 'T' to listen")
        self.tts_hint.setStyleSheet("font-size: 12px; color: #95a5a6; font-style: italic; font-weight: bold;")
        self.tts_hint.setAlignment(Qt.AlignCenter)
        hint_layout.addWidget(self.tts_hint)

        self.star_hint = QLabel("Press 'S' to star")
        self.star_hint.setStyleSheet("font-size: 12px; color: #95a5a6; font-style: italic; font-weight: bold;")
        self.star_hint.setAlignment(Qt.AlignCenter)
        hint_layout.addWidget(self.star_hint)
        
        bottom_bar_layout.addWidget(self.hint_container, 0, 1, Qt.AlignCenter)

        # Right Side: Shuffle Button
        shuffle_icon = AssetManager.get_icon("icons8-shuffle-48.png")
        self.btn_shuffle = QPushButton(shuffle_icon, "")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setFixedSize(45, 45)
        self.btn_shuffle.setIconSize(QSize(28, 28))
        self.btn_shuffle.setCursor(Qt.PointingHandCursor)
        self.btn_shuffle.setFocusPolicy(Qt.NoFocus)
        self.btn_shuffle.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 22px;
                color: #586380;
                font-size: 22px;
            }
            QPushButton:checked {
                background-color: #3498db;
                border: 1px solid #3498db;
                color: white;
            }
            QPushButton:hover {
                border: 1px solid #999;
                background-color: #f8f9fa;
            }
        """)
        self.btn_shuffle.clicked.connect(self.toggle_shuffle)
        bottom_bar_layout.addWidget(self.btn_shuffle, 0, 2, Qt.AlignRight)

        # Equalize column stretches for absolute centering of column 1
        bottom_bar_layout.setColumnStretch(0, 1)
        bottom_bar_layout.setColumnStretch(1, 1)
        bottom_bar_layout.setColumnStretch(2, 1)

        self.main_v_layout.addWidget(self.bottom_bar_container, alignment=Qt.AlignCenter)

        self.main_v_layout.addStretch(1)

        self.main_v_layout.addSpacing(30)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter)
        controls_layout.setSpacing(30)
        
        btn_style = """
            QPushButton {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 15px;
                color: #2c3e50;
                padding: 5px;
            }
            QPushButton:hover { background-color: #f8f9fa; border: 1px solid #3498db; }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #bdc3c7;
                border: 1px solid #eee;
            }
        """

        self.btn_prev = QPushButton("← Previous")
        self.btn_prev.setFixedSize(140, 50)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.setFocusPolicy(Qt.NoFocus)
        self.btn_prev.clicked.connect(self.prev_card)
        controls_layout.addWidget(self.btn_prev)
        
        self.btn_flip = QPushButton("Flip (Space)")
        self.btn_flip.setFixedSize(180, 60)
        self.btn_flip.setFocusPolicy(Qt.NoFocus)
        self.btn_flip.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        self.btn_flip.clicked.connect(self.card_widget.flip)
        controls_layout.addWidget(self.btn_flip)
        
        self.btn_next = QPushButton("Next →")
        self.btn_next.setFixedSize(140, 50)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.setFocusPolicy(Qt.NoFocus)
        self.btn_next.clicked.connect(self.next_card)
        controls_layout.addWidget(self.btn_next)
        
        self.main_v_layout.addLayout(controls_layout)

    def load_cards(self, cards):
        self.original_cards = list(cards)
        self.apply_filters()
        self.setFocus()

    def apply_filters(self):
        # 1. Start with original
        temp_cards = list(self.original_cards)
        
        # 2. Filter by Starred if enabled
        if self.starred_only:
            temp_cards = [c for c in temp_cards if c.get('starred', False)]
            
        # 3. Shuffle if enabled
        if self.btn_shuffle.isChecked():
            random.shuffle(temp_cards)
            
        self.cards = temp_cards
        self.current_index = 0
        
        if self.cards:
            self.update_card_display()
        else:
            self.card_widget.set_data("No Cards", "No cards matching the filter.", False)
            self.progress_label.setText("No cards match criteria.")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)

    def toggle_star_filter(self, checked):
        self.starred_only = checked
        self.apply_filters()
        self.setFocus()

    def toggle_shuffle(self, checked):
        if not self.cards: return
        current_card_id = self.cards[self.current_index]['id'] if self.cards else None
        
        if checked:
            # Shuffle remaining
            new_cards = self.cards[:self.current_index + 1]
            remaining_cards = self.cards[self.current_index + 1:]
            random.shuffle(remaining_cards)
            self.cards = new_cards + remaining_cards
        else:
            # Revert to filtered but original order
            temp_cards = list(self.original_cards)
            if self.starred_only:
                temp_cards = [c for c in temp_cards if c.get('starred', False)]
            self.cards = temp_cards
            # Find current index in new list
            if current_card_id:
                for i, card in enumerate(self.cards):
                    if card['id'] == current_card_id:
                        self.current_index = i
                        break
        
        self.update_card_display()
        self.setFocus()

    def update_card_display(self):
        if not self.cards: 
            self.progress_input.setText("0")
            self.total_label.setText("of 0")
            return
            
        card_data = self.cards[self.current_index]
        self.card_widget.set_data(card_data['word'], card_data['definition'], card_data.get('starred', False))
        
        # Update interactive progress input
        self.progress_input.setText(str(self.current_index + 1))
        self.total_label.setText(f"of {len(self.cards)}")
        
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.cards) - 1)

        # Update shortcut hints dynamically
        shortcuts = ConfigManager.get_shortcuts()
        star_key = shortcuts.get('star', 16777237)
        tts_key = shortcuts.get('tts', 16777235)

        self.star_hint.setText(f"Press '{ConfigManager.key_to_string(star_key)}' to star" if star_key != 0 else ' ')
        self.tts_hint.setText(f"Press '{ConfigManager.key_to_string(tts_key)}' to listen" if tts_key != 0 else ' ')

    def jump_to_card(self):
        """Jumps to a specific card index entered by the user."""
        try:
            target_idx = int(self.progress_input.text()) - 1
            if 0 <= target_idx < len(self.cards):
                self.current_index = target_idx
                self.update_card_display()
                self.setFocus() # Return focus to handle keyboard shortcuts
            else:
                # Revert to current if invalid
                self.progress_input.setText(str(self.current_index + 1))
        except ValueError:
            self.progress_input.setText(str(self.current_index + 1))
        self.progress_input.clearFocus()

    def handle_card_star_toggled(self, is_starred):
        if not self.cards: return
        card_data = self.cards[self.current_index]
        card_id = card_data['id']
        self.db.update_card_star(card_id, is_starred)
        
        # Update in both lists
        card_data['starred'] = is_starred
        for oc in self.original_cards:
            if oc['id'] == card_id:
                oc['starred'] = is_starred
                break
        
        # If we are in 'starred only' mode and unstarred a card, it stays until navigation or refresh?
        # Standard behavior: keep it for now so UI doesn't jump, but it will be gone on next load/filter.
        
        self.setFocus()

    def next_card(self):
        if self.current_index < len(self.cards) - 1:
            self.current_index += 1
            self.update_card_display()
        self.setFocus()

    def prev_card(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_card_display()
        self.setFocus()

    def play_current_tts(self):
        if not self.cards: return
        word = self.cards[self.current_index]['word']
        self.tts.speak(word)
        self.setFocus()

    def keyPressEvent(self, event):
        key = event.key()

        tts_key = self.shortcuts.get('tts', 16777235) # Default Up
        star_key = self.shortcuts.get('star', 16777237) # Default Down

        if key == tts_key:
            self.play_current_tts()
        elif key == star_key:
            self.card_widget.toggle_star()
        elif key == Qt.Key_Space:
            self.btn_flip.animateClick()
        elif key == Qt.Key_Right:
            if self.btn_next.isEnabled(): self.btn_next.animateClick()
        elif key == Qt.Key_Left:
            if self.btn_prev.isEnabled(): self.btn_prev.animateClick()
        elif key == Qt.Key_Up:
            # If Up is used as a custom shortcut, it won't scroll here
            if tts_key != Qt.Key_Up and star_key != Qt.Key_Up:
                self.card_widget.scroll_up()
        elif key == Qt.Key_Down:
            # If Down is used as a custom shortcut, it won't scroll here
            if tts_key != Qt.Key_Down and star_key != Qt.Key_Down:
                self.card_widget.scroll_down()
        else:
            super().keyPressEvent(event)
