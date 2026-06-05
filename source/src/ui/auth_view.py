import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame, QCheckBox,
                             QDialog, QFormLayout, QDialogButtonBox, QApplication)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QMovie
from ..backend.supabase_client import SupabaseManager
from ..utils.config_manager import ConfigManager
from .components.loading_dialog import LoadingDialog

class SupabaseConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Supabase Configuration")
        self.setFixedWidth(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Supabase 설정")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        info = QLabel("접속할 Supabase 프로젝트의 URI와 API Key를 입력하세요.\n"
                      "API Key는 Legacy anon key가 아닌, Publishable key를 넣어주셔야 합니다.")
        info.setWordWrap(True)
        info.setStyleSheet("color: black; font-size: 13px;")
        layout.addWidget(info)

        form = QFormLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://your-project.supabase.co")
        self.url_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("sb_publishable_...")
        self.key_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        url, key = ConfigManager.get_supabase_config()
        if url: self.url_input.setText(url)
        if key: self.key_input.setText(key)

        form.addRow("Project URL:", self.url_input)
        form.addRow("Publishable Key:", self.key_input)
        layout.addLayout(form)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.validate)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def validate(self):
        url = self.url_input.text().strip()
        key = self.key_input.text().strip()
        if not url or not key:
            QMessageBox.warning(self, "입력 오류", "URL과 Key를 모두 입력해주세요.")
            return
        if not url.startswith("https"):
            QMessageBox.warning(self, "형식 오류", "올바른 URL 형식이 아닙니다. (https://...로 시작해야 합니다.)")
            return

        # 실제 연결 테스트 수행
        self.buttons.setEnabled(False) # 테스트 중 버튼 비활성화
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            res = SupabaseManager.test_connection(url, key)
            if res.get("success"):
                QApplication.restoreOverrideCursor()
                self.accept()
            else:
                QApplication.restoreOverrideCursor()
                error_msg = res.get("error", "알 수 없는 오류가 발생했습니다.")
                QMessageBox.critical(self, "연결 실패", f"Supabase 연결에 실패했습니다.\n\n오류 내용:\n{error_msg}")
        finally:
            QApplication.restoreOverrideCursor()
            self.buttons.setEnabled(True)

    def get_config(self):
        return self.url_input.text().strip(), self.key_input.text().strip()

class LoginWorker(QThread):
    finished = Signal(object)

    def __init__(self, db, email, password):
        super().__init__()
        self.db = db
        self.email = email
        self.password = password

    def run(self):
        try:
            res = self.db.sign_in(self.email, self.password)
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit({"error": str(e)})

class PasswordChangeDialog(QDialog):
    def __init__(self, parent=None, is_recovery=False):
        super().__init__(parent)
        self.is_recovery = is_recovery
        self.setWindowTitle("Reset Password" if is_recovery else "Change Password")
        self.setFixedWidth(350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Set New Password")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)

        if is_recovery:
            info = QLabel("Verification successful. Please enter your new password below.")
            info.setWordWrap(True)
            info.setStyleSheet("color: #7f8c8d; font-size: 13px; margin-bottom: 5px;")
            layout.addWidget(info)

        form = QFormLayout()
        
        # Current Password field only if NOT in recovery mode
        self.current_pw = None
        if not is_recovery:
            self.current_pw = QLineEdit()
            self.current_pw.setPlaceholderText("Enter current password")
            self.current_pw.setEchoMode(QLineEdit.Password)
            self.current_pw.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
            form.addRow("Current Password:", self.current_pw)

        self.new_pw = QLineEdit()
        self.new_pw.setPlaceholderText("Minimum 6 characters")
        self.new_pw.setEchoMode(QLineEdit.Password)
        self.new_pw.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.confirm_pw = QLineEdit()
        self.confirm_pw.setPlaceholderText("Repeat new password")
        self.confirm_pw.setEchoMode(QLineEdit.Password)
        self.confirm_pw.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        form.addRow("New Password:", self.new_pw)
        form.addRow("Confirm:", self.confirm_pw)
        layout.addLayout(form)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.validate)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Ok).setText("Update Password")
        self.buttons.setStyleSheet("QPushButton { padding: 6px 15px; }")
        layout.addWidget(self.buttons)
        
    def validate(self):
        if self.current_pw and not self.current_pw.text().strip():
            QMessageBox.warning(self, "Error", "Please enter your current password.")
            return

        pw = self.new_pw.text()
        if len(pw) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters.")
            return
        if pw != self.confirm_pw.text():
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return
        self.accept()
        
    def get_passwords(self):
        """Returns (new_password, current_password)"""
        curr = self.current_pw.text() if self.current_pw else None
        return self.new_pw.text(), curr

    def get_password(self):
        """Legacy method for backward compatibility if needed, returns new password."""
        return self.new_pw.text()

