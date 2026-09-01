import io

CHUNK_SIZE = 1000

# F011 bounded extraction: a container that claims to expand beyond these
# limits is rejected before any decompression work (decompression-bomb guard).
MAX_DOCX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_DOCX_ENTRIES = 10_000
MAX_PDF_PAGES = 500


class ParseError(Exception):
    pass


def _guard_docx_container(data: bytes, filename: str) -> None:
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
    except Exception as error:
        raise ParseError(f"could not parse {filename}") from error
    if len(infos) > MAX_DOCX_ENTRIES:
        raise ParseError(f"docx container has too many entries: {filename}")
    total_uncompressed = sum(info.file_size for info in infos)
    if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
        raise ParseError(f"docx expands beyond the bounded extraction limit: {filename}")


def extract_text(filename: str, data: bytes) -> str:
    lowered = filename.lower()
    try:
        if lowered.endswith((".txt", ".md")):
            # Strict decode: binary payloads renamed to .txt fail here instead
            # of becoming replacement-character chunk noise (F011 AC-005).
            return data.decode("utf-8")
        if lowered.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > MAX_PDF_PAGES:
                raise ParseError(f"pdf exceeds the bounded page limit: {filename}")
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if lowered.endswith(".docx"):
            import docx

            _guard_docx_container(data, filename)
            document = docx.Document(io.BytesIO(data))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except ParseError:
        raise
    except Exception as error:
        raise ParseError(f"could not parse {filename}") from error
    raise ParseError(f"unsupported file type: {filename}")


def chunk_text(text: str) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    return [cleaned[i : i + CHUNK_SIZE] for i in range(0, len(cleaned), CHUNK_SIZE)]
