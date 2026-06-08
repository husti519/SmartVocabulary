from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, 
                             QPushButton, QFrame, QLineEdit, QScrollArea, QTextEdit, QSizePolicy, QApplication)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from ..backend.supabase_client import SupabaseManager
from ..backend.crawler import GeminiWorker
from ..utils.logger import log_exception
from .components.focus_button import FocusButton
from .components.loading_dialog import LoadingDialog

class SaveSetWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, db, edit_set_id, title, description, cards_data):
        super().__init__()
        self.db = db
        self.edit_set_id = edit_set_id
        self.title = title
        self.description = description
        self.cards_data = cards_data

    def run(self):
        try:
            if self.edit_set_id:
                self.db.update_card_set(self.edit_set_id, self.title, self.description)
                self.db.delete_all_cards_in_set(self.edit_set_id)
                set_id = self.edit_set_id
            else:
                res = self.db.create_card_set(self.title, self.description)
                set_id = res[0]['id']
            
            final_cards = [{"user_id": self.db.user.id, "cardset_id": set_id, "word": c["word"], "definition": c["definition"]} for c in self.cards_data]
            self.db.client.table("cards").insert(final_cards).execute()
            
            # Fetch full set data for navigation
            updated_set_res = self.db.client.table("card_sets").select("*").eq("id", set_id).execute()
            if updated_set_res.data:
                self.finished.emit(updated_set_res.data[0])
            else:
                self.finished.emit({"id": set_id, "title": self.title})
        except Exception as e:
            self.error.emit(str(e))

class SmartTextEdit(QTextEdit):
    """Custom QTextEdit that emits signals for forward navigation and auto-expands."""
    tab_pressed = Signal()
    size_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.adjust_height)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAcceptRichText(False)
        self.setFrameStyle(QFrame.NoFrame)
        self.adjust_height()

    def keyPressEvent(self, event):
        # Only handle forward Tab. Let system handle Shift+Tab or other keys.
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ShiftModifier):
            self.tab_pressed.emit()
            event.accept()
            return 
        super().keyPressEvent(event)

    def adjust_height(self):
        self.document().setTextWidth(self.viewport().width())
        new_height = int(self.document().size().height()) + 15
        new_height = max(45, new_height)
        if self.height() != new_height:
            self.setFixedHeight(new_height)
            self.size_changed.emit()

