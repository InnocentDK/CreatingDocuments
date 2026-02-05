from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from flask import Flask, redirect, render_template, request, send_file, url_for, flash

from services import (
    build_invoice_name,
    collect_input_fields,
    ensure_storage,
    export_invoice_documents,
    load_template,
    render_invoice_lines,
    save_template,
    list_templates,
)

app = Flask(__name__)
app.secret_key = "invoice-template-editor"


@dataclass
class Block:
    kind: str
    identifier: str
    text: str
    immutable: bool = False


@app.get("/")
def index():
    return render_template("index.html", templates=list_templates())


@app.post("/templates")
def create_template():
    title = request.form.get("title", "").strip()
    raw_blocks = request.form.get("blocks", "[]")

    if not title:
        flash("Название шаблона обязательно", "error")
        return redirect(url_for("index"))

    try:
        payload: list[dict[str, Any]] = json.loads(raw_blocks)
    except json.JSONDecodeError:
        flash("Не удалось прочитать блоки шаблона", "error")
        return redirect(url_for("index"))

    blocks: list[dict[str, Any]] = []
    for item in payload:
        block = Block(
            kind=item.get("kind", "static"),
            identifier=item.get("identifier", "").strip(),
            text=item.get("text", ""),
            immutable=bool(item.get("immutable", False)),
        )
        if block.kind == "field" and not block.identifier:
            continue
        blocks.append(asdict(block))

    if not blocks:
        flash("Добавьте хотя бы один блок", "error")
        return redirect(url_for("index"))

    save_template(title=title, blocks=blocks)
    flash("Шаблон сохранен", "success")
    return redirect(url_for("index"))


@app.get("/templates/<template_id>")
def fill_template(template_id: str):
    template_data = load_template(template_id)
    if not template_data:
        flash("Шаблон не найден", "error")
        return redirect(url_for("index"))

    fields = collect_input_fields(template_data["blocks"])
    return render_template("fill_template.html", template_data=template_data, fields=fields)


@app.post("/templates/<template_id>/generate")
def generate(template_id: str):
    template_data = load_template(template_id)
    if not template_data:
        flash("Шаблон не найден", "error")
        return redirect(url_for("index"))

    values = {key: value for key, value in request.form.items()}
    lines = render_invoice_lines(template_data["blocks"], values)
    invoice_name = build_invoice_name()
    docx_path, pdf_path = export_invoice_documents(invoice_name, lines)

    return render_template(
        "generated.html",
        template_data=template_data,
        invoice_name=invoice_name,
        docx_name=docx_path.name,
        pdf_name=pdf_path.name,
    )


@app.get("/downloads/<filename>")
def download(filename: str):
    output_dir = ensure_storage() / "output"
    file_path = output_dir / filename
    if not file_path.exists():
        flash("Файл не найден", "error")
        return redirect(url_for("index"))

    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
