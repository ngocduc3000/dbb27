import json

from backend import logger, mock, protocol


def test_logger_writes_one_jsonl_record(tmp_path):
    lg = logger.FrameLogger(str(tmp_path))
    parsed = protocol.parse_frame(mock.generate_frame("normal"))
    record = lg.write(parsed, source="mock")

    path = lg.current_path()
    lines = open(path, encoding="utf-8").read().strip().splitlines()
    assert len(lines) == 1
    saved = json.loads(lines[0])
    assert saved["source"] == "mock"
    assert saved["ok"] is True
    assert "raw_hex" in saved
    assert saved["decoded"]["uf_goal"] == record["decoded"]["uf_goal"]


def test_logger_appends_records(tmp_path):
    lg = logger.FrameLogger(str(tmp_path))
    parsed = protocol.parse_frame(mock.generate_frame("normal"))
    lg.write(parsed, source="mock")
    lg.write(parsed, source="mock")
    lines = open(lg.current_path(), encoding="utf-8").read().strip().splitlines()
    assert len(lines) == 2
