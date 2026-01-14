from io import BytesIO
from xml.sax.saxutils import escape
import zipfile


def build_docx_bytes(text):
    lines = text.splitlines() or [""]

    paragraphs = []
    for line in lines:
        if line.strip() == "":
            paragraphs.append("<w:p/>")
            continue
        safe_text = escape(line)
        paragraphs.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">"
            f"{safe_text}"
            "</w:t></w:r></w:p>"
        )

    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/"
        "wordprocessingml/2006/main\">"
        "<w:body>"
        f"{''.join(paragraphs)}"
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
