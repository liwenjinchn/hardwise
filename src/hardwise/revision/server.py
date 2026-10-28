"""Stateless, localhost-oriented revision comparison API and static page."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from hardwise.revision.models import ComparisonResult

STATIC_DIR = Path(__file__).parent.parent / "workbench" / "static"
MAX_FILE_BYTES = 10 * 1024 * 1024
ROLES = ("before_netlist", "before_bom", "after_netlist", "after_bom")
router = APIRouter()


class _UploadTooLarge(MultiPartException):
    pass


def _basename(filename: str, role: str) -> str:
    # Strip both POSIX and Windows client directories; no client path is ever used.
    name = PureWindowsPath(filename.replace("\\", "/")).name
    if (
        name in {"", ".", ".."}
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or len(name.encode("utf-8")) > 240
    ):
        raise MultiPartException(f"{role}: 文件名无效。")
    suffixes = {".net", ".txt"} if role.endswith("netlist") else {".csv", ".tsv"}
    if Path(name).suffix.lower() not in suffixes:
        raise MultiPartException(f"{role}: 格式不支持；仅接受 {' / '.join(sorted(suffixes))}。")
    return name


class _CompareMultipartParser(MultiPartParser):
    """Bound file bytes while streaming, not merely the in-memory spool size."""

    def __init__(self, request: Request) -> None:
        super().__init__(request.headers, self._bounded_stream(request), max_files=4, max_fields=0)
        self.uploads: list[UploadFile] = []
        self.roles: set[str] = set()
        self.part_bytes = 0
        self.finished = False

    async def _bounded_stream(self, request: Request):
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > 4 * MAX_FILE_BYTES + 64 * 1024:
                raise _UploadTooLarge("请求过大；每文件上限 10 MiB，最多四个文件。")
            yield chunk

    def on_headers_finished(self) -> None:
        super().on_headers_finished()
        part = self._current_part
        if part.file is None:
            raise MultiPartException("仅接受四个文件字段，不接受客户端路径或其他表单字段。")
        self.uploads.append(part.file)
        role = part.field_name
        if role not in ROLES:
            raise MultiPartException(f"非法上传 role: {role}；仅允许 {', '.join(ROLES)}。")
        if role in self.roles:
            raise MultiPartException(f"重复上传 role: {role}；每个 role 必须且只能有一个文件。")
        self.roles.add(role)
        _basename(part.file.filename or "", role)
        self.part_bytes = 0

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        self.part_bytes += end - start
        if self.part_bytes > MAX_FILE_BYTES:
            raise _UploadTooLarge(f"{self._current_part.field_name}: 文件超过 10 MiB。")
        super().on_part_data(data, start, end)

    def on_part_end(self) -> None:
        if self.part_bytes == 0:
            raise MultiPartException(f"{self._current_part.field_name}: 文件为空。")
        super().on_part_end()

    def on_end(self) -> None:
        self.finished = True
        super().on_end()


def _compare_uploads(uploads: dict[str, UploadFile]) -> ComparisonResult:
    """Copy and compute in one worker; the entire request directory is disposable."""
    from hardwise.revision.engine import compare_files

    with TemporaryDirectory(prefix="hardwise-compare-") as temporary:
        paths: list[Path] = []
        for role in ROLES:
            upload = uploads[role]
            directory = Path(temporary) / role
            directory.mkdir()
            path = directory / _basename(upload.filename or "", role)
            size = 0
            nonblank = False
            with path.open("xb") as output:
                while chunk := upload.file.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_FILE_BYTES:
                        raise HTTPException(status_code=413, detail=f"{role}: 文件超过 10 MiB。")
                    nonblank = nonblank or bool(chunk.strip())
                    output.write(chunk)
            if not nonblank:
                raise HTTPException(status_code=400, detail=f"{role}: 文件为空或仅含空白。")
            paths.append(path)
        try:
            return compare_files(*paths)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"无法比较输入: {exc}") from exc


_MULTIPART_SCHEMA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": list(ROLES),
                    "additionalProperties": False,
                    "properties": {role: {"type": "string", "format": "binary"} for role in ROLES},
                }
            }
        },
    }
}


@router.post("/api/compare", response_model=ComparisonResult, openapi_extra=_MULTIPART_SCHEMA)
async def compare_uploads(request: Request) -> ComparisonResult:
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "multipart/form-data"
    ):
        raise HTTPException(status_code=415, detail="请使用 multipart/form-data 上传四个文件。")
    parser = _CompareMultipartParser(request)
    try:
        form = await parser.parse()
        if not parser.finished:
            raise MultiPartException("multipart 上传不完整，缺少结束边界。")
        if parser.roles != set(ROLES):
            missing = ", ".join(role for role in ROLES if role not in parser.roles)
            raise MultiPartException(f"缺少文件 role: {missing}。")
        uploads = {role: form[role] for role in ROLES}
        return await run_in_threadpool(_compare_uploads, uploads)
    except _UploadTooLarge as exc:
        raise HTTPException(status_code=413, detail=exc.message) from exc
    except MultiPartException as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="无效的 multipart 上传。") from exc
    finally:
        # Also covers malformed multipart, client disconnects and engine exceptions.
        for upload in parser.uploads:
            upload.file.close()


@router.get("/api/compare/demo", response_model=ComparisonResult)
def compare_demo() -> ComparisonResult:
    from hardwise.revision.demo import compare_demo_files

    return compare_demo_files()


@router.get("/compare", include_in_schema=False)
def compare_page() -> FileResponse:
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="比较界面静态文件尚未构建。")
    return FileResponse(index)


def create_compare_app() -> FastAPI:
    """Create an independent app without initializing a WorkbenchContext."""
    app = FastAPI(title="Hardwise Revision Compare", docs_url=None, redoc_url=None)
    app.include_router(router)
    app.add_api_route("/", compare_page, include_in_schema=False)
    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="compare-assets")
    return app
