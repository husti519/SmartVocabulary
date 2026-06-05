import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QLockFile, QDir, Qt  # Added Qt
from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger
from src.utils.asset_manager import AssetManager
from src.utils.path_utils import get_resource_path
import ctypes

def main():
    setup_logger()

    app = QApplication(sys.argv)

    # Windows Taskbar Icon Fix
    if sys.platform == 'win32':
        myappid = u'lim.smartvoca.vocabularyapp.1.0' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app_icon = AssetManager.get_icon("icons8-Vocabulary-100.png")
    app.setWindowIcon(app_icon)

    # 중복 실행 방지
    lock_path = os.path.join(QDir.tempPath(), "smart_voca.lock")
    lock_file = QLockFile(lock_path)

    # attempt to lock for 100 milliseconds
    if not lock_file.tryLock(100):
        # 패키징 환경(PyInstaller)에서 확실히 보이도록 QMessageBox 상세 설정
        msg = QMessageBox()
        msg.setWindowIcon(app_icon)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("SmartVocabulary")
        msg.setText("프로그램이 이미 실행 중입니다.\n기존 창을 확인해 주세요.")
        # 최상단에 띄우기 (다른 창에 가려지는 문제 해결)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec()
        sys.exit(0)

    style_path = get_resource_path(os.path.join("assets", "style.css"))
    if not os.path.exists(style_path):
        QMessageBox.critical(None, "오류", f"스타일 시트 파일을 찾을 수 없습니다:\n{style_path}")
        sys.exit(1)

    with open(style_path, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()