import asyncio
import json
import socket
import threading
import time
import uuid
from pathlib import Path

import aiohttp
import psutil
from aiohttp import web
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


DOWNLOAD_DIR = Path.home() / "Downloads" / "LocalShare"
CHUNK_SIZE = 256 * 1024


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_broadcast_addresses():
    addresses = set()
    interface_stats = psutil.net_if_stats()
    for interface, interface_addresses in psutil.net_if_addrs().items():
        if interface in interface_stats and not interface_stats[interface].isup:
            continue
        for address in interface_addresses:
            if (
                address.family == socket.AF_INET
                and address.broadcast
                and not address.address.startswith("127.")
            ):
                addresses.add(address.broadcast)
    return sorted(addresses) or ["255.255.255.255"]


def get_all_local_ips():
    try:
        hostname = socket.gethostname()
        _, _, ip_addresses = socket.gethostbyname_ex(hostname)
        return ip_addresses
    except Exception:
        return [get_local_ip()]


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


class DropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(154)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Drop files to send")
        title.setObjectName("dropTitle")
        subtitle = QLabel("Files are sent to the selected device on your LAN")
        subtitle.setObjectName("muted")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile() and Path(url.toLocalFile()).is_file()
        ]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()


class NetworkWorker(QThread):
    devices_changed = pyqtSignal(list)
    incoming_started = pyqtSignal(str, str, str)
    transfer_progress = pyqtSignal(str, int, int)
    transfer_finished = pyqtSignal(str, bool, str)
    server_ready = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stop_requested = threading.Event()
        self._loop = None
        self._devices = {}
        self.local_ip = get_local_ip()
        self.local_ips = get_all_local_ips()

    def stop(self):
        self._stop_requested.set()

    def send_files(self, peer, paths, transfer_ids):
        if self._loop is None:
            return
        for path, transfer_id in zip(paths, transfer_ids):
            self._loop.call_soon_threadsafe(
                asyncio.create_task,
                self._send_file(transfer_id, peer, Path(path)),
            )

    async def _send_file(self, transfer_id, peer, path):
        self.transfer_progress.emit(transfer_id, 0, path.stat().st_size)
        try:
            boundary = f"localshare-{uuid.uuid4().hex}"
            writer = aiohttp.MultipartWriter("form-data", boundary=boundary)
            payload = ProgressFilePayload(path, transfer_id, self.transfer_progress)
            writer.append_payload(payload)
            url = f"http://{peer['ip']}:{peer['port']}/upload"
            timeout = aiohttp.ClientTimeout(total=None, connect=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=writer) as response:
                    if response.status >= 400:
                        detail = await response.text()
                        raise RuntimeError(detail or f"HTTP {response.status}")
                    await response.read()
            self.transfer_finished.emit(transfer_id, True, "Sent")
        except Exception as error:
            self.transfer_finished.emit(transfer_id, False, str(error))

    async def _run(self):
        self._loop = asyncio.get_running_loop()
        app = web.Application()
        app.router.add_post("/upload", self._handle_upload)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.server_ready.emit(port)

        tasks = [
            asyncio.create_task(self._listen()),
            asyncio.create_task(self._broadcast(port)),
        ]
        self.status_changed.emit(f"Sharing on {self.local_ip}:{port}")
        try:
            while not self._stop_requested.is_set():
                await asyncio.sleep(0.25)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await runner.cleanup()

    async def _handle_upload(self, request):
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        reader = await request.multipart()
        uploaded = []
        peer = next(
            (device["name"] for device in self._devices.values()
             if device["ip"] == request.remote),
            request.remote or "LAN device",
        )

        while True:
            part = await reader.next()
            if part is None:
                break
            if not part.filename:
                continue

            filename = Path(part.filename).name
            if not filename or filename in (".", ".."):
                continue
            transfer_id = str(uuid.uuid4())
            total = int(part.headers.get("Content-Length", "0") or 0)
            destination = self._unique_destination(filename)
            self.incoming_started.emit(transfer_id, destination.name, peer)
            received = 0
            try:
                with destination.open("wb") as output_file:
                    while True:
                        chunk = await part.read_chunk(CHUNK_SIZE)
                        if not chunk:
                            break
                        output_file.write(chunk)
                        received += len(chunk)
                        self.transfer_progress.emit(transfer_id, received, total)
                uploaded.append(destination.name)
                self.transfer_finished.emit(transfer_id, True, "Received")
            except Exception as error:
                destination.unlink(missing_ok=True)
                self.transfer_finished.emit(transfer_id, False, str(error))
                raise

        if not uploaded:
            return web.json_response({"error": "No files were uploaded"}, status=400)
        return web.json_response({"files": uploaded})

    @staticmethod
    def _unique_destination(filename):
        destination = DOWNLOAD_DIR / filename
        if not destination.exists():
            return destination
        stem, suffix = destination.stem, destination.suffix
        index = 1
        while True:
            candidate = DOWNLOAD_DIR / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    async def _listen(self):
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        receiver.setblocking(False)
        receiver.bind(("", 50000))
        loop = asyncio.get_running_loop()
        try:
            while not self._stop_requested.is_set():
                try:
                    data, address = await asyncio.wait_for(
                        loop.sock_recvfrom(receiver, 1024), timeout=0.5
                    )
                except asyncio.TimeoutError:
                    data = None
                now = time.time()
                if data:
                    try:
                        details = json.loads(data.decode("utf-8"))
                        if address[0] not in self.local_ips and details.get("name"):
                            self._devices[details["name"]] = {
                                "name": details["name"],
                                "ip": address[0],
                                "port": int(details["port"]),
                                "last_ping": now,
                            }
                    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError):
                        pass

                active = {
                    name: device for name, device in self._devices.items()
                    if now - device["last_ping"] < 10
                }
                if active.keys() != self._devices.keys():
                    self._devices = active
                    self.devices_changed.emit(list(active.values()))
                elif data:
                    self.devices_changed.emit(list(active.values()))
        finally:
            receiver.close()

    async def _broadcast(self, port):
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sender.setblocking(False)
        message = json.dumps({"name": socket.gethostname(), "port": port}).encode()
        destinations = get_broadcast_addresses()
        loop = asyncio.get_running_loop()
        try:
            while not self._stop_requested.is_set():
                for destination in destinations:
                    try:
                        await loop.sock_sendto(sender, message, (destination, 50000))
                    except OSError:
                        pass
                await asyncio.sleep(2)
        finally:
            sender.close()

    def run(self):
        try:
            asyncio.run(self._run())
        except OSError as error:
            self.status_changed.emit(f"Network error: {error}")


