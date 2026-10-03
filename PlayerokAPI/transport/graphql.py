"""GraphQL-транспорт: запросы, мутации и загрузка файлов."""

from __future__ import annotations

import json as jsonlib
import logging
from dataclasses import dataclass, field
from typing import Any

from ..common.endpoints import GRAPHQL_URL
from ..exceptions import AuthRequiredError, GraphQLError
from .http import HttpTransport

__all__ = ["GraphQLTransport", "Upload"]

logger = logging.getLogger("PlayerokAPI.graphql")


@dataclass(slots=True)
class Upload:
    """Файл для GraphQL-скаляра `Upload`."""

    content: bytes
    filename: str = "file"
    content_type: str = "application/octet-stream"

    @classmethod
    def from_path(cls, path: str, content_type: str | None = None) -> Upload:
        import mimetypes
        import os

        with open(path, "rb") as handle:
            content = handle.read()
        name = os.path.basename(path)
        mime = content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
        return cls(content=content, filename=name, content_type=mime)


@dataclass(slots=True)
class _Operation:
    query: str
    variables: dict[str, Any] = field(default_factory=dict)
    operation_name: str | None = None


class GraphQLTransport:
    """POST на `/graphql` с разбором `errors` в исключения.

    Мутации с файлами уходят по спецификации graphql-multipart-request —
    так же, как это делает фронт площадки.
    """

    def __init__(self, http: HttpTransport, url: str = GRAPHQL_URL) -> None:
        self._http = http
        self._url = url

    @property
    def http(self) -> HttpTransport:
        return self._http

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        operation_name: str | None = None,
        uploads: dict[str, Upload] | None = None,
        auth: bool = False,
    ) -> dict[str, Any]:
        """Выполнить операцию и вернуть содержимое `data`."""
        if auth and not self._http.token:
            raise AuthRequiredError(operation_name or "graphql")

        operation = _Operation(query, dict(variables or {}), operation_name)
        headers = {
            "apollo-require-preflight": "true",
            "x-gql-op": operation_name or "anonymous",
        }
        if operation_name:
            headers["x-apollo-operation-name"] = operation_name

        if uploads:
            payload = await self._send_multipart(operation, uploads, headers)
        else:
            payload = await self._http.request(
                "POST",
                self._url,
                json={
                    "operationName": operation.operation_name,
                    "query": operation.query,
                    "variables": operation.variables,
                },
                headers=headers,
            )

        if not isinstance(payload, dict):
            raise GraphQLError(
                [{"message": f"Неожиданный ответ GraphQL: {payload!r}"}],
                operation_name,
            )
        errors = payload.get("errors")
        if errors:
            raise GraphQLError(errors, operation_name)
        data = payload.get("data")
        if data is None:
            raise GraphQLError([{"message": "Пустой data в ответе"}], operation_name)
        return data

    async def _send_multipart(
        self,
        operation: _Operation,
        uploads: dict[str, Upload],
        headers: dict[str, str],
    ) -> Any:
        variables = _with_null_placeholders(operation.variables, uploads.keys())
        operations = {
            "operationName": operation.operation_name,
            "query": operation.query,
            "variables": variables,
        }
        file_map: dict[str, list[str]] = {}
        files: dict[str, tuple[str, bytes, str]] = {}
        for index, (path, upload) in enumerate(uploads.items()):
            key = str(index)
            file_map[key] = [f"variables.{path}"]
            files[key] = (upload.filename, upload.content, upload.content_type)

        return await self._http.request(
            "POST",
            self._url,
            data={
                "operations": jsonlib.dumps(operations, ensure_ascii=False),
                "map": jsonlib.dumps(file_map),
            },
            files=files,
            headers=headers,
        )


def _with_null_placeholders(variables: dict[str, Any], paths: Any) -> dict[str, Any]:
    """Проставить null на местах файлов — туда их подставит сервер."""
    import copy

    result = copy.deepcopy(variables)
    for path in paths:
        parts = path.split(".")
        cursor: Any = result
        for part in parts[:-1]:
            key: Any = int(part) if part.isdigit() else part
            cursor = cursor[key]
        last: Any = int(parts[-1]) if parts[-1].isdigit() else parts[-1]
        cursor[last] = None
    return result
