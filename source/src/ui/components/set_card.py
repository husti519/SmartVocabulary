from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGraphicsDropShadowEffect, QMenu)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor

class SetCardWidget(QFrame):
    cardset_width = 340
    clicked = Signal(dict)
    long_pressed = Signal(dict)
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    export_requested = Signal(dict)

    def __init__(self, set_data, parent=None):
        super().__init__(parent)
        self.set_data = set_data
        self.set_title = set_data.get('title', 'No Title')
        
        # Selection state
        self.is_selectable = False
        self.is_selected = False
        
        # Timer for long press detection
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.timeout.connect(self.on_long_press_timeout)
        self.is_long_press = False
        
        self.setup_ui()

    def set_selection_mode(self, enabled):
        self.is_selectable = enabled
        if not enabled:
            self.set_selected(False)

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame#SetCard {
                    background-color: lightgray;
                    border: 2px solid #3498db;
                    border-radius: 16px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#SetCard {
                    background-color: white;
                    border: 1px solid #E6E8EB;
                    border-radius: 16px;
                }
                QFrame#SetCard:hover {
                    border: 1px solid #3498db;
                    background-color: #FCFDFE;
                }
            """)

    def setup_ui(self):
        self.setFixedSize(290, 165)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("SetCard")
        self.update_style()
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(12)

        # Top Row: Card Count and Options Button
        top_layout = QHBoxLayout()
        
        # Calculate count
        count = 0
        if 'cards' in self.set_data:
            cards_info = self.set_data['cards']
            if isinstance(cards_info, list) and len(cards_info) > 0:
                count = cards_info[0].get('count', 0)
            elif isinstance(cards_info, dict):
                count = cards_info.get('count', 0)
        
        count_label = QLabel(f"{count} cards")
        count_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #3498db;
            background-color: #F0F7FF;
            border-radius: 6px;
            padding: 4px 10px;
        """)
        top_layout.addWidget(count_label)
        top_layout.addStretch()
        
        self.btn_options = QPushButton("···")
        self.btn_options.setFixedSize(32, 32)
        self.btn_options.setStyleSheet("""
            QPushButton {
                font-size: 18px; 
                color: black; 
                border: 1px solid #D9E0E6; 
                border-radius: 16px; 
                background: transparent;
                padding-bottom: 2px;
            }
            QPushButton:hover { 
                color: black; 
                background-color: #F6F7F9; 
                border: 1px solid #BDC3C7;
            }
        """)
        self.btn_options.clicked.connect(self.show_context_menu)
        top_layout.addWidget(self.btn_options)
        layout.addLayout(top_layout)

        # Title
        self.title_label = QLabel(self.set_title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #2c3e50;")
        layout.addWidget(self.title_label, 1)

    def show_context_menu(self):
        if self.is_selectable:
            return
            
        menu = QMenu(self)
        edit_act = menu.addAction("✏️ Edit")
        delete_act = menu.addAction("🗑️ Delete")
        menu.addSeparator()
        export_act = menu.addAction("📤 Export to CSV")
        
        # Note: We don't implement functions yet, just emit signals if needed later
        action = menu.exec(self.btn_options.mapToGlobal(self.btn_options.rect().bottomLeft()))
        
        if action == edit_act:
            self.edit_requested.emit(self.set_data)
        elif action == delete_act:
            self.delete_requested.emit(self.set_data)
        elif action == export_act:
            self.export_requested.emit(self.set_data)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_long_press = False
            self.long_press_timer.start(1200)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.long_press_timer.stop()
            if not self.is_long_press and self.rect().contains(event.pos()):
                if self.is_selectable:
                    self.set_selected(not self.is_selected)
                self.clicked.emit(self.set_data)
        super().mouseReleaseEvent(event)

    def on_long_press_timeout(self):
        self.is_long_press = True
        self.long_pressed.emit(self.set_data)

