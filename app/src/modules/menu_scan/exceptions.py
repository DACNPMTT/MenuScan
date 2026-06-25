from src.core.errors import ApplicationError


class FileTooLargeError(ApplicationError):
    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(
            status_code=413,
            code="FILE_TOO_LARGE",
            message="File exceeds the 10 MB limit.",
            details={"max_size_bytes": max_size_bytes},
        )


class EmptyUploadError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="VALIDATION_ERROR",
            message="The uploaded file is empty.",
            details={"fields": {"file": ["File must not be empty."]}},
        )


class UnsupportedFileTypeError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=415,
            code="UNSUPPORTED_FILE_TYPE",
            message="Only JPG, PNG, WEBP and PDF files are supported.",
        )


class InvalidPdfError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="INVALID_PDF",
            message="The PDF is invalid or exceeds the 5 page limit.",
        )


class InvalidTargetLanguageError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="VALIDATION_ERROR",
            message="The request data is invalid.",
            details={"fields": {"target_language": ["Choose 'vi' or 'en'."]}},
        )


class ScanNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="SCAN_NOT_FOUND",
            message="Scan was not found.",
        )


class SourceFileNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="SOURCE_FILE_NOT_FOUND",
            message="The scan source file was not found.",
        )


class StorageUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="STORAGE_UNAVAILABLE",
            message="Source file storage is temporarily unavailable.",
        )
