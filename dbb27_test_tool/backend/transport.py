import random

from backend import mock


class Transport:
    def open(self) -> None: ...
    def close(self) -> None: ...
    def send(self, data: bytes) -> None: ...
    def abort(self) -> None:
        """Signal an in-flight read_frame to return ASAP (called from another
        thread on disconnect). No-op for transports whose read never blocks."""
    def read_frame(self, timeout: float) -> bytes:
        raise NotImplementedError


class MockTransport(Transport):
    def __init__(self, scenario: str = "normal", fault_rate: float = 0.0,
                 alarms: list[str] | None = None):
        self.scenario = scenario
        self.fault_rate = fault_rate
        self.alarms = alarms or []

    def read_frame(self, timeout: float) -> bytes:
        inject = random.random() < self.fault_rate
        return mock.generate_frame(self.scenario, inject_fault=inject, alarms=self.alarms)


class SerialTransport(Transport):
    def __init__(self, port: str, baud: int = 9600):
        import threading
        self.port = port
        self.baud = baud
        self._ser = None
        self._stop = threading.Event()  # set by abort() to break the read loop
        self.open_retries = 3        # USB-serial adapters (e.g. CH340) often fail
        self.open_retry_delay = 0.5  # the first configure attempt, then succeed
        self.read_slice = 0.2        # per-read timeout: short so abort/stop is prompt

    def abort(self) -> None:
        self._stop.set()

    def _friendly_open_error(self, exc: Exception) -> str:
        """Turn a raw pyserial open failure into actionable Vietnamese guidance.

        Windows reports a wedged/flaky USB-serial adapter as PermissionError(13)
        'device is not functioning' (error 31) or 'Access is denied' — neither of
        which reads as a hardware problem to a user, so spell out what to try.
        """
        raw = str(exc)
        low = raw.lower()
        port_unusable = (
            "not functioning" in low or "access is denied" in low
            or "permissionerror" in low or "could not open port" in low
            or "denied" in low or "31" in low or "13" in low
        )
        if port_unusable:
            return (
                f"Không mở được {self.port}. Cổng đang bận hoặc adapter USB-Serial chập chờn. "
                f"Hãy thử: (1) rút và cắm lại adapter (ưu tiên cổng USB khác, cắm thẳng không qua hub); "
                f"(2) đóng phần mềm khác đang dùng {self.port}; (3) thử cáp USB khác. "
                f"Chi tiết: {raw}"
            )
        return f"Không mở được {self.port}: {raw}"

    def open(self) -> None:
        import serial  # imported lazily so mock-only use needs no hardware libs at import time
        import time
        self._stop.clear()  # fresh session: forget any prior abort
        last_exc: Exception | None = None
        for attempt in range(self.open_retries):
            try:
                self._ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baud,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False,
                    timeout=self.read_slice,  # short slices keep abort/stop responsive
                )
                return
            except serial.SerialException as exc:
                last_exc = exc
                self._ser = None
                if attempt < self.open_retries - 1:
                    time.sleep(self.open_retry_delay)
        raise RuntimeError(self._friendly_open_error(last_exc)) from last_exc

    def close(self) -> None:
        ser, self._ser = self._ser, None
        if ser is not None:
            try:
                ser.close()
            except Exception:  # noqa: BLE001 - closing a wedged USB port can raise; never propagate
                pass

    def send(self, data: bytes) -> None:
        if self._ser is None:
            raise RuntimeError("Serial port chưa mở")
        self._ser.reset_input_buffer()
        self._ser.write(data)

    def read_frame(self, timeout: float) -> bytes:
        import time
        if self._ser is None:
            raise RuntimeError("Serial port chưa mở")
        deadline = time.monotonic() + timeout
        buf = bytearray()
        # Stop as soon as abort() fires so close() never races an in-flight read.
        while time.monotonic() < deadline and not self._stop.is_set():
            chunk = self._ser.read(64)
            if chunk:
                buf.extend(chunk)
                if buf.endswith(b"\r\n"):
                    return bytes(buf)
        return bytes(buf)  # may be empty (timeout/abort) or partial; parser will flag it
