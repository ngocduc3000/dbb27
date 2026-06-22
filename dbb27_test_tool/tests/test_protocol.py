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
