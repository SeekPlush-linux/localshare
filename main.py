import asyncio
import json
import signal
import socket
import time
from pathlib import Path

from aiohttp import web


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]

with socket.socket() as s:
    for i in range(8080, 40000):
        try:
            s.bind(("127.0.0.1", i))
            http_port = i
            break
        except socket.error:
            continue

active_devices = {}
DOWNLOAD_DIR = Path.home() / 'Downloads' / 'LocalShare'


async def upload(request):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    reader = await request.multipart()
    uploaded_files = []

    while True:
        part = await reader.next()
        if part is None:
            break
        if not part.filename:
            continue

        filename = Path(part.filename).name
        if not filename or filename in ('.', '..'):
            continue

        destination = DOWNLOAD_DIR / filename
        with destination.open('wb') as output_file:
            while True:
                chunk = await part.read_chunk()
                if not chunk:
                    break
                output_file.write(chunk)
        uploaded_files.append(filename)

    if not uploaded_files:
        return web.json_response({'error': 'No files were uploaded'}, status=400)
    return web.json_response({'files': uploaded_files})


async def http_server(stop_event):
    app = web.Application()
    app.router.add_post('/upload', upload)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', http_port)
    await site.start()

    print(f"Running HTTP server at port {http_port}")

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        print("Stopping HTTP server...")
    finally:
        await runner.cleanup()


async def listener(stop_event):
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    receiver_socket.setblocking(False)
    receiver_socket.bind(('', 50000))
    loop = asyncio.get_running_loop()

    try:
        while not stop_event.is_set():
            try:
                data, addr = await loop.sock_recvfrom(receiver_socket, 1024)
            except BlockingIOError:
                await asyncio.sleep(0.1)
                continue

            if addr[0] in (local_ip, [x['ip'] for x in active_devices.values()]):
                continue

            print(f"Received message from {addr}: {data.decode()}")
            data_dict = json.loads(data.decode())

            active_devices[data_dict['name']] = {
                'ip': addr[0],
                'last_ping': time.time()
            }
    except asyncio.CancelledError:
        print("Stopping receiver...")
    finally:
        receiver_socket.close()


async def broadcast_presence(stop_event):
    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sender_socket.setblocking(False)
    loop = asyncio.get_running_loop()

    msg = json.dumps({
        "name": socket.gethostname(),
        "port": http_port
    }).encode()

    try:
        while not stop_event.is_set():
            try:
                await loop.sock_sendto(sender_socket, msg, ('<broadcast>', 50000))
            except BlockingIOError:
                await asyncio.sleep(0.1)
                continue

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass
    except asyncio.CancelledError:
        print("Stopping sender...")
    finally:
        sender_socket.close()


async def main():
    global active_devices

    print("LocalShare\n")
    stop_event = asyncio.Event()

    def request_shutdown():
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, request_shutdown)

    print("Starting listener")
    listener_task = asyncio.create_task(listener(stop_event))

    print("Starting sender")
    sender_task = asyncio.create_task(broadcast_presence(stop_event))

    print("Starting HTTP server")
    server_task = asyncio.create_task(http_server(stop_event))

    try:
        while not stop_event.is_set():
            now = time.time()
            active_devices = {
                name: device
                for name, device in active_devices.items()
                if now - device['last_ping'] < 10
            }

            print(f"Active Devices: {list(active_devices.keys())}")
            await asyncio.sleep(1)
    finally:
        listener_task.cancel()
        sender_task.cancel()
        server_task.cancel()
        await asyncio.gather(
            listener_task,
            sender_task,
            server_task,
            return_exceptions=True,
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Ctrl+C caught, stopping program")
