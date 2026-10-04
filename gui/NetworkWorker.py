import asyncio
import json
import socket
import threading
import time
import uuid
import aiohttp
from pathlib import Path
from aiohttp import web

from PyQt6.QtCore import QThread, pyqtSignal

from utils.constants import CHUNK_SIZE
from utils.functions import get_local_ip, get_broadcast_addresses, get_all_local_ips
from gui.ProgressFilePayload import ProgressFilePayload


class NetworkWorker(QThread):
    devices_changed = pyqtSignal(list)
    incoming_started = pyqtSignal(str, str, str)
    transfer_progress = pyqtSignal(str, int, int)
    transfer_finished = pyqtSignal(str, bool, str)
    server_ready = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self, download_dir):
        super().__init__()
        self._stop_requested = threading.Event()
        self._loop = None
        self._devices = {}
        self.download_dir = download_dir
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
            self.download_dir.mkdir(parents=True, exist_ok=True)
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

    def _unique_destination(self, filename):
        destination = self.download_dir / filename
        if not destination.exists():
            return destination
        stem, suffix = destination.stem, destination.suffix
        index = 1
        while True:
            candidate = self.download_dir / f"{stem} ({index}){suffix}"
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
