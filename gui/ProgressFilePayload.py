import asyncio
import aiohttp

from utils.constants import CHUNK_SIZE


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
