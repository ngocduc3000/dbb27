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
