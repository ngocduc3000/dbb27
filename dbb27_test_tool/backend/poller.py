import asyncio

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

    async def run(self) -> None:
        self._running = True
        self.transport.open()
        try:
            while self._running:
                raw = await self._read_with_retry()
                parsed = protocol.parse_frame(raw)
                record = self.logger.write(parsed, self.source)
                self.frames_total += 1
                record["frames_total"] = self.frames_total
                if not parsed.ok:
                    self.frames_error += 1
                record["frames_error"] = self.frames_error
                self.on_result(record)
                await asyncio.sleep(self.poll_ms / 1000)
        finally:
            self.transport.close()

    async def _read_with_retry(self) -> bytes:
        last = b""
        for _ in range(self.max_retries):
            self.transport.send(protocol.build_command())
            last = await asyncio.to_thread(self.transport.read_frame, 2.0)
            if last:
                return last
        return last  # empty -> parser flags it as error
