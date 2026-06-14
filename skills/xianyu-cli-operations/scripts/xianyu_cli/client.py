from __future__ import annotations

import json
import mimetypes
import uuid
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple
from urllib import error, parse, request


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class ApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: Optional[str] = None,
        timeout: int = 60,
        opener: Optional[Callable[..., Any]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.opener = opener or request.urlopen

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        query: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        url = self._url(path, query=query)
        body = None
        headers = self._headers()
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"

        req = request.Request(url, data=body, headers=headers, method=method.upper())
        return self._open(req)

    def multipart(
        self,
        path: str,
        *,
        fields: Mapping[str, Any],
        files: Iterable[Tuple[str, str, bytes]],
    ) -> Any:
        boundary = f"----xianyu-cli-{uuid.uuid4().hex}"
        body = self._multipart_body(boundary, fields=fields, files=files)
        headers = self._headers()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        req = request.Request(
            self._url(path),
            data=body,
            headers=headers,
            method="POST",
        )
        return self._open(req)

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path: str, *, query: Optional[Mapping[str, Any]] = None) -> str:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if query:
            clean = {key: value for key, value in query.items() if value is not None}
            if clean:
                url = f"{url}?{parse.urlencode(clean, doseq=True)}"
        return url

    def _open(self, req: request.Request) -> Any:
        try:
            with self.opener(req, timeout=self.timeout) as response:
                return self._decode_response(response)
        except error.HTTPError as exc:
            payload = self._decode_error(exc)
            message = payload.get("detail") if isinstance(payload, dict) else str(payload)
            raise ApiError(exc.code, message or f"HTTP {exc.code}", payload) from exc
        except error.URLError as exc:
            raise ApiError(0, str(exc.reason)) from exc

    def _decode_response(self, response: Any) -> Any:
        raw = response.read()
        if not raw:
            return None
        content_type = ""
        headers = getattr(response, "headers", {}) or {}
        if hasattr(headers, "get"):
            content_type = headers.get("Content-Type", "")
        text = raw.decode("utf-8", errors="replace")
        if "json" in content_type.lower() or text[:1] in ("{", "["):
            return json.loads(text)
        return text

    def _decode_error(self, exc: error.HTTPError) -> Any:
        raw = exc.read()
        if not raw:
            return {"detail": f"HTTP {exc.code}"}
        text = raw.decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"detail": text}

    def _multipart_body(
        self,
        boundary: str,
        *,
        fields: Mapping[str, Any],
        files: Iterable[Tuple[str, str, bytes]],
    ) -> bytes:
        lines = []
        boundary_bytes = boundary.encode("utf-8")
        for name, value in fields.items():
            if value is None:
                continue
            lines.extend(
                [
                    b"--" + boundary_bytes,
                    f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"),
                    b"",
                    str(value).encode("utf-8"),
                ]
            )
        for field_name, filename, content in files:
            mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            safe_name = filename.replace('"', '\\"')
            lines.extend(
                [
                    b"--" + boundary_bytes,
                    (
                        f'Content-Disposition: form-data; name="{field_name}"; '
                        f'filename="{safe_name}"'
                    ).encode("utf-8"),
                    f"Content-Type: {mime_type}".encode("utf-8"),
                    b"",
                    content,
                ]
            )
        lines.append(b"--" + boundary_bytes + b"--")
        lines.append(b"")
        return b"\r\n".join(lines)
