from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def ensure_storage() -> Path:
    root = Path(__file__).resolve().parent / "data"
    (root / "templates").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)
    return root


def list_templates() -> list[dict[str, Any]]:
    templates_dir = ensure_storage() / "templates"
    result: list[dict[str, Any]] = []
    for file_path in sorted(templates_dir.glob("*.json")):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        result.append(
            {
                "id": data["id"],
                "title": data["title"],
                "created_at": data["created_at"],
            }
        )
    return result


def save_template(title: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    templates_dir = ensure_storage() / "templates"
    payload = {
        "id": uuid4().hex[:10],
        "title": title,
        "blocks": blocks,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    target = templates_dir / f"{payload['id']}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_template(template_id: str) -> dict[str, Any] | None:
    target = ensure_storage() / "templates" / f"{template_id}.json"
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def collect_input_fields(blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for block in blocks:
        if block.get("kind") == "field" and not block.get("immutable", False):
            fields.append(
                {
                    "identifier": block["identifier"],
                    "label": block["identifier"].replace("_", " ").capitalize(),
                }
            )
    unique: dict[str, dict[str, str]] = {item["identifier"]: item for item in fields}
    return list(unique.values())


def render_invoice_lines(blocks: list[dict[str, Any]], values: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for block in blocks:
        kind = block.get("kind")
        if kind == "static":
            lines.append(block.get("text", ""))
            continue

        identifier = block.get("identifier", "")
        if block.get("immutable", False):
            lines.append(block.get("text", ""))
        else:
            lines.append(values.get(identifier, ""))
    return lines


def build_invoice_name(now: datetime | None = None, output_dir: Path | None = None) -> str:
    moment = now or datetime.now()
    date_part = moment.strftime("%Y%m%d")

    directory = output_dir or (ensure_storage() / "output")
    existing = {path.stem for path in directory.glob(f"invoice_{date_part}_*.docx")}

    index = 1
    while True:
        candidate = f"invoice_{date_part}_{index:04d}"
        if candidate not in existing:
            return candidate
        index += 1


def export_invoice_documents(invoice_name: str, lines: list[str]) -> tuple[Path, Path]:
    from docx import Document
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    output_dir = ensure_storage() / "output"

    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    docx_path = output_dir / f"{invoice_name}.docx"
    doc.save(docx_path)

    pdf_path = output_dir / f"{invoice_name}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    y = 800
    for line in lines:
        c.drawString(40, y, line)
        y -= 20
        if y < 40:
            c.showPage()
            y = 800
    c.save()

    return docx_path, pdf_path
