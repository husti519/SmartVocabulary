import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie
from ...utils.path_utils import get_resource_path

class LoadingDialog(QDialog):
    def __init__(self, base_message="Processing", parent=None):
        super().__init__(parent)
        self.base_message = base_message
        
        self.setWindowTitle("Please Wait")
        self.setFixedSize(250, 150)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # GIF Animation
        self.movie_label = QLabel()
        self.movie_label.setFixedSize(80, 80)
        
        # Use centralized path management
        gif_path = get_resource_path(os.path.join("assets", "loading.gif"))
        
        if os.path.exists(gif_path):
            self.movie = QMovie(gif_path)
            self.movie.setScaledSize(self.movie_label.size())
            self.movie_label.setMovie(self.movie)
            self.movie.start()
        else:
            self.movie_label.setText("⌛")
            self.movie_label.setStyleSheet("font-size: 40px;")
            self.movie_label.setAlignment(Qt.AlignCenter)
            
        layout.addWidget(self.movie_label, 0, Qt.AlignCenter)

        self.label = QLabel(f"{self.base_message}...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.label, 0, Qt.AlignCenter)
