ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_SOURCES_PER_PROJECT = 10

EXTENSION_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}

# F011 AC-005: the extension allowlist is the declared type; the leading
# bytes must agree. Sniffing is a content/extension boundary check, not an
# antivirus claim.
SNIFF_HEAD_BYTES = 8
_READ_CHUNK = 256 * 1024


class SourcePolicyError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def extension_of(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def validate_upload(filename: str, size_bytes: int, rights_acknowledged: bool) -> str:
    if not rights_acknowledged:
        raise SourcePolicyError("SOURCE_POLICY", "source rights must be acknowledged before upload")
    # F011 D8.2: filenames are untrusted metadata; path separators, control
    # characters, and NUL bytes never reach storage keys or list rendering.
    if any(char in filename for char in ("/", "\\", "\x00")) or any(
        ord(char) < 0x20 for char in filename
    ):
        raise SourcePolicyError("SOURCE_POLICY", "filename contains disallowed characters")
    extension = extension_of(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise SourcePolicyError(
            "SOURCE_POLICY", f"file type {extension or '(none)'} is not allowed"
        )
    if size_bytes > MAX_FILE_BYTES:
        raise SourcePolicyError("SOURCE_POLICY", "file exceeds the 20MB size limit")
    if size_bytes == 0:
        raise SourcePolicyError("SOURCE_POLICY", "file is empty")
    return extension


def _looks_like_text(head: bytes) -> bool:
    """Truncation-safe UTF-8 probe: the head may cut a multi-byte character."""
    for trim in range(4):
        try:
            head[: len(head) - trim or None].decode("utf-8")
            return True
        except UnicodeDecodeError:
            continue
    return False


def sniff_kind(head: bytes) -> str:
    if head.startswith(b"%PDF-"):
        return ".pdf"
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        return "zip"
    if _looks_like_text(head):
        return "text"
    return "unknown"


def validate_content_matches(extension: str, head: bytes) -> None:
    kind = sniff_kind(head)
    expected = {".pdf": ".pdf", ".docx": "zip", ".txt": "text", ".md": "text"}.get(extension)
    if expected is None or kind != expected:
        raise SourcePolicyError(
            "SOURCE_POLICY",
            f"file content does not match its {extension or '(none)'} extension",
        )


def read_upload_bounded(fileobj) -> tuple[bytes, str | None]:
    """Stream an upload in chunks, stopping at the size cap (F011 AC-005).

    Returns ``(data, None)`` when the payload fits, or ``(partial, message)``
    with a SourcePolicyError message when it exceeds the cap, so oversize is
    rejected without buffering the whole file.
    """
    buffer = bytearray()
    while len(buffer) <= MAX_FILE_BYTES:
        chunk = fileobj.read(_READ_CHUNK)
        if not chunk:
            return bytes(buffer), None
        buffer.extend(chunk)
    return bytes(buffer[: MAX_FILE_BYTES + 1]), "file exceeds the 20MB size limit"


def validate_upload_stream(filename: str, rights_acknowledged: bool, fileobj) -> bytes:
    """Full F011 upload boundary: rights, extension, bounded size, sniffing."""
    data, oversize = read_upload_bounded(fileobj)
    if oversize is not None:
        raise SourcePolicyError("SOURCE_POLICY", oversize)
    extension = validate_upload(filename, len(data), rights_acknowledged)
    validate_content_matches(extension, data[:SNIFF_HEAD_BYTES])
    return data
