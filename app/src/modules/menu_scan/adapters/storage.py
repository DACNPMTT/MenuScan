"""Private object-storage adapters for menu source files."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from src.core.config import StorageConfig


@dataclass(frozen=True, slots=True)
class StoredObject:
    data: bytes
    content_type: str | None = None


class ObjectNotFoundError(Exception):
    """Raised when the object key does not exist."""


class ObjectStorageError(Exception):
    """Raised when the object storage provider cannot complete the operation."""


class ObjectStorage(Protocol):
    def save_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Persist bytes under a server-generated key."""

    def read_object(self, key: str) -> StoredObject:
        """Read bytes for a key."""

    def delete_object(self, key: str) -> None:
        """Delete a key if it exists."""

    def create_presigned_get_url(self, key: str) -> str | None:
        """Return a short-lived GET URL when the adapter supports it."""


class LocalObjectStorage:
    """Filesystem-backed private storage for local development and tests."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()

    def save_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        path = self._path_for_key(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self._metadata_path(path).write_text(
                json.dumps({"content_type": content_type}),
                encoding="utf-8",
            )
        except OSError as error:
            raise ObjectStorageError("local object storage write failed") from error

    def read_object(self, key: str) -> StoredObject:
        path = self._path_for_key(key)
        try:
            data = path.read_bytes()
        except FileNotFoundError as error:
            raise ObjectNotFoundError(key) from error
        except OSError as error:
            raise ObjectStorageError("local object storage read failed") from error

        content_type = None
        try:
            metadata = json.loads(
                self._metadata_path(path).read_text(encoding="utf-8")
            )
            if isinstance(metadata.get("content_type"), str):
                content_type = metadata["content_type"]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            content_type = None

        return StoredObject(data=data, content_type=content_type)

    def delete_object(self, key: str) -> None:
        path = self._path_for_key(key)
        for target in (path, self._metadata_path(path)):
            try:
                target.unlink()
            except FileNotFoundError:
                continue
            except OSError as error:
                raise ObjectStorageError("local object storage delete failed") from error

    def create_presigned_get_url(self, key: str) -> str | None:
        return None

    def _path_for_key(self, key: str) -> Path:
        object_path = PurePosixPath(key)
        if object_path.is_absolute() or ".." in object_path.parts:
            raise ObjectStorageError("invalid object key")
        if not object_path.parts:
            raise ObjectStorageError("invalid object key")

        path = self._root.joinpath(*object_path.parts).resolve()
        if path != self._root and self._root not in path.parents:
            raise ObjectStorageError("invalid object key")
        return path

    @staticmethod
    def _metadata_path(path: Path) -> Path:
        return path.with_name(f"{path.name}.metadata.json")


class S3ObjectStorage:
    """Small S3-compatible adapter using AWS Signature V4.

    It intentionally uses path-style URLs because most S3-compatible providers
    support them and they avoid bucket-name TLS edge cases in custom endpoints.
    """

    _service = "s3"

    def __init__(self, config: StorageConfig) -> None:
        if not config.is_configured():
            raise ObjectStorageError("s3 object storage is not configured")
        assert config.bucket_name is not None  # noqa: S101
        assert config.endpoint_url is not None  # noqa: S101
        assert config.access_key_id is not None  # noqa: S101
        assert config.secret_access_key is not None  # noqa: S101

        self._bucket_name = config.bucket_name
        self._endpoint_url = config.endpoint_url.rstrip("/")
        self._region = config.region
        self._access_key_id = config.access_key_id
        self._secret_access_key = config.secret_access_key
        self._session_token = config.session_token
        self._signed_url_seconds = config.signed_url_seconds

    def save_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        self._request(
            method="PUT",
            key=key,
            body=data,
            extra_headers={"content-type": content_type},
        )

    def read_object(self, key: str) -> StoredObject:
        response = self._request(method="GET", key=key, body=b"")
        return StoredObject(
            data=response.data,
            content_type=response.headers.get("content-type"),
        )

    def delete_object(self, key: str) -> None:
        self._request(method="DELETE", key=key, body=b"")

    def create_presigned_get_url(self, key: str) -> str | None:
        now = _utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        credential_scope = self._credential_scope(date_stamp)
        parsed = urlparse(self._object_url(key))
        host = parsed.netloc
        query = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self._access_key_id}/{credential_scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(self._signed_url_seconds),
            "X-Amz-SignedHeaders": "host",
        }
        if self._session_token:
            query["X-Amz-Security-Token"] = self._session_token

        canonical_query = _canonical_query(query)
        canonical_request = "\n".join(
            (
                "GET",
                parsed.path or "/",
                canonical_query,
                f"host:{host}\n",
                "host",
                "UNSIGNED-PAYLOAD",
            )
        )
        string_to_sign = self._string_to_sign(
            amz_date=amz_date,
            credential_scope=credential_scope,
            canonical_request=canonical_request,
        )
        signature = hmac.new(
            self._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return (
            f"{parsed.scheme}://{host}{parsed.path}?"
            f"{canonical_query}&X-Amz-Signature={signature}"
        )

    def _request(
        self,
        *,
        method: str,
        key: str,
        body: bytes = b"",
        extra_headers: dict[str, str] | None = None,
    ) -> "_HttpResponse":
        headers = self._signed_headers(
            method=method,
            key=key,
            body=body,
            extra_headers=extra_headers or {},
        )
        request = Request(
            self._object_url(key),
            data=body if method in {"PUT", "POST"} else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310  # nosec B310
                return _HttpResponse(
                    data=response.read(),
                    headers={
                        key.lower(): value
                        for key, value in response.headers.items()
                    },
                )
        except HTTPError as error:
            if error.code == 404:
                raise ObjectNotFoundError(key) from error
            raise ObjectStorageError("s3 object storage request failed") from error
        except URLError as error:
            raise ObjectStorageError("s3 object storage request failed") from error

    def _signed_headers(
        self,
        *,
        method: str,
        key: str,
        body: bytes,
        extra_headers: dict[str, str],
    ) -> dict[str, str]:
        now = _utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()
        parsed = urlparse(self._object_url(key))
        headers = {
            "host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            **{name.lower(): value for name, value in extra_headers.items()},
        }
        if self._session_token:
            headers["x-amz-security-token"] = self._session_token

        signed_header_names = sorted(headers)
        canonical_headers = "".join(
            f"{name}:{headers[name].strip()}\n" for name in signed_header_names
        )
        credential_scope = self._credential_scope(date_stamp)
        canonical_request = "\n".join(
            (
                method,
                parsed.path or "/",
                "",
                canonical_headers,
                ";".join(signed_header_names),
                payload_hash,
            )
        )
        string_to_sign = self._string_to_sign(
            amz_date=amz_date,
            credential_scope=credential_scope,
            canonical_request=canonical_request,
        )
        signature = hmac.new(
            self._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        authorization = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self._access_key_id}/{credential_scope}, "
            f"SignedHeaders={';'.join(signed_header_names)}, "
            f"Signature={signature}"
        )
        return {**headers, "authorization": authorization}

    def _object_url(self, key: str) -> str:
        encoded_key = "/".join(quote(part, safe="") for part in _key_parts(key))
        return (
            f"{self._endpoint_url}/"
            f"{quote(self._bucket_name, safe='')}/{encoded_key}"
        )

    def _credential_scope(self, date_stamp: str) -> str:
        return f"{date_stamp}/{self._region}/{self._service}/aws4_request"

    def _string_to_sign(
        self,
        *,
        amz_date: str,
        credential_scope: str,
        canonical_request: str,
    ) -> str:
        return "\n".join(
            (
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            )
        )

    def _signing_key(self, date_stamp: str) -> bytes:
        date_key = _hmac_sha256(f"AWS4{self._secret_access_key}".encode(), date_stamp)
        region_key = _hmac_sha256(date_key, self._region)
        service_key = _hmac_sha256(region_key, self._service)
        return _hmac_sha256(service_key, "aws4_request")


@dataclass(frozen=True, slots=True)
class _HttpResponse:
    data: bytes
    headers: dict[str, str]


def build_object_storage(config: StorageConfig) -> ObjectStorage:
    if config.provider == "local":
        return LocalObjectStorage(config.local_root)
    if config.provider == "s3":
        return S3ObjectStorage(config)
    raise ObjectStorageError(f"unsupported storage provider: {config.provider}")


def _key_parts(key: str) -> tuple[str, ...]:
    object_path = PurePosixPath(key)
    if object_path.is_absolute() or ".." in object_path.parts:
        raise ObjectStorageError("invalid object key")
    parts = tuple(part for part in object_path.parts if part not in ("", "."))
    if not parts:
        raise ObjectStorageError("invalid object key")
    return parts


def _canonical_query(query: dict[str, str]) -> str:
    return urlencode(
        sorted(query.items()),
        quote_via=quote,
        safe="-_.~",
    )


def _hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
