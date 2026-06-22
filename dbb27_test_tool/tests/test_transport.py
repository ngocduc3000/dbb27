from backend import protocol, transport


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
