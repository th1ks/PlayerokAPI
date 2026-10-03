"""Загрузка файлов в хранилище площадки."""

from __future__ import annotations

import mimetypes
import os
from typing import Any

from ..common.endpoints import Service
from ..common.utils import encode_multipart
from ..exceptions import PlayerokError
from ..transport.rest import RestTransport

__all__ = ["FilesMethods"]


class FilesMethods:
    """Трёхшаговая загрузка, как её делает сайт.

    `GET /file/v1/upload-url` выдаёт presigned-форму, тело уходит прямо
    в хранилище, затем `POST /file/v1/confirm-upload` подтверждает загрузку.
    Наружу отдаётся идентификатор файла — его принимают `imagesIds`
    сообщения, `attachmentIds` товара и `avatarId` профиля.
    """

    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def upload(
        self,
        content: bytes,
        filename: str = "file",
        *,
        content_type: str | None = None,
        file_type: str | None = None,
    ) -> str:
        """Загрузить файл и вернуть его идентификатор."""
        if not content:
            raise ValueError("Пустой файл")

        mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        url, file_id, fields = await self._request_slot(file_type)
        await self._put_to_storage(url, fields, filename, content, mime)
        await self.confirm(file_id)
        return file_id

    async def upload_path(self, path: str, *, file_type: str | None = None) -> str:
        """То же, но файл берётся с диска."""
        with open(path, "rb") as handle:
            content = handle.read()
        return await self.upload(content, os.path.basename(path), file_type=file_type)

    async def confirm(self, file_id: str) -> Any:
        """Подтвердить загрузку. Без этого файл остаётся во временном хранилище."""
        return await self._rest.post(
            Service.BFF,
            "/file/v1/confirm-upload",
            json={"id": file_id},
            auth=True,
        )

    async def _request_slot(self, file_type: str | None) -> tuple[str, str, dict[str, Any]]:
        payload = await self._rest.get(
            Service.BFF,
            "/file/v1/upload-url",
            params={"file_type": file_type} if file_type else None,
            auth=True,
        )
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ /file/v1/upload-url")

        url = str(payload.get("url") or "")
        if not url:
            raise PlayerokError("Сервер не выдал адрес загрузки")
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        file_id = payload.get("file_id") or payload.get("fileId")
        if not file_id:
            raise PlayerokError("Сервер не выдал идентификатор файла")

        fields = payload.get("fields")
        return url, str(file_id), dict(fields) if isinstance(fields, dict) else {}

    async def _put_to_storage(
        self,
        url: str,
        fields: dict[str, Any],
        filename: str,
        content: bytes,
        mime: str,
    ) -> None:
        # Поля presigned-формы обязаны идти перед самим файлом.
        body, content_type = encode_multipart(fields, {"file": (filename, content, mime)})
        await self._rest.http.request(
            "POST",
            url,
            content=body,
            headers={"Content-Type": content_type},
            parse_json=False,
        )