class OTPVerifyDialog(QDialog):
    def __init__(self, email, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Verify OTP")
        self.setFixedWidth(350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Enter 8-digit Verification Code")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        info = QLabel(f"A verification code has been sent to:\n{email}")
        info.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        layout.addWidget(info)

        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter code")
        self.otp_input.setAlignment(Qt.AlignCenter)
        self.otp_input.setMaxLength(8) # 8-digit OTP as requested by user
        self.otp_input.setStyleSheet("""
            QLineEdit {
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
                border: 2px solid #3498db;
                border-radius: 8px;
                color: black;
                background-color: white;
            }
        """)
        layout.addWidget(self.otp_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.Ok).setText("Verify Code")
        self.buttons.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.buttons)

    def get_otp(self):
        return self.otp_input.text().strip()

class LoginView(QWidget):
    login_success = Signal()
    go_to_signup = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self.setup_ui()
        self.load_remembered_email()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        frame = QFrame()
        frame.setFixedSize(400, 520)
# ... (rest of styling remains same)
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 15px;
            }
            QLineEdit {
                padding: 12px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
                color: black;
            }
            QPushButton#primary_btn {
                background-color: #3498db;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton#secondary_btn {
                color: #3498db;
                border: 1px solid transparent;
                background: none;
                padding: 5px 10px;
                border-radius: 5px;
            }
            QPushButton#secondary_btn:hover {
                border: 1px solid #3498db;
                background-color: #f0f8ff;
            }
            QCheckBox {
                color: #7f8c8d;
                font-size: 13px;
                border: none;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(40, 40, 40, 40)
        frame_layout.setSpacing(18)

        title = QLabel("Login")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; border: none; color: #2c3e50;")
        frame_layout.addWidget(title)

        # Settings button (top right style)
        self.btn_settings = QPushButton("⚙️ Supabase Settings")
        self.btn_settings.setObjectName("secondary_btn")
        self.btn_settings.setFixedSize(140, 30)
        self.btn_settings.clicked.connect(self.open_settings)
        frame_layout.addWidget(self.btn_settings, 0, Qt.AlignRight)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email Address")
        self.email_input.returnPressed.connect(self.handle_login)
        frame_layout.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        frame_layout.addWidget(self.password_input)

        # Remember Email Checkbox
        self.remember_checkbox = QCheckBox("Remember Email")
        self.remember_checkbox.setStyleSheet("background-color: transparent")
        frame_layout.addWidget(self.remember_checkbox)

        login_btn = QPushButton("Login")
        login_btn.setObjectName("primary_btn")
        login_btn.clicked.connect(self.handle_login)
        frame_layout.addWidget(login_btn)

        self.forgot_pw_btn = QPushButton("Forgot Password?")
        self.forgot_pw_btn.setObjectName("secondary_btn")
        self.forgot_pw_btn.clicked.connect(self.handle_forgot_password)
        frame_layout.addWidget(self.forgot_pw_btn)

        signup_layout = QHBoxLayout()
        signup_layout.setAlignment(Qt.AlignCenter)
        signup_text = QLabel("Don't have an account?")
        signup_text.setStyleSheet("color: #7f8c8d; border: none")
        signup_layout.addWidget(signup_text)
        
        signup_btn = QPushButton("Sign Up")
        signup_btn.setObjectName("secondary_btn")
        signup_btn.clicked.connect(self.go_to_signup.emit)
        signup_layout.addWidget(signup_btn)
        frame_layout.addLayout(signup_layout)

        layout.addWidget(frame)

    def set_initial_focus(self):
        """Sets focus to email if empty, otherwise to password."""
        if not self.email_input.text().strip():
            self.email_input.setFocus()
        else:
            self.password_input.setFocus()

    def load_remembered_email(self):
        if os.path.exists(ConfigManager.CONFIG_FILE):
            try:
                with open(ConfigManager.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    email = config.get("remembered_email", "")
                    if email:
                        self.email_input.setText(email)
                        self.remember_checkbox.setChecked(True)
            except Exception:
                pass

    def save_remembered_email(self):
        email = self.email_input.text() if self.remember_checkbox.isChecked() else ""
        try:
            config = {}
            if os.path.exists(ConfigManager.CONFIG_FILE):
                with open(ConfigManager.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            
            config["remembered_email"] = email
            with open(ConfigManager.CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception:
            pass

    def open_settings(self):
        dialog = SupabaseConfigDialog(self)
        if dialog.exec():
            url, key = dialog.get_config()
            self.db.update_config(url, key)
            QMessageBox.information(self, "Success", "Supabase configuration updated!")

    def handle_forgot_password(self):
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        email, ok = QInputDialog.getText(self, "Reset Password", 
                                        "Enter your email address to receive a 8-digit reset code:", 
                                        QLineEdit.Normal, self.email_input.text())
        if ok and email.strip():
            # 1. Request OTP via email
            res = self.db.send_password_reset_email(email.strip())
            if not res.get("success"):
                QMessageBox.critical(self, "Error", f"Failed to send reset code: {res.get('error')}")
                return

            # 2. Open OTP Verification Dialog in a loop for retries
            otp_dialog = OTPVerifyDialog(email.strip(), self)
            while True:
                if otp_dialog.exec():
                    otp_code = otp_dialog.get_otp()
                    
                    # 3. Verify OTP
                    verify_res = self.db.verify_otp(email.strip(), otp_code, type="recovery")
                    if verify_res.get("success"):
                        # 4. If verified, open Password Change Dialog
                        pw_dialog = PasswordChangeDialog(self, is_recovery=True)
                        if pw_dialog.exec():
                            new_password = pw_dialog.get_password()
                            update_res = self.db.update_password(new_password)
                            
                            if update_res.get("success"):
                                QMessageBox.information(self, "Success", "Password reset successfully! You can now login with your new password.")
                                # Sign out because verify_otp creates a temporary session
                                self.db.sign_out()
                                self.password_input.clear()
                                break # Success, exit loop
                            else:
                                QMessageBox.critical(self, "Error", f"Failed to update password: {update_res.get('error')}")
                        else:
                            # User cancelled password change dialog
                            self.db.sign_out()
                            break
                    else:
                        QMessageBox.critical(self, "Verification Failed", f"Invalid or expired code: {verify_res.get('error')}")
                        # Loop continues, allowing retry in otp_dialog
                else:
                    # User cancelled OTP dialog
                    break

    def handle_login(self):
        if not self.db.client:
            QMessageBox.critical(self, "Configuration Error", 
                                "Supabase is not configured. Please click the ⚙️ Settings button to enter your URL and Key.")
            return

        email = self.email_input.text()
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return

        self.loading_dialog = LoadingDialog("Logging in", self)
        self.loading_dialog.show()
        
        self.worker = LoginWorker(self.db, email, password)
        self.worker.finished.connect(self.on_login_finished)
        self.worker.start()

    def on_login_finished(self, res):
        self.loading_dialog.close()
        if hasattr(res, 'user') and res.user:
            self.save_remembered_email()
            self.password_input.clear() # Clear for next use
            self.login_success.emit()
        else:
            error_msg = res.get('error', 'Login failed.') if isinstance(res, dict) else "Login failed."
            QMessageBox.critical(self, "Login Error", error_msg)

    def clear_password(self):
        self.password_input.clear()

class SignupView(QWidget):
    signup_success = Signal()
    go_to_login = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SupabaseManager()
        self.temp_user_data = {}
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)

        self.frame = QFrame()
        self.frame.setFixedSize(400, 580)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 15px;
            }
            QLineEdit {
                padding: 12px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
                color: black;
            }
            QPushButton#primary_btn {
                background-color: #2ecc71;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton#secondary_btn {
                color: #2ecc71;
                border: 1px solid transparent;
                background: none;
                padding: 5px 10px;
                border-radius: 5px;
            }
            QPushButton#secondary_btn:hover {
                border: 1px solid #2ecc71;
                background-color: #f0fff0;
            }
            QPushButton#eye_btn {
                border: none;
                background: none;
                font-size: 18px;
                color: #7f8c8d;
                padding: 0px 5px;
            }
            QWidget#signup_widget {
                background-color: white;
            }
            QWidget#verify_widget {
                background-color: white;
            }
        """)
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(40, 40, 40, 40)
        self.frame_layout.setSpacing(15)

        # Container for Signup Form
        self.signup_widget = QWidget()
        self.signup_widget.setObjectName("signup_widget")
        signup_layout = QVBoxLayout(self.signup_widget)
        signup_layout.setContentsMargins(0, 0, 0, 0)
        signup_layout.setSpacing(15)

        title = QLabel("Create Account")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; border: none; color: #2c3e50;")
        signup_layout.addWidget(title)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.returnPressed.connect(self.handle_signup)
        signup_layout.addWidget(self.username_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email Address")
        self.email_input.returnPressed.connect(self.handle_signup)
        signup_layout.addWidget(self.email_input)

        # Password layout with toggle
        pw_layout = QHBoxLayout()
        pw_layout.setSpacing(0)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_signup)
        pw_layout.addWidget(self.password_input)
        
        self.eye_btn = QPushButton("🔒")
        self.eye_btn.setObjectName("eye_btn")
        self.eye_btn.setFixedSize(40, 40)
        self.eye_btn.setCursor(Qt.PointingHandCursor)
        self.eye_btn.clicked.connect(self.toggle_password_visibility)
        pw_layout.addWidget(self.eye_btn)
        signup_layout.addLayout(pw_layout)

        signup_btn = QPushButton("Sign Up")
        signup_btn.setObjectName("primary_btn")
        signup_btn.clicked.connect(self.handle_signup)
        signup_layout.addWidget(signup_btn)

        login_row = QHBoxLayout()
        login_row.setAlignment(Qt.AlignCenter)
        login_text = QLabel("Already have an account?")
        login_text.setStyleSheet("color: #7f8c8d; border:none")
        login_row.addWidget(login_text)
        
        login_btn = QPushButton("Login")
        login_btn.setObjectName("secondary_btn")
        login_btn.clicked.connect(self.go_to_login.emit)
        login_row.addWidget(login_btn)
        signup_layout.addLayout(login_row)

        # Container for Verification Message
        self.verify_widget = QWidget()
        self.verify_widget.setObjectName("verify_widget")
        self.verify_widget.hide()
        verify_layout = QVBoxLayout(self.verify_widget)
        verify_layout.setContentsMargins(0, 0, 0, 0)
        verify_layout.setSpacing(20)

        verify_title = QLabel("Verify Your Email")
        verify_title.setAlignment(Qt.AlignCenter)
        verify_title.setStyleSheet("font-size: 24px; font-weight: bold; border: none; color: #2c3e50;")
        verify_layout.addWidget(verify_title)

        self.verify_msg = QLabel("A 8-digit verification code has been sent to your email.\nPlease enter the code to complete your registration.")
        self.verify_msg.setWordWrap(True)
        self.verify_msg.setAlignment(Qt.AlignCenter)
        self.verify_msg.setStyleSheet("color: #7f8c8d; border: none; font-size: 14px;")
        verify_layout.addWidget(self.verify_msg)

        verify_done_btn = QPushButton("Enter Verification Code")
        verify_done_btn.setObjectName("primary_btn")
        verify_done_btn.clicked.connect(self.handle_verification_complete)
        verify_layout.addWidget(verify_done_btn)

        self.resend_btn = QPushButton("Resend Verification Code")
        self.resend_btn.setObjectName("secondary_btn")
        self.resend_btn.clicked.connect(self.handle_resend_otp)
        verify_layout.addWidget(self.resend_btn)

        back_btn = QPushButton("Go Back")
        back_btn.setObjectName("secondary_btn")
        back_btn.clicked.connect(self.show_signup_form)
        verify_layout.addWidget(back_btn)

        self.frame_layout.addWidget(self.signup_widget)
        self.frame_layout.addWidget(self.verify_widget)
        
        self.main_layout.addWidget(self.frame)

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.eye_btn.setText("🔓")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.eye_btn.setText("🔒")

    def show_signup_form(self):
        self.temp_user_data = {}
        self.verify_widget.hide()
        self.signup_widget.show()

    def show_verify_message(self):
        self.signup_widget.hide()
        self.verify_widget.show()

    def handle_resend_otp(self):
        email = self.temp_user_data.get("email")
        if not email:
            QMessageBox.warning(self, "Error", "No email found. Please sign up again.")
            self.show_signup_form()
            return

        self.resend_btn.setEnabled(False)
        self.resend_btn.setText("Sending...")
        
        res = self.db.resend_signup_otp(email)
        
        if res.get("success"):
            QMessageBox.information(self, "Resent", f"A new verification code has been sent to {email}.")
        else:
            QMessageBox.critical(self, "Error", f"Failed to resend code: {res.get('error')}")
            
        # Optional: Add a timer to prevent spamming resend
        QTimer.singleShot(60000, lambda: self.enable_resend_button())
        self.resend_btn.setText("Resend Code (Wait 60s)")

    def enable_resend_button(self):
        self.resend_btn.setEnabled(True)
        self.resend_btn.setText("Resend Verification Code")

    def handle_signup(self):
        if not self.db.client:
            QMessageBox.critical(self, "Configuration Error", 
                                "Supabase is not configured. Please go back to Login and click the ⚙️ Settings button.")
            return

        username = self.username_input.text()
        email = self.email_input.text()
        password = self.password_input.text()

        if not username or not email or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return

        # 1. Sign up for Auth
        res = self.db.sign_up(email, password, username)

        if isinstance(res, dict) and 'error' in res:
            error_msg = res['error']
            QMessageBox.critical(self, "Signup Error", f"Signup failed: {error_msg}")
            return

        self.temp_user_data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        self.show_verify_message()

    def handle_verification_complete(self):
        email = self.temp_user_data.get("email")
        username = self.temp_user_data.get("username")

        if not email:
            QMessageBox.warning(self, "Error", "No registration session found. Please sign up again.")
            self.show_signup_form()
            return

        otp_dialog = OTPVerifyDialog(email, self)
        if otp_dialog.exec():
            otp_code = otp_dialog.get_otp()
            
            # 1. Verify OTP
            verify_res = self.db.verify_otp(email, otp_code, type="signup")
            
            if verify_res.get("success"):
                # 2. OTP verification successful, user is now logged in
                try:
                    # Create or update profile
                    self.db.client.table("profiles").upsert({
                        "id": verify_res["user"].id,
                        "username": username
                    }).execute()
                    
                    QMessageBox.information(self, "Success", "Email verified and profile created!")
                    self.signup_success.emit()
                except Exception as e:
                    QMessageBox.warning(self, "Profile Error", f"Authenticated, but failed to create profile: {e}")
                    self.signup_success.emit()
            else:
                error_msg = verify_res.get("error", "Verification failed.")
                QMessageBox.critical(self, "Verification Failed", f"Invalid or expired code: {error_msg}")
