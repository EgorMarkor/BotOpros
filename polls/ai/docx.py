from io import BytesIO
from xml.sax.saxutils import escape
import zipfile


def _is_table_separator(line):
    stripped = line.strip()
    if not stripped or "-" not in stripped:
        return False
    for char in stripped:
        if char not in "|-: ":
            return False
    return True


def _split_table_row(line):
    parts = line.strip().strip("|").split("|")
    return [part.strip() for part in parts]


def _build_paragraph_xml(text):
    if text.strip() == "":
        return "<w:p/>"
    safe_text = escape(text)
    return (
        "<w:p><w:r><w:t xml:space=\"preserve\">"
        f"{safe_text}"
        "</w:t></w:r></w:p>"
    )


def _build_table_xml(rows):
    if not rows:
        return ""

    column_count = max(len(row) for row in rows)
    grid_cols = "".join("<w:gridCol w:w=\"2400\"/>" for _ in range(column_count))
    tbl_pr = (
        "<w:tblPr>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"4\" w:color=\"auto\"/>"
        "<w:left w:val=\"single\" w:sz=\"4\" w:color=\"auto\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"4\" w:color=\"auto\"/>"
        "<w:right w:val=\"single\" w:sz=\"4\" w:color=\"auto\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"4\" w:color=\"auto\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:color=\"auto\"/>"
        "</w:tblBorders>"
        "</w:tblPr>"
    )

    table_rows = []
    for row in rows:
        cells = row + [""] * (column_count - len(row))
        row_cells = []
        for cell in cells:
            safe_text = escape(cell)
            row_cells.append(
                "<w:tc><w:tcPr/><w:p><w:r><w:t xml:space=\"preserve\">"
                f"{safe_text}"
                "</w:t></w:r></w:p></w:tc>"
            )
        table_rows.append("<w:tr>" + "".join(row_cells) + "</w:tr>")

    return "<w:tbl>" + tbl_pr + f"<w:tblGrid>{grid_cols}</w:tblGrid>" + "".join(table_rows) + "</w:tbl>"


def _build_body_xml(text):
    lines = text.splitlines() or [""]

    blocks = []
    index = 0
    while index < len(lines):
        line = lines[index]
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if "|" in line and _is_table_separator(next_line):
            header = _split_table_row(line)
            rows = [header]
            index += 2
            while index < len(lines):
                row_line = lines[index]
                if "|" not in row_line:
                    break
                rows.append(_split_table_row(row_line))
                index += 1
            blocks.append(_build_table_xml(rows))
            continue

        blocks.append(_build_paragraph_xml(line))
        index += 1

    return "".join(blocks)


def build_docx_bytes(text):
    body_xml = _build_body_xml(text)

    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/"
        "wordprocessingml/2006/main\">"
        "<w:body>"
        f"{body_xml}"
        "</w:body>"
        "</w:document>"
    )

    content_types_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/"
        "content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/"
        "vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/word/document.xml\" ContentType=\"application/"
        "vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
        "</Types>"
    )

    rels_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/"
        "relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/"
        "officeDocument/2006/relationships/officeDocument\" "
        "Target=\"word/document.xml\"/>"
        "</Relationships>"
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types_xml)
        docx.writestr("_rels/.rels", rels_xml)
        docx.writestr("word/document.xml", document_xml)

    return buffer.getvalue()
