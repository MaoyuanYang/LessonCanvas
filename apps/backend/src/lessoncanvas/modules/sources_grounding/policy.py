ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_SOURCES_PER_PROJECT = 10

EXTENSION_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


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
