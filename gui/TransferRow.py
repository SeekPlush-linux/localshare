from PyQt6.QtWidgets import (
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class TransferRow(QWidget):
    def __init__(self, filename, target, state="Pending"):
        super().__init__()
        self.name_label = QLabel(filename)
        self.name_label.setObjectName("transferName")
        self.target_label = QLabel(f"{target}  |  {state}")
        self.target_label.setObjectName("transferTarget")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)
        layout.addWidget(self.name_label)
        layout.addWidget(self.target_label)
        layout.addWidget(self.progress)

    def set_state(self, state):
        current = self.target_label.text().split("  |  ", 1)[0]
        self.target_label.setText(f"{current}  |  {state}")

    def set_progress(self, completed, total):
        if total <= 0:
            self.progress.setRange(0, 0)
            return
        self.progress.setRange(0, 100)
        self.progress.setValue(min(100, int(completed * 100 / total)))
