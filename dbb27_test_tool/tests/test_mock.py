from backend import mock, protocol


def test_encode_decimal5_is_5_chars():
    assert mock.encode_decimal5(2.35, 2) == "02.35"
    assert mock.encode_decimal5(500, 0) == "00500"
    assert mock.encode_decimal5(-146, 0) == "-0146"


def test_generated_normal_frame_parses_ok():
    frame = mock.generate_frame("normal")
    p = protocol.parse_frame(frame)
    assert p.ok is True, p.errors
    assert p.field_count == 31
    assert p.checksum_recv == p.checksum_calc


def test_alarm_scenario_sets_an_alarm_flag():
    frame = mock.generate_frame("alarm")
    p = protocol.parse_frame(frame)
    alarms = [v for k, v in p.decoded.items() if k.startswith("alarm_")]
    assert any(alarms) is True


def test_bad_frame_scenario_does_not_parse_ok():
    frame = mock.generate_frame("bad_frame")
    p = protocol.parse_frame(frame)
    assert p.ok is False


def test_alarm_keys_lists_all_nine_alarms():
    assert len(mock.ALARM_IDS) == 9
    assert "alarm_blood_leak" in mock.ALARM_IDS
    assert "alarm_bp" in mock.ALARM_IDS


def test_explicit_alarms_activate_only_those_flags():
    frame = mock.generate_frame("normal", alarms=["alarm_blood_leak", "alarm_tmp"])
    p = protocol.parse_frame(frame)
    assert p.decoded["alarm_blood_leak"] is True
    assert p.decoded["alarm_tmp"] is True
    assert p.decoded["alarm_air"] is False
    assert p.decoded["alarm_conductivity"] is False


def test_no_alarms_means_all_flags_false():
    frame = mock.generate_frame("normal")
    p = protocol.parse_frame(frame)
    assert all(v is False for k, v in p.decoded.items() if k.startswith("alarm_"))
