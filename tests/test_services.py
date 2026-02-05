from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services import build_invoice_name, collect_input_fields, render_invoice_lines


def test_build_invoice_name_increments(tmp_path):
    (tmp_path / "invoice_20260101_0001.docx").write_text("x", encoding="utf-8")
    (tmp_path / "invoice_20260101_0002.docx").write_text("x", encoding="utf-8")

    result = build_invoice_name(now=datetime(2026, 1, 1), output_dir=tmp_path)

    assert result == "invoice_20260101_0003"


def test_collect_input_fields_and_render_lines():
    blocks = [
        {"kind": "static", "identifier": "", "text": "Счет", "immutable": True},
        {"kind": "field", "identifier": "client_name", "text": "", "immutable": False},
        {"kind": "field", "identifier": "total", "text": "100", "immutable": True},
    ]

    fields = collect_input_fields(blocks)
    lines = render_invoice_lines(blocks, {"client_name": "ООО Вектор"})

    assert fields == [{"identifier": "client_name", "label": "Client name"}]
    assert lines == ["Счет", "ООО Вектор", "100"]
