import asyncio
from datetime import datetime

from backend import protocol


class Poller:
    def __init__(self, transport, logger, source, on_result, poll_ms=1000, max_retries=3):
        self.transport = transport
        self.logger = logger
        self.source = source
        self.on_result = on_result
        self.poll_ms = poll_ms
        self.max_retries = max_retries
        self._running = False
        self.frames_total = 0
        self.frames_error = 0

    def stop(self) -> None:
        self._running = False
        # Unblock an in-flight read in the worker thread so run()'s finally can
        # close the port without racing a still-running read.
        self.transport.abort()

    def _status_record(self, message: str, *, connection_error: bool = False) -> dict:
        """Build a UI/log record for a non-frame condition (open failure or no data)."""
        self.frames_total += 1
        self.frames_error += 1
        return {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "source": self.source, "raw_hex": "", "len_recv": None, "len_calc": 0,
            "checksum_recv": None, "checksum_calc": None, "ok": False,
            "field_count": 0, "decoded": {}, "error": message,
            "frames_total": self.frames_total, "frames_error": self.frames_error,
            "connection_error": connection_error,
        }

    def _emit(self, record: dict) -> None:
        self.logger.write_record(record)
        self.on_result(record)

    async def run(self) -> None:
        self._running = True
        try:
            self.transport.open()
        except Exception as exc:  # noqa: BLE001 - report any open failure to the UI
            # SerialTransport.open already raises an actionable, user-facing message;
            # use it as-is rather than wrapping it in another generic prefix.
            self._emit(self._status_record(str(exc), connection_error=True))
            self._running = False
            return
        try:
            while self._running:
                raw = await self._read_with_retry()
                if not self._running:
                    break  # stopped while waiting on a (possibly blocking) read
                if not raw:
                    self._emit(self._status_record(
                        "Không nhận được dữ liệu từ thiết bị (timeout). "
                        "Kiểm tra cổng COM, cáp RS232 và máy DBB-27."))
                    await asyncio.sleep(self.poll_ms / 1000)
                    continue
                parsed = protocol.parse_frame(raw)
                record = self.logger.write(parsed, self.source)
                self.frames_total += 1
                record["frames_total"] = self.frames_total
                if not parsed.ok:
                    self.frames_error += 1
                record["frames_error"] = self.frames_error
                record["connection_error"] = False
                self.on_result(record)
                await asyncio.sleep(self.poll_ms / 1000)
        finally:
            self.transport.close()

    async def _read_with_retry(self) -> bytes:
        last = b""
        for _ in range(self.max_retries):
            if not self._running:
                return last
            self.transport.send(protocol.build_command())
            last = await asyncio.to_thread(self.transport.read_frame, 2.0)
            if last:
                return last
        return last  # empty -> caller reports "no data"
