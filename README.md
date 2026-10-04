# LocalShare

LocalShare is a lightweight desktop app for transferring files between devices on the same local network. It discovers nearby peers over UDP broadcast, lets you select a recipient, and sends files directly over HTTP without requiring a cloud account, login, or external service.

It is designed for quick local transfers between laptops, desktops, or other devices on the same Wi‑Fi or LAN.

![App Showcase](/assets/demo.png)

## Features

- Discover nearby devices on the same network automatically
- Send one or many files to a selected device
- Receive incoming files and save them into a configurable download folder
- Track transfer progress and status in a queue
- Light and dark themes
- Works without a central server or cloud dependency

## How it works

LocalShare uses:

- UDP broadcast discovery to find peers on the local LAN
- HTTP multipart uploads for file transfer
- PyQt6 for the desktop interface
- Python standard library networking utilities for local peer detection

Each device announces itself on the LAN, and the app shows the discovered peers in a sidebar. Once a device is selected, you can drag files onto the transfer area or choose them manually from the file picker.

## Requirements

- Python 3.10 or newer
- A local network (same Wi‑Fi, Ethernet segment, or LAN)

## Installation

You can either get the pre-built binaries from [Releases](https://github.com/SeekPlush-linux/localshare/releases), or do the following:

1. Clone the repository:

   ```bash
   git clone https://github.com/SeekPlush-linux/localshare.git
   cd localshare
   ```

2. (Highly recommended for Linux users) Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Running the app

Start the application with:

```bash
python main.py
```

## Typical workflow

1. Launch LocalShare on each device you want to use.
2. Ensure both devices are on the same network.
3. Wait for the device list to populate.
4. Select the destination device.
5. Drag files into the drop zone or click “Choose files…”.
6. Watch the transfer queue for progress.
7. Received files appear in the configured download directory.

## Download folder

By default, received files are saved to:

```bash
~/Downloads/LocalShare
```

You can change this in the app’s Settings page.

## Dependencies

The project uses:

- PyQt6 for the desktop interface
- aiohttp for HTTP file transfer
- psutil for network interface detection

These are listed in [requirements.txt](requirements.txt).

## Notes

- This app is intended for local-network sharing and does not route through a central server.
- Device discovery depends on UDP broadcast support being available on your network.
- If no devices appear, confirm both devices are connected to the same network and the firewall allows local traffic on the application’s ports.

## License

This project is distributed under the MIT license. See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome. If you want to improve the app, please open an issue or submit a pull request with a clear description of the change.
