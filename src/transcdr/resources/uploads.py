from __future__ import annotations

import asyncio
import io
import mimetypes
import os
from typing import IO, AsyncIterator, Callable, Dict, Iterator, Optional, Tuple, Union, cast

import httpx

from .._base_client import new_idempotency_key, strip_none
from .._base_client import path_segment as seg
from .._errors import APIError
from ..types import Asset, Upload
from ._base import AsyncResource, SyncResource

__all__ = ["Uploads", "AsyncUploads", "FileInput", "ProgressCallback"]

#: A path, raw bytes, or a binary file object (seekable, so its size is known).
FileInput = Union[str, "os.PathLike[str]", bytes, bytearray, memoryview, IO[bytes]]
#: ``on_progress(bytes_sent, total_bytes)``
ProgressCallback = Callable[[int, int], None]

CHUNK_SIZE = 1024 * 1024


class _Source:
    """Where upload bytes come from; reopenable so a failed PUT can be retried."""

    def __init__(
        self, file: FileInput, filename: Optional[str], content_type: Optional[str]
    ) -> None:
        self._path: Optional[str] = None
        self._fileobj: Optional[IO[bytes]] = None
        self._start = 0
        if isinstance(file, (bytes, bytearray, memoryview)):
            self._fileobj = io.BytesIO(bytes(file))
            self.size = len(self._fileobj.getbuffer())
            default_name = "upload"
        elif isinstance(file, (str, os.PathLike)):
            self._path = os.fspath(file)
            self.size = os.path.getsize(self._path)
            default_name = os.path.basename(self._path)
        else:
            fileobj = cast(IO[bytes], file)
            if not (hasattr(fileobj, "read") and hasattr(fileobj, "seek") and fileobj.seekable()):
                raise TypeError(
                    "upload_file needs a path, bytes, or a seekable binary file object"
                )
            self._fileobj = fileobj
            self._start = fileobj.tell()
            fileobj.seek(0, os.SEEK_END)
            self.size = fileobj.tell() - self._start
            fileobj.seek(self._start)
            default_name = os.path.basename(str(getattr(fileobj, "name", "") or "")) or "upload"
        self.filename = filename or default_name
        self.content_type = (
            content_type or mimetypes.guess_type(self.filename)[0] or "application/octet-stream"
        )

    def open(self) -> IO[bytes]:
        if self._path is not None:
            return open(self._path, "rb")
        assert self._fileobj is not None
        self._fileobj.seek(self._start)
        return self._fileobj

    def release(self, handle: IO[bytes]) -> None:
        if self._path is not None:
            handle.close()


def _put_request_parts(upload: Upload, source: _Source) -> Tuple[str, str, Dict[str, str]]:
    method = (upload.get("upload_method") or "PUT").upper()
    headers = {"Content-Type": source.content_type}
    headers.update(upload.get("upload_headers") or {})
    # An explicit length keeps httpx from switching to chunked encoding,
    # which presigned S3 PUTs reject.
    headers["Content-Length"] = str(source.size)
    return upload["upload_url"], method, headers


def _storage_error(response: httpx.Response) -> APIError:
    text = response.text[:500] if response.content else ""
    return APIError(
        f"Uploading to storage failed with HTTP {response.status_code}" + (f": {text}" if text else ""),
        status=response.status_code,
        headers=response.headers,
        body=text,
    )


def _iter_chunks(
    handle: IO[bytes], total: int, on_progress: Optional[ProgressCallback]
) -> Iterator[bytes]:
    sent = 0
    while sent < total:
        chunk = handle.read(min(CHUNK_SIZE, total - sent))
        if not chunk:
            break
        sent += len(chunk)
        yield chunk
        if on_progress is not None:
            on_progress(sent, total)


async def _aiter_chunks(
    handle: IO[bytes], total: int, on_progress: Optional[ProgressCallback]
) -> AsyncIterator[bytes]:
    sent = 0
    while sent < total:
        chunk = await asyncio.to_thread(handle.read, min(CHUNK_SIZE, total - sent))
        if not chunk:
            break
        sent += len(chunk)
        yield chunk
        if on_progress is not None:
            on_progress(sent, total)


