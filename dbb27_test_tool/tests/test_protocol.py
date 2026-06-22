from backend import protocol


def test_build_command_is_K_cr_lf():
    assert protocol.build_command() == b"K\r\n"


def test_registry_has_31_fields_with_unique_ids():
    assert len(protocol.FIELD_REGISTRY) == 31
    ids = [f.id for f in protocol.FIELD_REGISTRY]
    assert len(set(ids)) == 31


def test_registry_lookup_by_id():
    assert protocol.FIELDS_BY_ID["A"].key == "uf_goal"
    assert protocol.FIELDS_BY_ID["A"].size == 5
    assert protocol.FIELDS_BY_ID["f"].key == "alarm_air"
    assert protocol.FIELDS_BY_ID["f"].kind == "flag1"
    assert protocol.FIELDS_BY_ID["N"].key == "treatment_mode"


def test_checksum_low_byte_two_hex_lowercase():
    # bytes summing to 0x5a -> "5a"
    payload = bytes([0x30, 0x2a])  # 48 + 42 = 90 = 0x5a
    assert protocol.compute_checksum(payload) == "5a"


def test_checksum_wraps_at_256():
    payload = bytes([0xff, 0x02])  # 257 & 0xff = 1 -> "01"
    assert protocol.compute_checksum(payload) == "01"


def test_decode_decimal5_positive_with_point():
    f = protocol.FIELDS_BY_ID["A"]
    assert protocol.decode_value(f, "02.35") == 2.35


def test_decode_decimal5_negative_integer():
    f = protocol.FIELDS_BY_ID["I"]  # dialysate pressure can be negative
    assert protocol.decode_value(f, "-0146") == -146.0


def test_decode_flag_true_false():
    f = protocol.FIELDS_BY_ID["f"]  # air alarm
    assert protocol.decode_value(f, "1") is True
    assert protocol.decode_value(f, "0") is False


def test_decode_unused_is_none():
    f = protocol.FIELDS_BY_ID["O"]
    assert protocol.decode_value(f, "00000") is None


def test_decode_bptime_keeps_raw_string():
    f = protocol.FIELDS_BY_ID["S"]
    assert protocol.decode_value(f, "43205") == "43205"


def _build_valid_frame() -> bytes:
    # Minimal hand-built RES-DATA with two fields: A (uf_goal) and f (air alarm)
    res = b"A02.35" + b"f1"
    length = f"{len(res):03d}".encode("ascii")
    payload = protocol.STX + length + res
    checksum = protocol.compute_checksum(payload).encode("ascii")
    return payload + checksum + protocol.ETX


def test_parse_valid_partial_frame():
    frame = _build_valid_frame()
    p = protocol.parse_frame(frame)
    assert p.ok is True
    assert p.errors == []
    assert p.decoded["uf_goal"] == 2.35
    assert p.decoded["alarm_air"] is True
    assert p.field_count == 2
    assert p.checksum_recv == p.checksum_calc


def test_parse_bad_checksum_flags_error_but_still_decodes():
    frame = bytearray(_build_valid_frame())
    # corrupt the first checksum char (second to last before CR LF)
    frame[-4] = ord("0") if chr(frame[-4]) != "0" else ord("1")
    p = protocol.parse_frame(bytes(frame))
    assert p.ok is False
    assert any("checksum" in e.lower() for e in p.errors)
    assert p.decoded["uf_goal"] == 2.35  # still decoded


def test_parse_missing_stx():
    p = protocol.parse_frame(b"XX003A02.35..\r\n")
    assert p.ok is False
    assert any("stx" in e.lower() for e in p.errors)


def test_parse_unknown_id_stops_and_flags():
    res = b"Z12345"  # 'Z' not in registry
    length = f"{len(res):03d}".encode("ascii")
    payload = protocol.STX + length + res
    frame = payload + protocol.compute_checksum(payload).encode("ascii") + protocol.ETX
    p = protocol.parse_frame(frame)
    assert p.ok is False
    assert any("unknown id" in e.lower() for e in p.errors)