class ProgressFilePayload(aiohttp.payload.Payload):
    def __init__(self, path, transfer_id, progress_signal):
        super().__init__(path, content_type="application/octet-stream")
        self.path = path
        self.transfer_id = transfer_id
        self.progress_signal = progress_signal
        self._size = path.stat().st_size
        self.set_content_disposition("form-data", name="file", filename=path.name)

    def decode(self, encoding="utf-8"):
        raise TypeError("Binary file payload cannot be decoded")

    async def write(self, writer):
        sent = 0
        with self.path.open("rb") as file:
            while True:
                chunk = await asyncio.to_thread(file.read, CHUNK_SIZE)
                if not chunk:
                    break
                await writer.write(chunk)
                sent += len(chunk)
                self.progress_signal.emit(self.transfer_id, sent, self._size)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LocalShare")
        self.resize(1020, 700)
        self._rows = {}
        self.worker = NetworkWorker()

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
        outer.addWidget(content, 1)

        self.worker.devices_changed.connect(self.update_devices)
        self.worker.incoming_started.connect(self.add_incoming_transfer)
        self.worker.transfer_progress.connect(self.update_transfer_progress)
        self.worker.transfer_finished.connect(self.finish_transfer)
        self.worker.status_changed.connect(self.network_status.setText)
        self.worker.start()
        self.setStyleSheet(STYLESHEET)

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


STYLESHEET = """
QWidget#root { background: #f4f6f5; color: #172321; font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; }
QFrame#sidebar { background: #182925; color: #f1f6f2; }
QLabel#brand { color: #f5fbf7; font-size: 23px; font-weight: 700; padding-bottom: 20px; }
QLabel#sectionLabel { color: #9cafa6; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel#muted { color: #75847e; font-size: 12px; }
QFrame#sidebar QLabel#muted { color: #9cafa6; }
QListWidget#deviceList { background: transparent; border: none; color: #e4eee8; outline: none; }
QListWidget#deviceList::item { padding: 12px 8px; border-radius: 5px; }
QListWidget#deviceList::item:selected { background: #2d423b; color: #b9f2cc; }
QLabel#pageTitle { font-size: 27px; font-weight: 700; }
QLabel#sectionTitle { font-size: 16px; font-weight: 700; }
QPushButton#primaryButton { background: #167d58; color: white; border: none; border-radius: 5px; padding: 10px 16px; font-weight: 600; }
QPushButton#primaryButton:hover { background: #106746; }
QFrame#dropZone { background: #e9efeb; border: 2px dashed #a8bbb0; border-radius: 7px; }
QLabel#dropTitle { color: #214237; font-size: 18px; font-weight: 700; }
QListWidget#queueList { background: transparent; border: none; outline: none; }
QListWidget#queueList::item { background: white; border: 1px solid #dce4df; border-radius: 5px; margin-bottom: 8px; }
QLabel#transferName { font-size: 13px; font-weight: 700; }
QLabel#transferTarget { color: #75847e; font-size: 11px; }
QProgressBar { background: #e8eeea; border: none; border-radius: 3px; height: 6px; text-align: center; }
QProgressBar::chunk { background: #31a373; border-radius: 3px; }
"""


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
