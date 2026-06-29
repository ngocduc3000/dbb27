import asyncio

from backend import logger, poller, transport


def test_poller_emits_results_and_counts(tmp_path):
    results = []
    t = transport.MockTransport(scenario="normal")
    lg = logger.FrameLogger(str(tmp_path))
    p = poller.Poller(t, lg, source="mock", on_result=results.append, poll_ms=10)

    async def drive():
        task = asyncio.create_task(p.run())
        await asyncio.sleep(0.1)
        p.stop()
        await task

    asyncio.run(drive())
    assert p.frames_total >= 2
    assert len(results) == p.frames_total
    assert results[0]["ok"] is True


def test_poller_stop_aborts_the_transport(tmp_path):
    """stop() must signal the transport to abort any in-flight read, otherwise a
    blocking read keeps a worker thread (and the COM port) alive after disconnect."""
    class _AbortRecordingTransport(transport.Transport):
        def __init__(self):
            self.aborted = False

        def read_frame(self, timeout: float) -> bytes:
            return b""

        def abort(self) -> None:
            self.aborted = True

    t = _AbortRecordingTransport()
    lg = logger.FrameLogger(str(tmp_path))
    p = poller.Poller(t, lg, source="serial", on_result=lambda r: None, poll_ms=10)
    p.stop()
    assert t.aborted is True


class _BoomTransport(transport.Transport):
    def open(self):
        raise RuntimeError("COM không tồn tại")

    def close(self):
        pass


def test_poller_emits_error_when_open_fails(tmp_path):
    results = []
    lg = logger.FrameLogger(str(tmp_path))
    p = poller.Poller(_BoomTransport(), lg, source="serial", on_result=results.append, poll_ms=10)

    asyncio.run(p.run())

    assert len(results) == 1
    rec = results[0]
    assert rec["ok"] is False
    assert rec["connection_error"] is True
    assert "COM không tồn tại" in rec["error"]


class _SilentTransport(transport.Transport):
    """Opens fine but never returns data (simulates wrong device / dead line)."""
    def read_frame(self, timeout: float) -> bytes:
        return b""


def test_poller_reports_no_data(tmp_path):
    results = []
    lg = logger.FrameLogger(str(tmp_path))
    p = poller.Poller(_SilentTransport(), lg, source="serial", on_result=results.append, poll_ms=10)

    async def drive():
        task = asyncio.create_task(p.run())
        await asyncio.sleep(0.08)
        p.stop()
        await task

    asyncio.run(drive())
    assert len(results) >= 1
    assert all(r["ok"] is False for r in results)
    assert "Không nhận được dữ liệu" in results[0]["error"]