class CardInputRow(QFrame):
    delete_requested = Signal(object)
    tab_reached_end = Signal(object)
    autofill_status_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet("""
            CardInputRow { background-color: white; border-bottom: 2px solid #E6E8EB; margin-bottom: 10px; }
            SmartTextEdit { border: none; border-bottom: 2px solid #2c3e50; background-color: transparent; padding: 5px 0px; font-size: 16px; color: #2c3e50; }
            SmartTextEdit:focus { border-bottom: 2px solid #3498db; }
            QLabel#header_label { font-size: 11px; font-weight: 800; color: #586380; letter-spacing: 1px; }
            QLabel#num_label { font-size: 18px; font-weight: 700; color: #2c3e50; }
            QMessageBox { background-color: #F7F8FA; }
            QMessageBox QPushButton {
                color: #2c3e50;
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px 15px;
                min-height: 20px;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover { background-color: #e9ecef; border-color: #adb5bd; }
        """)
        
        self.main_row_layout = QHBoxLayout(self)
        self.main_row_layout.setContentsMargins(10, 15, 10, 15)
        self.main_row_layout.setSpacing(30)
        self.main_row_layout.setAlignment(Qt.AlignTop)

        self.num_label = QLabel("1")
        self.num_label.setObjectName("num_label")
        self.num_label.setFixedWidth(30)
        self.num_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.num_label.setContentsMargins(0, 5, 0, 0)
        self.main_row_layout.addWidget(self.num_label, 0, Qt.AlignTop)

        # TERM (Word)
        word_vbox = QVBoxLayout()
        word_vbox.setContentsMargins(0, 5, 0, 0)
        word_vbox.setSpacing(5)
        word_vbox.setAlignment(Qt.AlignCenter)
        word_hdr = QLabel("TERM")
        word_hdr.setObjectName("header_label")
        word_vbox.addWidget(word_hdr)
        word_vbox.addStretch()
        
        self.word_input = SmartTextEdit()
        self.word_input.setPlaceholderText("Enter term")
        word_vbox.addWidget(self.word_input)

        self.btn_autofill = FocusButton("✨ Auto-fill")
        self.btn_autofill.setCursor(Qt.PointingHandCursor)
        self.btn_autofill.setStyleSheet("""
            QPushButton { background-color: #f0f7ff; border: 1px solid #3498db; color: #3498db; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background-color: #3498db; color: white; }
            QPushButton:focus { border: 2px solid #2980b9; background-color: #e1f0ff; }
            QPushButton:disabled { background-color: #f5f5f5; border: 1px solid #ddd; color: #aaa; }
        """)
        word_vbox.addWidget(self.btn_autofill, 0, Qt.AlignLeft)
        self.main_row_layout.addLayout(word_vbox, 2)
        self.main_row_layout.setAlignment(word_vbox, Qt.AlignTop)

        # DEFINITION
        def_vbox = QVBoxLayout()
        def_vbox.setContentsMargins(0, 5, 0, 0)
        def_vbox.setSpacing(5)
        def_vbox.setAlignment(Qt.AlignTop)
        def_hdr = QLabel("DEFINITION")
        def_hdr.setObjectName("header_label")
        def_vbox.addWidget(def_hdr)
        def_vbox.addStretch()
        
        self.def_input = SmartTextEdit()
        self.def_input.setPlaceholderText("Enter definition")
        def_vbox.addWidget(self.def_input)
        self.main_row_layout.addLayout(def_vbox, 3)
        self.main_row_layout.setAlignment(def_vbox, Qt.AlignTop)

        # DELETE
        self.btn_delete = QPushButton("🗑️")
        self.btn_delete.setFixedSize(40, 40)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet("QPushButton { background-color: transparent; color: #BDC3C7; border: none; font-size: 20px; } QPushButton:hover { color: #E74C3C; }")
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self))
        self.main_row_layout.addWidget(self.btn_delete, 0, Qt.AlignTop)

        # Wire Signals (Forward Only)
        self.word_input.tab_pressed.connect(lambda: self.btn_autofill.setFocus())
        self.word_input.size_changed.connect(self.update_row_height)
        
        self.btn_autofill.tab_pressed.connect(lambda: self.def_input.setFocus())
        self.btn_autofill.enter_pressed.connect(self.autofill_data)
        self.btn_autofill.clicked.connect(self.autofill_data)

        self.def_input.tab_pressed.connect(lambda: self.tab_reached_end.emit(self))
        self.def_input.size_changed.connect(self.update_row_height)

    def autofill_data(self):
        word = self.word_input.toPlainText().strip()
        if not word: return
        self.autofill_status_changed.emit(True)
        self.loading_dots = 0
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_timer.start(400)
        self.worker = GeminiWorker(word)
        self.worker.finished.connect(self.on_autofill_finished)
        self.worker.error.connect(self.on_autofill_error)
        self.worker.start()

    def update_loading_animation(self):
        self.loading_dots = (self.loading_dots + 1) % 4
        self.btn_autofill.setText(f"⌛ Fetching{'.' * self.loading_dots}")

    def on_autofill_finished(self, definition_text):
        self.stop_loading_animation()
        if definition_text:
            self.def_input.setPlainText(definition_text)
            self.def_input.setFocus()

    def on_autofill_error(self, err_msg):
        self.stop_loading_animation()
        QMessageBox.warning(self, "Auto-fill Error", f"Failed to fetch word data:\n{err_msg}")

    def stop_loading_animation(self):
        if hasattr(self, 'loading_timer'): self.loading_timer.stop()
        self.autofill_status_changed.emit(False)
        self.btn_autofill.setText("✨ Auto-fill")

    def update_row_height(self):
        max_child_h = max(self.word_input.height(), self.def_input.height())
        new_row_height = max(170, max_child_h + 80)
        if self.height() != new_row_height:
            self.setFixedHeight(new_row_height)
            self.updateGeometry()

    def get_data(self):
        word, definition = self.word_input.toPlainText().strip(), self.def_input.toPlainText().strip()
        return {"word": word, "definition": definition} if word and definition else None

