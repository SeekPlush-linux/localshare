import uuid
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from utils.constants import DOWNLOAD_DIR, LIGHT_STYLESHEET, DARK_STYLESHEET
from gui.TransferRow import TransferRow
from gui.NetworkWorker import NetworkWorker
from gui.DropZone import DropZone


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LocalShare")
        self.resize(1020, 700)
        self._rows = {}
        self.settings = QSettings("SeekPlush-linux", "LocalShare")
        self.download_dir = Path(
            self.settings.value("download_dir", str(DOWNLOAD_DIR))
        ).expanduser()
        self.theme = self.settings.value("theme", "Light")
        if self.theme not in ("Light", "Dark"):
            self.theme = "Light"
        self.worker = NetworkWorker(self.download_dir)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(270)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 24, 16, 18)
        side_layout.setSpacing(12)
        brand = QLabel("LocalShare")
        brand.setObjectName("brand")
        side_layout.addWidget(brand)
        self.home_button = QPushButton("Send files")
        self.home_button.setObjectName("navButton")
        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("navButton")
        self.about_button = QPushButton("About")
        self.about_button.setObjectName("navButton")
        side_layout.addWidget(self.home_button)
        side_layout.addWidget(self.settings_button)
        side_layout.addWidget(self.about_button)
        side_layout.addWidget(QLabel("NEARBY DEVICES", objectName="sectionLabel"))
        self.device_list = QListWidget()
        self.device_list.setObjectName("deviceList")
        self.device_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        side_layout.addWidget(self.device_list, 1)
        self.network_status = QLabel("Finding devices on your network…")
        self.network_status.setObjectName("muted")
        self.network_status.setWordWrap(True)
        side_layout.addWidget(self.network_status)
        outer.addWidget(sidebar)

        self.pages = QStackedWidget()
        outer.addWidget(self.pages, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 28, 32, 24)
        content_layout.setSpacing(18)
        heading = QHBoxLayout()
        title = QLabel("Send files")
        title.setObjectName("pageTitle")
        self.add_button = QPushButton("Choose files…")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.choose_files)
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(self.add_button)
        content_layout.addLayout(heading)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.queue_files)
        content_layout.addWidget(self.drop_zone)

        queue_heading = QHBoxLayout()
        queue_title = QLabel("Transfer Queue")
        queue_title.setObjectName("sectionTitle")
        self.queue_count = QLabel("0 transfers")
        self.queue_count.setObjectName("muted")
        queue_heading.addWidget(queue_title)
        queue_heading.addStretch(1)
        queue_heading.addWidget(self.queue_count)
        content_layout.addLayout(queue_heading)
        self.queue_list = QListWidget()
        self.queue_list.setObjectName("queueList")
        content_layout.addWidget(self.queue_list, 1)
        self.pages.addWidget(content)

        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(32, 28, 32, 24)
        settings_layout.setSpacing(18)
        settings_title = QLabel("Settings")
        settings_title.setObjectName("pageTitle")
        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(QLabel("Appearance", objectName="sectionTitle"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.theme)
        self.theme_combo.currentTextChanged.connect(self.set_theme)
        settings_layout.addWidget(QLabel("Color mode"))
        settings_layout.addWidget(self.theme_combo)
        settings_layout.addSpacing(12)
        settings_layout.addWidget(QLabel("Downloads", objectName="sectionTitle"))
        settings_layout.addWidget(QLabel("Folder for files received from nearby devices"))
        folder_row = QHBoxLayout()
        self.download_path = QLineEdit(str(self.download_dir))
        self.download_path.setObjectName("downloadPath")
        self.download_path.setClearButtonEnabled(True)
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self.browse_download_dir)
        folder_row.addWidget(self.download_path, 1)
        folder_row.addWidget(browse_button)
        settings_layout.addLayout(folder_row)
        save_button = QPushButton("Save folder")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save_download_dir)
        settings_layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.settings_status = QLabel("")
        self.settings_status.setObjectName("muted")
        settings_layout.addWidget(self.settings_status)
        settings_layout.addStretch(1)
        self.pages.addWidget(settings_page)

        about_page = QWidget()
        about_layout = QVBoxLayout(about_page)
        about_layout.setContentsMargins(32, 28, 32, 24)
        about_layout.setSpacing(16)
        about_title = QLabel("About LocalShare")
        about_title.setObjectName("pageTitle")
        about_layout.addWidget(about_title)
        about_layout.addWidget(QLabel("LocalShare", objectName="sectionTitle"))
        about_description = QLabel(
            "A simple peer-to-peer file sharing app for devices on your local network. "
            "Discover nearby devices and send files without a cloud account."
        )
        about_description.setObjectName("muted")
        about_description.setWordWrap(True)
        about_layout.addWidget(about_description)
        repository_button = QPushButton("View project on GitHub")
        repository_button.setObjectName("primaryButton")
        repository_button.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/SeekPlush-linux/localshare")
            )
        )
        about_layout.addWidget(repository_button, alignment=Qt.AlignmentFlag.AlignLeft)
        about_layout.addStretch(1)
        self.pages.addWidget(about_page)

        self.home_button.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.settings_button.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.about_button.clicked.connect(lambda: self.pages.setCurrentIndex(2))

        self.worker.devices_changed.connect(self.update_devices)
        self.worker.incoming_started.connect(self.add_incoming_transfer)
        self.worker.transfer_progress.connect(self.update_transfer_progress)
        self.worker.transfer_finished.connect(self.finish_transfer)
        self.worker.status_changed.connect(self.network_status.setText)
        self.worker.start()
        self.apply_theme()

    def set_theme(self, theme):
        self.theme = theme
        self.settings.setValue("theme", theme)
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(DARK_STYLESHEET if self.theme == "Dark" else LIGHT_STYLESHEET)

    def browse_download_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Choose download folder", self.download_path.text()
        )
        if directory:
            self.download_path.setText(directory)
            self.save_download_dir()

    def save_download_dir(self):
        value = self.download_path.text().strip()
        if not value:
            self.settings_status.setText("Choose a folder path first.")
            return
        self.download_dir = Path(value).expanduser()
        self.worker.download_dir = self.download_dir
        self.settings.setValue("download_dir", str(self.download_dir))
        self.download_path.setText(str(self.download_dir))
        self.settings_status.setText("Download folder saved.")

    def choose_files(self):
        filenames, _ = QFileDialog.getOpenFileNames(self, "Choose files")
        if filenames:
            self.queue_files([Path(name) for name in filenames])

    def queue_files(self, paths):
        item = self.device_list.currentItem()
        if item is None:
            self.network_status.setText("Select a nearby device before adding files.")
            return
        peer = item.data(Qt.ItemDataRole.UserRole)
        valid_paths = [path for path in paths if path.is_file()]
        if not valid_paths:
            return
        transfer_ids = []
        for path in valid_paths:
            transfer_id = str(uuid.uuid4())
            transfer_ids.append(transfer_id)
            self._add_transfer(transfer_id, path.name, peer["name"], "Pending")
        self.worker.send_files(peer, valid_paths, transfer_ids)

    def _add_transfer(self, transfer_id, filename, target, state):
        row = TransferRow(filename, target, state)
        item = QListWidgetItem()
        item.setSizeHint(row.sizeHint())
        self.queue_list.addItem(item)
        self.queue_list.setItemWidget(item, row)
        self._rows[transfer_id] = row
        self.queue_count.setText(f"{len(self._rows)} transfers")

    def add_incoming_transfer(self, transfer_id, filename, peer):
        self._add_transfer(transfer_id, filename, peer, "Receiving")

    def update_transfer_progress(self, transfer_id, completed, total):
        row = self._rows.get(transfer_id)
        if row:
            row.set_state("Transferring")
            row.set_progress(completed, total)

    def finish_transfer(self, transfer_id, success, detail):
        row = self._rows.get(transfer_id)
        if row:
            row.set_state(detail if success else f"Failed: {detail}")
            row.progress.setRange(0, 100)
            row.progress.setValue(100 if success else row.progress.value())

    def update_devices(self, devices):
        selected = self.device_list.currentItem()
        selected_name = selected.data(Qt.ItemDataRole.UserRole)["name"] if selected else None
        self.device_list.clear()
        for peer in sorted(devices, key=lambda device: device["name"].lower()):
            item = QListWidgetItem(f">  {peer['name']}\n    {peer['ip']}")
            item.setData(Qt.ItemDataRole.UserRole, peer)
            self.device_list.addItem(item)
            if peer["name"] == selected_name:
                self.device_list.setCurrentItem(item)
        if devices:
            self.network_status.setText(f"{len(devices)} device(s) found")
        elif self.worker.isRunning():
            self.network_status.setText("Finding devices on your network…")

    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait(3000)
        super().closeEvent(event)
