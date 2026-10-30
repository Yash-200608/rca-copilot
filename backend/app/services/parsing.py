"""Document intake: PDF (text-based), .eml, .docx, .txt / pasted text (incl. pasted emails).

Every parser returns a ParsedDoc whose `text` carries `[Page n]` markers so the AI can cite
locations. Scanned (image-only) PDFs are detected and flagged `scanned=True`: the AI run is
blocked for such documents instead of silently producing an incomplete investigation."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser

MIN_CHARS_PER_PAGE = 30


@dataclass
class ParsedDoc:
    kind: str  # pdf | email | docx | text
    text: str
    pages: int = 1
    scanned: bool = False
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class UnsupportedDocument(ValueError):
    pass


def sniff(filename: str, data: bytes) -> str:
    """Decide the kind by magic bytes first (never trust the client's content type)."""
    name = (filename or "").lower()
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:2] == b"PK":
        if name.endswith(".docx"):
            return "docx"
        raise UnsupportedDocument("ZIP-based file that is not a .docx")
    if data[:4] == b"\xd0\xcf\x11\xe0":
        raise UnsupportedDocument("Outlook .msg / legacy Office files are not supported - save the email as .eml or paste its text")
    if name.endswith(".eml") or re.match(rb"\s*(received|from|return-path|mime-version|date|subject):", data[:400], re.I):
        return "email"
    if b"\x00" in data[:2000]:
        raise UnsupportedDocument("Binary file type is not supported")
    return "text"


def parse_pdf(data: bytes) -> ParsedDoc:
    import pdfplumber

    parts: list[str] = []
    empty_pages: list[int] = []
    total = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            tables = []
            try:
                for tbl in page.extract_tables() or []:
                    rows = [" | ".join((c or "").replace("\n", " ").strip() for c in row) for row in tbl if row]
                    if rows:
                        tables.append("[Table]\n" + "\n".join(rows))
            except Exception:  # table extraction is best-effort
                pass
            if len(text) < MIN_CHARS_PER_PAGE:
                empty_pages.append(i)
            total += len(text)
            parts.append(f"[Page {i}]\n{text}" + ("\n" + "\n".join(tables) if tables else ""))
    scanned = n > 0 and (total / n) < MIN_CHARS_PER_PAGE
    warnings: list[str] = []
    if scanned:
        warnings.append("No extractable text - this looks like a scanned/image-only PDF. OCR is required; paste the text instead.")
    elif empty_pages:
        warnings.append(f"Page(s) {', '.join(map(str, empty_pages))} contain little or no extractable text and may be scanned images.")
    return ParsedDoc("pdf", "\n\n".join(parts), pages=n, scanned=scanned, warnings=warnings)


def _html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))


def parse_eml(data: bytes) -> ParsedDoc:
    msg = BytesParser(policy=policy.default).parsebytes(data)
    headers = {k: str(msg.get(k, "")) for k in ("From", "To", "Cc", "Subject", "Date")}
    body_part = msg.get_body(preferencelist=("plain", "html"))
    body = ""
    if body_part is not None:
        body = body_part.get_content()
        if body_part.get_content_type() == "text/html":
            body = _html_to_text(body)
    lines = [f"{k}: {v}" for k, v in headers.items() if v]
    text = "\n".join(lines) + "\n\n" + body.strip()
    warnings, pages = [], 1
    scanned = False
    for att in msg.iter_attachments():
        fname = att.get_filename() or "attachment"
        payload = att.get_payload(decode=True) or b""
        try:
            kind = sniff(fname, payload)
            if kind == "pdf":
                sub = parse_pdf(payload)
            elif kind == "docx":
                sub = parse_docx(payload)
            else:
                sub = parse_text(payload.decode("utf-8", errors="replace"))
            text += f"\n\n[Attachment: {fname}]\n{sub.text}"
            warnings += [f"{fname}: {w}" for w in sub.warnings]
            scanned = scanned or sub.scanned
            pages += sub.pages
        except UnsupportedDocument as e:
            warnings.append(f"Attachment {fname} skipped: {e}")
    return ParsedDoc("email", text, pages=pages, scanned=False, warnings=warnings,
                     meta={"headers": headers, "attachment_scanned": scanned})


def parse_docx(data: bytes) -> ParsedDoc:
    import docx

    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for tbl in d.tables:
        for row in tbl.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return ParsedDoc("docx", "\n".join(parts))


_EMAIL_HEADER = re.compile(r"^\s*(from|subject|sent|to|date)\s*:", re.I | re.M)


def parse_text(text: str) -> ParsedDoc:
    """Pasted text / .txt. Detects a pasted email (>= 2 header lines at the top)."""
    head = "\n".join(text.strip().splitlines()[:12])
    is_email = len(_EMAIL_HEADER.findall(head)) >= 2
    meta: dict = {}
    if is_email:
        for k in ("From", "To", "Subject", "Sent", "Date"):
            m = re.search(rf"^\s*{k}\s*:\s*(.+)$", head, re.I | re.M)
            if m:
                meta[k] = m.group(1).strip()
        meta = {"headers": meta}
    return ParsedDoc("email" if is_email else "text", text.strip(), meta=meta)


def parse_upload(filename: str, data: bytes) -> ParsedDoc:
    kind = sniff(filename, data)
    if kind == "pdf":
        return parse_pdf(data)
    if kind == "docx":
        return parse_docx(data)
    if kind == "email":
        return parse_eml(data)
    return parse_text(data.decode("utf-8", errors="replace"))
