import asyncio
import json
import signal
import socket
import time


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]

active_devices = []


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

            if addr[0] in (local_ip, [x['ip'] for x in active_devices]):
                continue

            print(f"Received message from {addr}: {data.decode()}")
            data_dict = json.loads(data.decode())
            active_devices.append({
                'name': data_dict['name'],
                'ip': addr[0],
                'last_ping': time.time()
            })
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
        "port": 8080
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

    try:
        while not stop_event.is_set():
            active_devices = [x for x in active_devices if time.time() - x['last_ping'] < 10]

            print(f"Active Devices: {[x['name'] for x in active_devices]}")
            await asyncio.sleep(1)
    finally:
        listener_task.cancel()
        sender_task.cancel()
        await asyncio.gather(listener_task, sender_task, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Ctrl+C caught, stopping program")
