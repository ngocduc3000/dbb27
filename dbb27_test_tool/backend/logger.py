import json
import os
from dataclasses import asdict
from datetime import datetime

from backend import protocol


class FrameLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def current_path(self) -> str:
        name = f"dbb27-{datetime.now():%Y%m%d}.jsonl"
        return os.path.join(self.log_dir, name)

    def write(self, parsed: protocol.ParsedFrame, source: str) -> dict:
        d = asdict(parsed)
        record = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "source": source,
            "raw_hex": d["raw_hex"],
            "len_recv": d["len_recv"],
            "len_calc": d["len_calc"],
            "checksum_recv": d["checksum_recv"],
            "checksum_calc": d["checksum_calc"],
            "ok": d["ok"],
            "field_count": d["field_count"],
            "decoded": d["decoded"],
            "error": "; ".join(d["errors"]) if d["errors"] else None,
        }
        with open(self.current_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record
