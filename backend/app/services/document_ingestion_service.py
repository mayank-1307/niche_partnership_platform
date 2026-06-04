from __future__ import annotations

import io
import re
import zlib
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None


@dataclass(slots=True)
class UploadedDocumentContext:
    filename: str
    content_type: str
    text: str
    excerpt: str
    truncated: bool = False


_DOCX_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_MAX_TEXT_CHARS = 24000
_MAX_EXCERPT_CHARS = 12000


def _normalize_filename(filename: str) -> str:
    safe_name = Path(filename).name.strip()
    return safe_name or "uploaded-document"


def _normalize_text(text: str) -> str:
    lines = []
    text = "".join(char if char in "\n\t" or 32 <= ord(char) != 127 else " " for char in text)
    for raw_line in text.replace("\r", "\n").split("\n"):
        cleaned_line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if cleaned_line:
            lines.append(cleaned_line)
    return "\n".join(lines)


def _decode_text_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _extract_docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        return ""

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError:
        return ""

    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", _DOCX_NAMESPACE):
        fragments = [(node.text or "") for node in paragraph.findall(".//w:t", _DOCX_NAMESPACE)]
        paragraph_text = "".join(fragments).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)
    return "\n".join(paragraphs)


def _unescape_pdf_literal(value: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            result.append(char)
            index += 1
            continue

        if index + 1 >= len(value):
            break

        next_char = value[index + 1]
        if next_char in "\\()":
            result.append(next_char)
            index += 2
            continue
        if next_char == "n":
            result.append("\n")
            index += 2
            continue
        if next_char == "r":
            result.append("\r")
            index += 2
            continue
        if next_char == "t":
            result.append("\t")
            index += 2
            continue
        if next_char == "b":
            result.append("\b")
            index += 2
            continue
        if next_char == "f":
            result.append("\f")
            index += 2
            continue
        if next_char.isdigit():
            octal_digits = [next_char]
            cursor = index + 2
            while cursor < len(value) and len(octal_digits) < 3 and value[cursor].isdigit():
                octal_digits.append(value[cursor])
                cursor += 1
            try:
                result.append(chr(int("".join(octal_digits), 8)))
            except ValueError:
                pass
            index = cursor
            continue

        result.append(next_char)
        index += 2

    return "".join(result)


def _extract_pdf_strings(text: str) -> str:
    fragments: list[str] = []
    for match in re.finditer(r"\((?:\\.|[^\\)])*?\)", text, re.S):
        extracted = _unescape_pdf_literal(match.group(0)[1:-1]).strip()
        if extracted:
            fragments.append(extracted)

    for match in re.finditer(r"\[([^\]]+)\]\s*TJ", text, re.S):
        inner = match.group(1)
        for literal in re.finditer(r"\((?:\\.|[^\\)])*?\)", inner, re.S):
            extracted = _unescape_pdf_literal(literal.group(0)[1:-1]).strip()
            if extracted:
                fragments.append(extracted)

    return "\n".join(fragments)


def _extract_pdf_text(data: bytes) -> str:
    if PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(data))
            pages: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append(page_text)
            if pages:
                return "\n".join(pages)
        except Exception:
            pass

    decoded_chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw_stream = match.group(1).strip(b"\r\n")
        stream_candidates = [raw_stream]
        try:
            decompressed = zlib.decompress(raw_stream)
            if decompressed not in stream_candidates:
                stream_candidates.append(decompressed)
        except Exception:
            pass

        for candidate in stream_candidates:
            decoded = candidate.decode("latin-1", errors="ignore")
            extracted = _extract_pdf_strings(decoded)
            if extracted.strip():
                decoded_chunks.append(extracted)

    if decoded_chunks:
        return "\n".join(decoded_chunks)

    return _extract_pdf_strings(data.decode("latin-1", errors="ignore"))


def _extract_text(filename: str, content_type: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    content_type = content_type.lower().strip()

    if suffix == ".pdf" or content_type == "application/pdf":
        return _extract_pdf_text(data)
    if suffix == ".docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx_text(data)
    if suffix in {".txt", ".md", ".csv", ".log", ".rtf"} or content_type.startswith("text/"):
        return _decode_text_bytes(data)

    raise ValueError("Unsupported document type. Please upload a PDF, DOCX, or text file.")


def extract_uploaded_document(filename: str, content_type: str, data: bytes) -> UploadedDocumentContext:
    safe_name = _normalize_filename(filename)
    if not data:
        raise ValueError("Uploaded document is empty.")

    extracted_text = _extract_text(safe_name, content_type, data)
    normalized_text = _normalize_text(extracted_text)
    if not normalized_text:
        raise ValueError("Could not extract readable text from the uploaded document.")

    truncated = len(normalized_text) > _MAX_TEXT_CHARS
    normalized_text = normalized_text[:_MAX_TEXT_CHARS]
    excerpt = normalized_text[:_MAX_EXCERPT_CHARS]

    return UploadedDocumentContext(
        filename=safe_name,
        content_type=content_type or "application/octet-stream",
        text=normalized_text,
        excerpt=excerpt,
        truncated=truncated,
    )
