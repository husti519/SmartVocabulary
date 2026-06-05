from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, Signal

class FocusButton(QPushButton):
    """Custom QPushButton that handles Tab and Enter for custom navigation."""
    tab_pressed = Signal()
    enter_pressed = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab and not (event.modifiers() & Qt.ShiftModifier):
            self.tab_pressed.emit()
            event.accept()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.enter_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)
