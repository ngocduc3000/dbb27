import random

from backend import mock


class Transport:
    def open(self) -> None: ...
    def close(self) -> None: ...
    def send(self, data: bytes) -> None: ...
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
        self.port = port
        self.baud = baud
        self._ser = None

    def open(self) -> None:
        import serial  # imported lazily so mock-only use needs no hardware libs at import time
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
            timeout=1.0,
        )

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

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
        while time.monotonic() < deadline:
            chunk = self._ser.read(64)
            if chunk:
                buf.extend(chunk)
                if buf.endswith(b"\r\n"):
                    return bytes(buf)
        return bytes(buf)  # may be empty (timeout) or partial; parser will flag it
