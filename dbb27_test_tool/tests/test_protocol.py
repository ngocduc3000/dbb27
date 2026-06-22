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
