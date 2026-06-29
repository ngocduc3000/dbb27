import serial as pyserial
import pytest

from backend import protocol, transport


def test_serial_open_retries_transient_failure_then_succeeds(monkeypatch):
    calls = {"n": 0}

    class FakeSerial:
        def __init__(self, *a, **k):
            calls["n"] += 1
            if calls["n"] < 3:  # first two opens fail like a flaky CH340
                raise pyserial.SerialException(
                    "Cannot configure port ... not functioning")

    monkeypatch.setattr(pyserial, "Serial", FakeSerial)
    t = transport.SerialTransport("COM4", 9600)
    t.open_retry_delay = 0  # don't actually sleep in tests
    t.open()
    assert calls["n"] == 3  # retried until the open succeeded


def test_serial_open_failure_raises_actionable_message(monkeypatch):
    class FakeSerial:
        def __init__(self, *a, **k):
            raise pyserial.SerialException(
                "Cannot configure port, something went wrong. Original message: "
                "PermissionError(13, 'A device attached to the system is not "
                "functioning.', None, 31)")

    monkeypatch.setattr(pyserial, "Serial", FakeSerial)
    t = transport.SerialTransport("COM4", 9600)
    t.open_retry_delay = 0
    with pytest.raises(RuntimeError) as ei:
        t.open()
    msg = str(ei.value)
    assert "COM4" in msg                       # names the offending port
    assert "cắm lại" in msg.lower()            # tells the user what to do
    assert "31" in msg                         # keeps the raw cause for debugging


def test_read_frame_returns_promptly_when_aborted():
    """A wedged device makes read() block; abort() must unblock read_frame fast
    so close() never races an in-flight read on disconnect."""
    import threading
    import time

    class FakeSer:
        def __init__(self):
            self.closed = False

        def read(self, n):
            time.sleep(0.05)
            return b""

        def reset_input_buffer(self):
            pass

        def close(self):
            self.closed = True

    t = transport.SerialTransport("COMX", 9600)
    t._ser = FakeSer()
    threading.Timer(0.2, t.abort).start()
    start = time.monotonic()
    out = t.read_frame(timeout=5.0)  # would block ~5s without abort
    elapsed = time.monotonic() - start
    assert out == b""
    assert elapsed < 1.5  # returned because of abort, not the 5s deadline


def test_mock_transport_returns_parseable_frame():
    t = transport.MockTransport(scenario="normal")
    t.open()
    t.send(protocol.build_command())
    frame = t.read_frame(timeout=1.0)
    t.close()
    p = protocol.parse_frame(frame)
    assert p.ok is True, p.errors


def test_mock_transport_fault_rate_one_produces_bad_frame():
    t = transport.MockTransport(scenario="normal", fault_rate=1.0)
    t.open()
    frame = t.read_frame(timeout=1.0)
    p = protocol.parse_frame(frame)
    assert p.ok is False
