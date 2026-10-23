import asyncio

from gui.ProgressFilePayload import ProgressFilePayload


class DummyWriter:
    def __init__(self):
        self.writes = []

    async def write(self, chunk):
        self.writes.append(chunk)


class FakeSignal:
    def __init__(self):
        self.events = []

    def emit(self, transfer_id, sent, total):
        self.events.append((transfer_id, sent, total))


def test_progress_file_payload_writes_bytes_and_reports_progress(tmp_path):
    target = tmp_path / "payload.bin"
    target.write_bytes(b"abcdefghij")

    signal = FakeSignal()
    payload = ProgressFilePayload(target, "transfer-1", signal)
    writer = DummyWriter()

    asyncio.run(payload.write(writer))

    assert writer.writes == [b"abcdefghij"]
    assert signal.events == [("transfer-1", 10, 10)]


def test_progress_file_payload_decode_rejects_binary_payload(tmp_path):
    target = tmp_path / "payload.bin"
    target.write_bytes(b"hello")

    payload = ProgressFilePayload(target, "transfer-2", FakeSignal())

    try:
        payload.decode()
        assert False, "decode() should raise TypeError for binary payloads"
    except TypeError as exc:
        assert str(exc) == "Binary file payload cannot be decoded"
