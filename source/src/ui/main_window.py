import sys
from enum import IntEnum
from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QHBoxLayout, 
                               QPushButton, QLabel, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from .home_view import HomeView
from .my_sets_view import MySetsView
from .study_view import StudyView
from .auth_view import LoginView, SignupView
from .create_set_view import CreateSetView
from .settings_view import SettingsView
from ..utils.asset_manager import AssetManager

class ViewIndex(IntEnum):
    LOGIN = 0
    SIGNUP = 1
    HOME = 2
    MY_SETS = 3
    STUDY = 4
    CREATE_SET = 5
    SETTINGS = 6

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Vocabulary")
        self.setWindowIcon(AssetManager.get_icon("icons8-Vocabulary-100.png"))
        self.resize(1250, 800)
        self.previous_view_index = ViewIndex.HOME

        # Main Central Widget and Layout
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background-color: #F7F8FA;")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar
        self.setup_sidebar()

        # Stacked Widget for Views
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # Initialize Views
        self.login_view = LoginView()
        self.signup_view = SignupView()
        self.home_view = HomeView()
        self.my_sets_view = MySetsView()
        self.study_view = StudyView()
        self.create_set_view = CreateSetView()
        self.settings_view = SettingsView()
        
        self.stacked_widget.insertWidget(ViewIndex.LOGIN, self.login_view)
        self.stacked_widget.insertWidget(ViewIndex.SIGNUP, self.signup_view)
        self.stacked_widget.insertWidget(ViewIndex.HOME, self.home_view)
        self.stacked_widget.insertWidget(ViewIndex.MY_SETS, self.my_sets_view)
        self.stacked_widget.insertWidget(ViewIndex.STUDY, self.study_view)
        self.stacked_widget.insertWidget(ViewIndex.CREATE_SET, self.create_set_view)
        self.stacked_widget.insertWidget(ViewIndex.SETTINGS, self.settings_view)

        # Connect signals
        self.setup_connections()
        
        # Start with Login
        self.show_login()

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar_width_expanded = 200
        self.sidebar_width_collapsed = 68
        self.sidebar.setFixedWidth(self.sidebar_width_expanded)
        self.is_sidebar_collapsed = False

        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-right: 1px solid #E6E8EB;
            }
            QPushButton {
                text-align: left;
                padding: 14px 24px;
                border: none;
                font-size: 15px;
                color: #586380;
                background: none;
                font-weight: 500;
                border-radius: 0px;
            }
            QPushButton:hover {
                background-color: #F6F7F9;
                color: #2c3e50;
            }
            QPushButton#active {
                font-weight: bold;
                color: #3498db;
                background-color: #F0F7FF;
                border-right: 3px solid #3498db;
            }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 15, 0, 15)
        sidebar_layout.setSpacing(2)

        # Header with Logo and Toggle Button
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: white;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(24, 10, 15, 20)

        self.logo_label = QLabel("Smart Vocabulary")
        self.logo_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #3498db;" \
        "border: none; letter-spacing: -0.5px; background-color: transparent;")
        header_layout.addWidget(self.logo_label)

        self.btn_toggle_sidebar = QPushButton("≡")
        self.btn_toggle_sidebar.setFixedSize(32, 32)
        self.btn_toggle_sidebar.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_sidebar.setStyleSheet("""
            QPushButton {
                font-size: 22px; 
                padding: 0; 
                text-align: center; 
                color: #7f8c8d; 
                background: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #f0f0f0; }
        """)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.btn_toggle_sidebar)
        
        sidebar_layout.addWidget(header_widget)

        # Navigation Buttons
        self.btn_nav_home = QPushButton("🏠  Home")
        self.btn_nav_home.clicked.connect(self.show_home)
        sidebar_layout.addWidget(self.btn_nav_home)

        self.btn_nav_sets = QPushButton("📚  My Sets")
        self.btn_nav_sets.clicked.connect(self.show_my_sets)
        sidebar_layout.addWidget(self.btn_nav_sets)

        self.btn_nav_settings = QPushButton("⚙️  Settings")
        self.btn_nav_settings.clicked.connect(self.show_settings)
        sidebar_layout.addWidget(self.btn_nav_settings)

        sidebar_layout.addStretch()

        self.btn_about = QPushButton("ℹ️  About...")
        self.btn_about.clicked.connect(self.show_about)
        sidebar_layout.addWidget(self.btn_about)

        self.btn_logout = QPushButton("🚪  Logout")
        self.btn_logout.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.btn_logout)

        self.main_layout.addWidget(self.sidebar)
        self.sidebar.hide()

    def toggle_sidebar(self):
        if self.is_sidebar_collapsed:
            # Expand
            self.sidebar.setFixedWidth(self.sidebar_width_expanded)
            self.logo_label.show()
            self.btn_nav_home.setText("🏠  Home")
            self.btn_nav_sets.setText("📚  My Sets")
            self.btn_nav_settings.setText("⚙️  Settings")
            self.btn_about.setText("ℹ️  About...")
            self.btn_logout.setText("🚪  Logout")
            self.is_sidebar_collapsed = False
        else:
            # Collapse
            self.sidebar.setFixedWidth(self.sidebar_width_collapsed)
            self.logo_label.hide()
            self.btn_nav_home.setText("🏠")
            self.btn_nav_sets.setText("📚")
            self.btn_nav_settings.setText("⚙️")
            self.btn_about.setText("ℹ️")
            self.btn_logout.setText("🚪")
            self.is_sidebar_collapsed = True

    def show_about(self):
        """Shows the application About dialog."""
        about_text = """
        <h2 style='color: #2c3e50;'>Smart Vocabulary</h2>
        <p><b>스마트 영단어 암기장</b></p>
        <hr>
        <p>본 애플리케이션은 사용자의 효율적인 영어 학습을 돕기 위해 개발된 PySide6 기반 데스크톱 앱입니다.</p>

        <h4 style='margin-bottom: 5px;'>Key Features:</h4>
        <ul style='font-size: 12px';>
            <li>Gemini AI 기반의 지능형 단어 상세 정보 생성</li>
            <li>Supabase를 활용한 클라우드 데이터 동기화</li>
            <li>gTTS를 이용한 고품질 발음 지원</li>
            <li>커스텀 단축키 및 스마트 필터링 학습 시스템</li>
            <li>단어 리스트의 CSV Export/Import 지원</li>
        </ul>

        <h4 style='margin-bottom: 5px;'>Technical Stack:</h4>
        <p style='font-size: 12px;'>
            - <b>UI Framework:</b> PySide6 (Qt for Python)<br>
            - <b>Backend:</b> Supabase (PostgreSQL)<br>
            - <b>AI Engine:</b> Google Gemini AI<br>
            - <b>TTS:</b> gTTS (Google Text-to-Speech)<br>
        </p>

        <hr>
        <p style='color: #7f8c8d; font-size: 11px;'>
            Copyright 2026. All rights reserved.<br>
            Icons by <a href="https://icons8.com" style="color: #3498db;">Icons8</a>
        </p>
        """
        QMessageBox.about(self, "About Smart Vocabulary", about_text.strip())

    def handle_change_password(self):
        from .auth_view import PasswordChangeDialog
        
        dialog = PasswordChangeDialog(self)
        if dialog.exec():
            new_password, current_password = dialog.get_passwords()
            res = self.home_view.db.update_password(new_password, current_password)
            
            if res.get("success"):
                QMessageBox.information(self, "Success", "Password updated successfully!")
            else:
                QMessageBox.critical(self, "Error", f"Failed to update password: {res.get('error')}")

    def setup_connections(self):
        # Auth Navigation
        self.login_view.login_success.connect(self.handle_login_success)
        self.login_view.go_to_signup.connect(self.show_signup)
        self.signup_view.signup_success.connect(self.show_login)
        self.signup_view.go_to_login.connect(self.show_login)

        # App Navigation
        self.home_view.request_my_sets.connect(self.show_my_sets)
        self.home_view.set_selected.connect(self.open_set_detail)
        self.home_view.import_requested.connect(self.handle_import)
        self.home_view.batch_import_requested.connect(self.handle_batch_import)
        self.home_view.create_requested.connect(self.show_create_set)
        self.home_view.edit_requested.connect(self.handle_edit_set)
        self.home_view.delete_requested.connect(self.handle_delete_set)
        self.home_view.export_requested.connect(self.handle_export_set)
        
        self.my_sets_view.start_study.connect(self.on_study_ready)
        self.my_sets_view.create_requested.connect(self.show_create_set)
        self.my_sets_view.edit_requested.connect(self.handle_edit_set)
        self.my_sets_view.delete_requested.connect(self.handle_delete_set)
        self.my_sets_view.export_requested.connect(self.handle_export_set)
        self.my_sets_view.bulk_export_requested.connect(self.handle_bulk_export_sets)
        self.my_sets_view.bulk_delete_requested.connect(self.handle_bulk_delete_sets)

        self.create_set_view.cancel_requested.connect(self.handle_back_navigation)
        self.create_set_view.save_success.connect(self.handle_save_success)

        self.settings_view.request_logout.connect(self.handle_logout)
        self.settings_view.request_change_password.connect(self.handle_change_password)

        self.study_view.btn_back.clicked.connect(self.show_my_sets)

    def handle_login_success(self):
        """Called once when login is successful to initialize the sessionUI."""
        # 1. Reload settings to reflect current config or cleared state from previous logout
        self.settings_view.load_settings()
      
        # 2. Proceed to Home View
        self.show_home()

    def on_study_ready(self, cards):
        """Called when cards are loaded and ready to be studied."""
        self.study_view.load_cards(cards)
        self.show_study()

    def handle_bulk_export_sets(self, selected_sets):
        """Exports multiple card sets to a selected directory as separate CSV files."""
        import csv
        import os
        from PySide6.QtWidgets import QFileDialog

        # 1. Select destination directory
        dest_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Export CSV Files")
        if not dest_dir:
            return

        success_count = 0
        error_count = 0
        
        for set_data in selected_sets:
            try:
                # Fetch cards
                cards = self.home_view.db.get_cards(set_data['id'])
                if not cards:
                    continue
                
                # Sanitize filename
                safe_title = "".join([c if c.isalnum() else "_" for c in set_data['title']])
                file_path = os.path.join(dest_dir, f"{safe_title}.csv")
                
                # Write to CSV
                with open(file_path, mode='w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    for card in cards:
                        writer.writerow([card['word'], card['definition']])
                
                success_count += 1
            except Exception:
                error_count += 1

        if success_count > 0:
            msg = f"Successfully exported {success_count} sets to:\n{dest_dir}"
            if error_count > 0:
                msg += f"\n\n({error_count} sets failed to export)"
            QMessageBox.information(self, "Export Successful", msg)
            self.my_sets_view.exit_selection_mode()
        elif error_count > 0:
            QMessageBox.critical(self, "Export Failed", f"Failed to export {error_count} sets.")

    def handle_bulk_delete_sets(self, selected_sets):
        """Deletes multiple card sets after confirmation."""
        count = len(selected_sets)
        reply = QMessageBox.question(
            self, "Delete Multiple Sets", 
            f"Are you sure you want to delete {count} selected sets?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            fail_count = 0
            
            for set_data in selected_sets:
                res = self.home_view.db.delete_card_set(set_data['id'])
                if res:
                    success_count += 1
                else:
                    fail_count += 1
            
            if success_count > 0:
                QMessageBox.information(self, "Deleted", f"Successfully deleted {success_count} card sets.")
                self.my_sets_view.exit_selection_mode()
                self.home_view.refresh_data()
                self.my_sets_view.refresh_sets()
            
            if fail_count > 0:
                QMessageBox.critical(self, "Error", f"Failed to delete {fail_count} card sets.")

    def handle_export_set(self, set_data):
        """Fetches all cards in the set and exports them to a CSV file."""
        import csv
        from PySide6.QtWidgets import QFileDialog

        # 1. Select destination file
        default_name = f"{set_data['title']}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", default_name, "CSV Files (*.csv)"
        )
        
        if not file_path:
            return

        # 2. Fetch cards from DB
        cards = self.home_view.db.get_cards(set_data['id'])
        if not cards:
            QMessageBox.warning(self, "No Cards", "This set has no cards to export.")
            return

        # 3. Write to CSV
        try:
            with open(file_path, mode='w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                for card in cards:
                    writer.writerow([card['word'], card['definition']])
            
            QMessageBox.information(self, "Export Successful", f"Successfully exported {len(cards)} cards to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred while exporting:\n{str(e)}")

    def handle_back_navigation(self):
        """Returns to the previous view after cancel."""
        if self.check_navigation_lock(): return
        
        self.stacked_widget.setCurrentIndex(self.previous_view_index)
        # Re-sync sidebar based on which view we returned to
        if self.previous_view_index == ViewIndex.HOME:
            self.update_sidebar_selection(self.btn_nav_home)
            self.home_view.refresh_data()
        elif self.previous_view_index == ViewIndex.MY_SETS:
            self.update_sidebar_selection(self.btn_nav_sets)
            self.my_sets_view.refresh_sets()

    def handle_save_success(self, set_data):
        "Can not save during AI Task"
        if self.check_navigation_lock(): return

        """Called when a set is successfully saved. Navigates to the set's detail view."""
        # First ensure we are logically in the My Sets view state
        self.show_my_sets()
        # Then open the specific detail view
        self.my_sets_view.open_detail(set_data)
        # Refresh home data in background since it changed
        self.home_view.refresh_data()

    def handle_edit_set(self, set_data):
        self.previous_view_index = ViewIndex(self.stacked_widget.currentIndex())
        self.create_set_view.load_set_data(set_data)
        self.stacked_widget.setCurrentWidget(self.create_set_view)
        self.update_sidebar_selection(None)

    def handle_delete_set(self, set_data):
        reply = QMessageBox.question(
            self, "Delete Set", 
            f"Are you sure you want to delete '{set_data['title']}'?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            res = self.home_view.db.delete_card_set(set_data['id'])
            if res:
                QMessageBox.information(self, "Deleted", "Card set deleted successfully.")
                
                # If deleted from detail view inside MySetsView, snap back to list view
                if self.stacked_widget.currentWidget() == self.my_sets_view and \
                   self.my_sets_view.stacked_widget.currentIndex() == 1:
                    self.my_sets_view.stacked_widget.setCurrentIndex(0)
                
                self.home_view.refresh_data()
                self.my_sets_view.refresh_sets()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete card set.")

    def show_create_set(self):
        self.previous_view_index = ViewIndex(self.stacked_widget.currentIndex())
        self.create_set_view.clear_all()
        self.stacked_widget.setCurrentWidget(self.create_set_view)
        self.update_sidebar_selection(None)

    def open_set_detail(self, set_data):
        """Switches to MySetsView and opens the specific set detail."""
        self.show_my_sets()
        self.my_sets_view.open_detail(set_data)

    def handle_import(self, import_data):
        file_path = import_data.get("file_path")
        title = import_data.get("title")
        
        result = self.home_view.db.import_from_csv(file_path, custom_title=title)
        
        if "success" in result:
            QMessageBox.information(self, "Success", f"Successfully imported '{title}' with {result['count']} flashcards!")
            self.home_view.refresh_data()
        else:
            QMessageBox.critical(self, "Error", f"Failed to import: {result.get('error', 'Unknown error')}")

    def handle_batch_import(self, file_paths):
        from PySide6.QtWidgets import QProgressDialog
        from .home_view import BatchImportWorker
        
        progress = QProgressDialog("Importing files...", "Cancel", 0, len(file_paths), self)
        progress.setWindowTitle("Batch Import")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        
        # Create worker
        self.batch_worker = BatchImportWorker(self.home_view.db, file_paths)
        
        def update_progress(index, file_name):
            progress.setLabelText(f"Processing ({index+1}/{len(file_paths)}): {file_name}")
            progress.setValue(index)
            if progress.wasCanceled():
                self.batch_worker.terminate()

        self.batch_worker.progress.connect(update_progress)
        self.batch_worker.finished.connect(lambda results: self.on_batch_import_finished(results, progress))
        
        self.batch_worker.start()

    def on_batch_import_finished(self, results, progress_dialog):
        progress_dialog.setValue(len(results))
        
        success_count = sum(1 for r in results if "success" in r["result"])
        fail_count = len(results) - success_count
        
        summary = f"Import completed.\nSuccess: {success_count}\nFailed: {fail_count}"
        
        if fail_count > 0:
            errors = "\n\nDetails of failures:"
            for r in results:
                if "error" in r["result"]:
                    errors += f"\n- {r['file']}: {r['result']['error']}"
            summary += errors
            QMessageBox.warning(self, "Batch Import Results", summary)
        else:
            QMessageBox.information(self, "Batch Import Success", summary)
            
        self.home_view.refresh_data()
        self.my_sets_view.refresh_sets()

    def update_sidebar_selection(self, active_btn):
        # Reset all styles
        for btn in [self.btn_nav_home, self.btn_nav_sets, self.btn_nav_settings]:
            btn.setObjectName("")
            btn.setStyle(btn.style())
        
        if active_btn:
            active_btn.setObjectName("active")
            active_btn.setStyle(active_btn.style())

    def check_navigation_lock(self):
        """Returns True if navigation is locked (e.g. AI is working)."""
        if self.create_set_view.is_autofilling or self.settings_view.is_busy:
            QMessageBox.warning(self, "Navigation Disabled", 
                                "Please wait for the current AI task to complete before leaving this page.")
            return True
        return False

    def show_settings(self):
        if self.check_navigation_lock(): return
        self.sidebar.show()
        self.update_sidebar_selection(self.btn_nav_settings)
        self.stacked_widget.setCurrentWidget(self.settings_view)

    def show_login(self):
        if self.check_navigation_lock(): return
        self.sidebar.hide()
        self.login_view.clear_password()
        self.stacked_widget.setCurrentWidget(self.login_view)
        # Reset MySetsView to its initial list state
        self.my_sets_view.reset_view()
        # Set focus intelligently after the UI is shown
        QTimer.singleShot(200, self.login_view.set_initial_focus)

    def show_signup(self):
        self.stacked_widget.setCurrentWidget(self.signup_view)
        self.signup_view.show_signup_form()
        self.signup_view.username_input.clear()
        self.signup_view.email_input.clear()
        self.signup_view.password_input.clear()

    def show_home(self):
        if self.check_navigation_lock(): return
        self.sidebar.show()
        self.update_sidebar_selection(self.btn_nav_home)
        self.home_view.refresh_data()
        self.stacked_widget.setCurrentWidget(self.home_view)

    def show_my_sets(self):
        if self.check_navigation_lock(): return
        self.sidebar.show()
        self.update_sidebar_selection(self.btn_nav_sets)
        self.my_sets_view.refresh_sets()
        
        # If returning from StudyView, show the DetailView (index 1)
        if self.stacked_widget.currentWidget() == self.study_view:
            self.my_sets_view.stacked_widget.setCurrentIndex(1)
            # Re-load detail view data to sync any changes (like starred status)
            if self.my_sets_view.detail_view.set_data:
                self.my_sets_view.detail_view.load_set(self.my_sets_view.detail_view.set_data)
            
        self.stacked_widget.setCurrentWidget(self.my_sets_view)
        
    def show_study(self):
        self.my_sets_view.reset_view()
        self.study_view.refresh_settings()
        self.sidebar.show()
        self.stacked_widget.setCurrentWidget(self.study_view)

    def handle_logout(self):
        if self.check_navigation_lock(): return
        # Perform logout logic
        self.home_view.db.sign_out()
        
        self.show_login()