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
