from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QScrollArea, QGridLayout, QFileDialog, QInputDialog, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QColor
from ..backend.supabase_client import SupabaseManager
from .components.set_card import SetCardWidget
import os

class BatchImportWorker(QThread):
    progress = Signal(int, str) # current index, file name
    finished = Signal(list) # list of results

    def __init__(self, db, file_paths):
        super().__init__()
        self.db = db
        self.file_paths = file_paths

    def run(self):
        results = []
        for i, path in enumerate(self.file_paths):
            file_name = os.path.basename(path)
            self.progress.emit(i, file_name)
            
            # Use file name (without extension) as set title for batch import
            title = os.path.splitext(file_name)[0]
            res = self.db.import_from_csv(path, custom_title=title)
            results.append({"file": file_name, "result": res})
            
        self.finished.emit(results)

class HomeView(QWidget):
    request_my_sets = Signal()
    set_selected = Signal(dict)
    import_requested = Signal(dict)
    batch_import_requested = Signal(list)
    create_requested = Signal()
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    export_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self._columns = 3
        self._recent_data = []
        self._all_sets_data = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(40)
        layout.setAlignment(Qt.AlignTop)

        # 1. Header Area
        header_layout = QVBoxLayout()
        header_layout.setSpacing(25)

        welcome_label = QLabel("Welcome back!")
        welcome_label.setStyleSheet("font-size: 28px; font-weight: 800; color: #2c3e50; letter-spacing: -0.5px;")
        header_layout.addWidget(welcome_label)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)

        self.btn_import = self.create_action_button("Import csv file", "📤")
        self.btn_import.clicked.connect(self.on_import_clicked)
        actions_layout.addWidget(self.btn_import)

        self.btn_create = self.create_action_button("Create manually", "➕")
        self.btn_create.clicked.connect(self.create_requested.emit)
        actions_layout.addWidget(self.btn_create)
        
        actions_layout.addStretch()
        header_layout.addLayout(actions_layout)
        layout.addLayout(header_layout)

        # 2. Main Content
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setStyleSheet("border: none; background: transparent;")
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(50)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setAlignment(Qt.AlignTop)

        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(self.recent_container)

        self.sets_container = QWidget()
        self.sets_layout = QVBoxLayout(self.sets_container)
        self.sets_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(self.sets_container)

        content_scroll.setWidget(content_widget)
        layout.addWidget(content_scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Calculate optimal column count:
        new_cols = max(2, self.width() // SetCardWidget.cardset_width)
        if new_cols != self._columns:
            self._columns = new_cols
            self.rebuild_sections()

    def create_action_button(self, text, icon_str):
        btn = QPushButton(f"{icon_str}  {text}")
        btn.setFixedSize(240, 56)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E6E8EB;
                border-radius: 12px;
                font-size: 15px;
                font-weight: bold;
                color: #2c3e50;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background-color: #F6F7F9;
                border: 1px solid #3498db;
                color: #3498db;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 4)
        btn.setGraphicsEffect(shadow)
        return btn

    def on_import_clicked(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select CSV Files", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_paths:
            return

        if len(file_paths) == 1:
            file_path = file_paths[0]
            default_title = os.path.splitext(os.path.basename(file_path))[0]
            title, ok = QInputDialog.getText(
                self, "Import CSV", "Enter a title for this card set:",
                QLineEdit.Normal, default_title
            )
            if ok and title.strip():
                self.import_requested.emit({"file_path": file_path, "title": title.strip()})
        else:
            self.batch_import_requested.emit(file_paths)

    def refresh_data(self):
        if not self.db.user: return
        self._recent_data = self.db.get_recent_card_sets(limit=10) # Get more to fill rows
        self._all_sets_data = self.db.get_card_sets()
        self.rebuild_sections()

    def rebuild_sections(self):
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        while self.sets_layout.count():
            item = self.sets_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        # Show up to 2 full rows of recent sets
        recent_limit = self._columns * 2
        recent_to_show = self._recent_data[:recent_limit]
        recent_section = self.create_section_widget("Recent", recent_to_show, None, "No recently studied sets yet.")
        self.recent_layout.addWidget(recent_section)

        # Show 1 full row of all sets as preview
        preview_limit = self._columns
        preview_sets = self._all_sets_data[:preview_limit] if self._all_sets_data else []
        sets_section = self.create_section_widget("My Sets", preview_sets, self.show_all_sets, "You haven't created any sets yet.")
        self.sets_layout.addWidget(sets_section)

    def create_section_widget(self, title_text, data, see_all_callback, empty_msg):
        section_widget = QWidget()
        section_layout = QVBoxLayout(section_widget)
        section_layout.setSpacing(15)
        section_layout.setContentsMargins(0, 0, 0, 0)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 20, 0)

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        header_row.addWidget(title)
        header_row.addStretch()

        # Only show 'See all' if data exists AND a callback is provided
        if data and see_all_callback:
            see_all_btn = QPushButton("See all")
            see_all_btn.setStyleSheet("""
                QPushButton { color: #3498db; border: none; font-weight: bold; font-size: 14px; }
                QPushButton:hover { text-decoration: underline; }
            """)
            see_all_btn.clicked.connect(see_all_callback)
            header_row.addWidget(see_all_btn)
        
        section_layout.addLayout(header_row)

        if data:
            grid = QGridLayout()
            grid.setSpacing(20)
            for i, set_data in enumerate(data):
                card = SetCardWidget(set_data)
                card.clicked.connect(self.set_selected.emit)
                card.edit_requested.connect(self.edit_requested.emit)
                card.delete_requested.connect(self.delete_requested.emit)
                card.export_requested.connect(self.export_requested.emit)
                grid.addWidget(card, i // self._columns, i % self._columns)
            
            # If the last row is not full, add a spacer to keep cards left-aligned
            if len(data) % self._columns != 0:
                grid.setColumnStretch(self._columns - 1, 1)
            
            section_layout.addLayout(grid)
        else:
            placeholder = QLabel(empty_msg)
            placeholder.setFixedHeight(120)
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel { background-color: #f8f9fa; border: 1px dashed #ddd; border-radius: 10px; color: #95a5a6; font-style: italic; }
            """)
            section_layout.addWidget(placeholder)
        
        return section_widget

    def show_all_recent(self): self.request_my_sets.emit()
    def show_all_sets(self): self.request_my_sets.emit()