class Uploads(SyncResource):
    def create(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
        metadata: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Upload:
        """Open a direct-to-storage upload session. An ``Idempotency-Key`` is
        generated when not given, so the call is retried safely."""
        body = strip_none(
            {
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "metadata": metadata,
            }
        )
        return cast(
            Upload,
            self._client.request(
                "POST",
                "/v1/uploads",
                json=body,
                idempotency_key=idempotency_key or new_idempotency_key(),
            ),
        )

    def complete(self, id: str) -> Asset:
        """Finish an upload session; returns the ready asset."""
        return cast(Asset, self._client.request("POST", f"/v1/uploads/{seg(id)}/complete"))

    def upload_file(
        self,
        file: FileInput,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        *,
        metadata: Optional[Dict[str, str]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Asset:
        """Upload a local file in one call and return the ready :class:`Asset`.

        Creates an upload session, streams the bytes to its ``upload_url`` with
        the returned headers, then completes the session. ``file`` is a path,
        bytes, or a seekable binary file object.
        """
        source = _Source(file, filename, content_type)
        upload = self.create(
            filename=source.filename,
            content_type=source.content_type,
            size_bytes=source.size,
            metadata=metadata,
        )
        self._put(upload, source, on_progress)
        return self.complete(upload["id"])

    def _put(self, upload: Upload, source: _Source, on_progress: Optional[ProgressCallback]) -> None:
        client = self._client
        url, method, headers = _put_request_parts(upload, source)
        url = client._url(url)
        attempt = 0
        while True:
            handle = source.open()
            try:
                response = client._client.request(
                    method,
                    url,
                    content=_iter_chunks(handle, source.size, on_progress),
                    headers=headers,
                    timeout=client.timeout,
                )
            except httpx.TransportError as exc:
                if attempt < client.max_retries:
                    client._sleep(client._retry_delay(attempt))
                    attempt += 1
                    continue
                raise client._connection_error(exc) from exc
            finally:
                source.release(handle)
            if 200 <= response.status_code < 300:
                return
            if attempt < client.max_retries and client._retryable_status(response.status_code):
                client._sleep(client._retry_delay(attempt, response))
                attempt += 1
                continue
            raise _storage_error(response)


class AsyncUploads(AsyncResource):
    async def create(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
        metadata: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Upload:
        body = strip_none(
            {
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "metadata": metadata,
            }
        )
        return cast(
            Upload,
            await self._client.request(
                "POST",
                "/v1/uploads",
                json=body,
                idempotency_key=idempotency_key or new_idempotency_key(),
            ),
        )

    async def complete(self, id: str) -> Asset:
        return cast(Asset, await self._client.request("POST", f"/v1/uploads/{seg(id)}/complete"))

    async def upload_file(
        self,
        file: FileInput,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        *,
        metadata: Optional[Dict[str, str]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Asset:
        """Async twin of :meth:`Uploads.upload_file`; file reads run in a thread."""
        source = _Source(file, filename, content_type)
        upload = await self.create(
            filename=source.filename,
            content_type=source.content_type,
            size_bytes=source.size,
            metadata=metadata,
        )
        await self._put(upload, source, on_progress)
        return await self.complete(upload["id"])

    async def _put(
        self, upload: Upload, source: _Source, on_progress: Optional[ProgressCallback]
    ) -> None:
        client = self._client
        url, method, headers = _put_request_parts(upload, source)
        url = client._url(url)
        attempt = 0
        while True:
            handle = source.open()
            try:
                response = await client._client.request(
                    method,
                    url,
                    content=_aiter_chunks(handle, source.size, on_progress),
                    headers=headers,
                    timeout=client.timeout,
                )
            except httpx.TransportError as exc:
                if attempt < client.max_retries:
                    await client._sleep(client._retry_delay(attempt))
                    attempt += 1
                    continue
                raise client._connection_error(exc) from exc
            finally:
                source.release(handle)
            if 200 <= response.status_code < 300:
                return
            if attempt < client.max_retries and client._retryable_status(response.status_code):
                await client._sleep(client._retry_delay(attempt, response))
                attempt += 1
                continue
            raise _storage_error(response)

