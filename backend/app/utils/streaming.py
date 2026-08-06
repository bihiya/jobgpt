"""Streaming response helpers for large CSV/file downloads."""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator, Iterable
from pathlib import Path

from fastapi.responses import StreamingResponse
from starlette.responses import FileResponse


async def iter_csv_rows(headers: list[str], rows: Iterable[Iterable]) -> AsyncIterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    for row in rows:
        writer.writerow(row)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def csv_streaming_response(headers: list[str], rows: Iterable[Iterable], filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter_csv_rows(headers, rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def file_stream(path: str | Path, media_type: str = "application/octet-stream") -> FileResponse:
    """Efficient file streaming with sendfile when available."""
    return FileResponse(path, media_type=media_type, filename=Path(path).name)