class CreateSetView(QWidget):
    cancel_requested = Signal()
    save_success = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self.rows = []
        self.edit_set_id = None
        self.is_autofilling = False
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(100, 20, 100, 20)
        self.main_layout.setSpacing(15)

        # Header: Back Button (Repositioned and restyled)
        header_back_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("← Back")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #3498db;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        header_back_layout.addWidget(self.btn_cancel)
        header_back_layout.addStretch()
        self.main_layout.addLayout(header_back_layout)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        self.title_main = QLabel("Create a new study set")
        self.title_main.setStyleSheet("font-size: 24px; font-weight: 800; color: #2c3e50;")
        header_layout.addWidget(self.title_main)
        header_layout.addStretch()

        self.btn_save = QPushButton("Save")
        self.btn_save.setFixedSize(120, 50)
        self.btn_save.setStyleSheet("QPushButton { background-color: #3498db; color: white; border-radius: 8px; font-size: 16px; font-weight: 800; } QPushButton:hover { background-color: #2980b9; }")
        self.btn_save.clicked.connect(self.save_set)
        header_layout.addWidget(self.btn_save)
        self.main_layout.addWidget(header_widget)

        info_layout = QVBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('Enter a title...')
        self.title_input.setStyleSheet("QLineEdit { border: none; border-bottom: 2px solid #2c3e50; background-color: transparent; padding: 8px 0px; font-size: 18px; font-weight: 700; color: #2c3e50; }")
        info_layout.addWidget(self.title_input)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Add a description...")
        self.desc_input.setStyleSheet("QLineEdit { border: none; border-bottom: 2px solid #E6E8EB; background-color: transparent; padding: 8px 0px; font-size: 15px; color: #586380; }")
        info_layout.addWidget(self.desc_input)
        self.main_layout.addLayout(info_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")
        self.scroll_content = QWidget()
        self.rows_layout = QVBoxLayout(self.scroll_content)
        self.rows_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        buttons_layout = QHBoxLayout()
        self.btn_add_card = QPushButton("+ ADD CARD")
        self.btn_add_card.setFixedSize(140, 50)
        self.btn_add_card.setStyleSheet("""
           QPushButton { 
                background-color: white;
                border: 2px solid #3498db;
                color: #3498db;
                border-radius: 8px;
                font-weight: 800;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3498db; color: white; }
        """)
        self.btn_add_card.clicked.connect(self.add_and_scroll)
        buttons_layout.addWidget(self.btn_add_card)
        buttons_layout.addStretch()
        self.main_layout.addLayout(buttons_layout)

        for _ in range(3): self.add_row()

    def add_and_scroll(self):
        new_row = self.add_row()
        QTimer.singleShot(10, lambda: self.scroll_area.ensureWidgetVisible(new_row))

    def add_row(self):
        row = CardInputRow()
        row.num_label.setText(str(len(self.rows) + 1))
        row.delete_requested.connect(self.remove_row)
        row.tab_reached_end.connect(self.handle_row_tab_out)
        row.autofill_status_changed.connect(self.handle_autofill_status)
        # Apply current autofill lock state to the new row
        row.btn_autofill.setEnabled(not self.is_autofilling)
        
        self.rows_layout.addWidget(row)
        self.rows.append(row)
        return row

    def handle_autofill_status(self, is_busy):
        self.is_autofilling = is_busy
        # Toggle all autofill buttons based on global state
        for row in self.rows:
            row.btn_autofill.setEnabled(not is_busy)

    def handle_row_tab_out(self, current_row):
        idx = self.rows.index(current_row)
        if idx == len(self.rows) - 1: 
            next_row = self.add_row()
        else: 
            next_row = self.rows[idx + 1]
        
        next_row.word_input.setFocus()
        # Ensure the newly focused row is visible in the scroll area
        QTimer.singleShot(10, lambda: self.scroll_area.ensureWidgetVisible(next_row))

    def remove_row(self, row_widget):
        if self.is_autofilling:
            QMessageBox.warning(self, "Removing Disabled", "Please wait for the current auto-fill task to complete before Removing.")
            return
    
        if len(self.rows) <= 1: return

        self.rows_layout.removeWidget(row_widget)
        self.rows.remove(row_widget)
        row_widget.deleteLater()
        for i, r in enumerate(self.rows): r.num_label.setText(str(i + 1))
        self.scroll_content.adjustSize()

    def clear_all(self):
        self.title_input.clear()
        self.desc_input.clear()
        self.edit_set_id = None
        self.title_main.setText("Create a new study set")
        for row in self.rows:
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self.rows = []
        for _ in range(3): self.add_row()
        # Reset scroll to top
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(0))

    def load_set_data(self, set_data):
        self.title_input.setText(set_data.get('title', ''))
        self.desc_input.setText(set_data.get('description', ''))
        self.edit_set_id = set_data.get('id')
        self.title_main.setText("Edit study set")
        for row in self.rows:
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self.rows = []
        cards = self.db.get_cards(self.edit_set_id)
        if cards:
            for card in cards:
                row = self.add_row()
                row.word_input.setPlainText(card.get('word', ''))
                row.def_input.setPlainText(card.get('definition', ''))
        else:
            for _ in range(3): self.add_row()
        # Reset scroll to top
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(0))

    def on_cancel_requested(self):
        if self.is_autofilling:
            QMessageBox.warning(self, "Action Disabled", "Please wait for the current auto-fill task to complete.")
            return
        
        self.cancel_requested.emit()

    def save_set(self):
        if self.is_autofilling:
            QMessageBox.warning(self, "Saving Disabled", "Please wait for the current auto-fill task to complete before Saving.")
            return

        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please enter a title for this study set.")
            return
            
        cards_data = [d for r in self.rows if (d := r.get_data())]
        if not cards_data:
            QMessageBox.warning(self, "Validation Error", "Please add at least one complete card (term and definition).")
            return

        # Show Loading Dialog
        self.loading_dialog = LoadingDialog("Saving study set", self)
        self.loading_dialog.show()

        # Start Background Worker
        self.save_worker = SaveSetWorker(
            self.db, 
            self.edit_set_id, 
            title, 
            self.desc_input.text().strip(), 
            cards_data
        )
        self.save_worker.finished.connect(self.on_save_finished)
        self.save_worker.error.connect(self.on_save_error)
        self.save_worker.start()

    def on_save_finished(self, set_data):
        self.loading_dialog.close()
        self.save_success.emit(set_data)

    def on_save_error(self, err_msg):
        self.loading_dialog.close()
        log_exception("CreateSetView.save_set", "Save failed", Exception(err_msg))
        QMessageBox.critical(self, "Save Error", f"Failed to save study set: {err_msg}")
