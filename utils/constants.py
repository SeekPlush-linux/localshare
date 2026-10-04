from pathlib import Path


DOWNLOAD_DIR = Path.home() / "Downloads" / "LocalShare"
CHUNK_SIZE = 256 * 1024

LIGHT_STYLESHEET = """
QWidget#root { background: #f4f6f5; color: #172321; font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; }
QFrame#sidebar { background: #182925; color: #f1f6f2; }
QLabel#brand { color: #f5fbf7; font-size: 23px; font-weight: 700; padding-bottom: 20px; }
QLabel#sectionLabel { color: #9cafa6; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel { color: #000000; }
QLabel#muted { color: #75847e; font-size: 12px; }
QFrame#sidebar QLabel#muted { color: #9cafa6; }
QPushButton#navButton { background: transparent; color: #dbe7e0; border: none; border-radius: 4px; padding: 9px 8px; text-align: left; }
QPushButton#navButton:hover { background: #2d423b; color: #b9f2cc; }
QListWidget#deviceList { background: transparent; border: none; color: #e4eee8; outline: none; }
QListWidget#deviceList::item { padding: 12px 8px; border-radius: 5px; }
QListWidget#deviceList::item:selected { background: #2d423b; color: #b9f2cc; }
QLabel#pageTitle { color: #000000; font-size: 27px; font-weight: 700; }
QLabel#sectionTitle { color: #000000; font-size: 16px; font-weight: 700; }
QPushButton { background: #e5ebe7; color: #21352d; border: 1px solid #cbd6cf; border-radius: 5px; padding: 9px 14px; }
QPushButton:hover { background: #d9e3dc; }
QPushButton:focus { border: none; }
QPushButton#primaryButton { background: #167d58; color: white; border: none; border-radius: 5px; padding: 10px 16px; font-weight: 600; }
QPushButton#primaryButton:hover { background: #106746; }
QLineEdit#downloadPath, QComboBox { background: white; color: #172321; border: 1px solid #cbd6cf; border-radius: 4px; padding: 8px; }
QComboBox QAbstractItemView { background: white; color: #172321; border: 1px solid #cbd6cf; }
QFrame#dropZone { background: #e9efeb; border: 2px dashed #a8bbb0; border-radius: 7px; }
QLabel#dropTitle { color: #214237; font-size: 18px; font-weight: 700; }
QListWidget#queueList { background: transparent; border: none; outline: none; }
QListWidget#queueList::item { background: white; border: 1px solid #dce4df; border-radius: 5px; margin-bottom: 8px; }
QLabel#transferName { font-size: 13px; font-weight: 700; }
QLabel#transferTarget { color: #75847e; font-size: 11px; }
QProgressBar { background: #e8eeea; border: none; border-radius: 3px; height: 6px; text-align: center; }
QProgressBar::chunk { background: #31a373; border-radius: 3px; }
"""

DARK_STYLESHEET = """
QWidget#root { background: #202a27; color: #e7eeea; font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; }
QFrame#sidebar { background: #121c19; color: #f1f6f2; }
QLabel#brand { color: #f5fbf7; font-size: 23px; font-weight: 700; padding-bottom: 20px; }
QLabel#sectionLabel { color: #9cafa6; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel { color: #f5fbf7; }
QLabel#muted { color: #a4b2ac; font-size: 12px; }
QFrame#sidebar QLabel#muted { color: #9cafa6; }
QPushButton#navButton { background: transparent; color: #dbe7e0; border: none; border-radius: 4px; padding: 9px 8px; text-align: left; }
QPushButton#navButton:hover { background: #2d423b; color: #b9f2cc; }
QListWidget#deviceList { background: transparent; border: none; color: #e4eee8; outline: none; }
QListWidget#deviceList::item { padding: 12px 8px; border-radius: 5px; }
QListWidget#deviceList::item:selected { background: #2d423b; color: #b9f2cc; }
QLabel#pageTitle { color: #f5fbf7; font-size: 27px; font-weight: 700; }
QLabel#sectionTitle { color: #f5fbf7; font-size: 16px; font-weight: 700; }
QPushButton { background: #34433d; color: #e7eeea; border: 1px solid #50625a; border-radius: 5px; padding: 9px 14px; }
QPushButton:hover { background: #40534a; }
QPushButton:focus { border: none; }
QPushButton#primaryButton { background: #208960; color: white; border: none; border-radius: 5px; padding: 10px 16px; font-weight: 600; }
QPushButton#primaryButton:hover { background: #2b9b70; }
QLineEdit#downloadPath, QComboBox { background: #293631; color: #e7eeea; border: 1px solid #50625a; border-radius: 4px; padding: 8px; }
QComboBox QAbstractItemView { background: #293631; color: #e7eeea; border: 1px solid #50625a; }
QFrame#dropZone { background: #293631; border: 2px dashed #60766a; border-radius: 7px; }
QLabel#dropTitle { color: #b9f2cc; font-size: 18px; font-weight: 700; }
QListWidget#queueList { background: transparent; border: none; outline: none; }
QListWidget#queueList::item { background: #293631; border: 1px solid #40534a; border-radius: 5px; margin-bottom: 8px; }
QLabel#transferName { font-size: 13px; font-weight: 700; }
QLabel#transferTarget { color: #a4b2ac; font-size: 11px; }
QProgressBar { background: #34433d; border: none; border-radius: 3px; height: 6px; text-align: center; }
QProgressBar::chunk { background: #42bd89; border-radius: 3px; }
"""
