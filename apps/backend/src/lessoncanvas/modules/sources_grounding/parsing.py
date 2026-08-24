import io

CHUNK_SIZE = 1000


class ParseError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> str:
    lowered = filename.lower()
    try:
        if lowered.endswith((".txt", ".md")):
            return data.decode("utf-8", errors="replace")
        if lowered.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if lowered.endswith(".docx"):
            import docx

            document = docx.Document(io.BytesIO(data))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as error:
        raise ParseError(f"could not parse {filename}") from error
    raise ParseError(f"unsupported file type: {filename}")


def chunk_text(text: str) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    return [cleaned[i : i + CHUNK_SIZE] for i in range(0, len(cleaned), CHUNK_SIZE)]
