"""File upload demo blueprint."""

import os
import uuid
from kewe import Blueprint, Request, json, File
from kewe.errors.exceptions import NotFound, BadRequest
from models.schemas import uploads_store

upload_bp = Blueprint("upload", url_prefix="/api/upload")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@upload_bp.post("/")
async def upload_file(request: Request):
    """Upload a file via multipart form. Uses KeWe's streaming multipart parser."""
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        raise BadRequest("Expected multipart/form-data")

    boundary = content_type.split("boundary=")[-1].strip()
    if not boundary:
        raise BadRequest("No boundary found in content-type")

    # Read raw body
    body = await request.body
    parts = _parse_multipart(body, boundary)

    uploaded = []
    for part in parts:
        headers, data = part
        filename = _extract_filename(headers) or f"upload_{uuid.uuid4().hex[:8]}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(data)

        file_id = str(uuid.uuid4())[:8]
        uploads_store[file_id] = {
            "id": file_id,
            "original_name": filename,
            "path": filepath,
            "size": len(data),
        }
        uploaded.append(uploads_store[file_id])

    return json({"uploaded": uploaded, "count": len(uploaded)}, status=201)


def _parse_multipart(body: bytes, boundary: str):
    """Simple multipart parser for demo purposes."""
    boundary_bytes = boundary.encode()
    parts = []
    raw_parts = body.split(b"--" + boundary_bytes)

    for raw in raw_parts:
        if not raw or raw == b"--":
            continue
        # Split headers and body
        if b"\r\n\r\n" in raw:
            header_section, data = raw.split(b"\r\n\r\n", 1)
            # Remove trailing boundary markers
            if data.endswith(b"\r\n"):
                data = data[:-2]
            if data.endswith(b"--"):
                data = data[:-2]
            # Check for closing boundary
            if not data or data == b"--\r\n":
                continue
            parts.append((header_section.decode(errors="replace"), data))

    return parts


def _extract_filename(headers: str) -> str | None:
    """Extract filename from Content-Disposition header."""
    for line in headers.split("\r\n"):
        line_lower = line.lower()
        if "content-disposition" in line_lower and "filename" in line_lower:
            parts = line.split("filename=")
            if len(parts) > 1:
                filename = parts[1].strip().strip('"')
                return os.path.basename(filename)
    return None


@upload_bp.get("/")
async def list_uploads():
    """List all uploaded files."""
    return json(list(uploads_store.values()))


@upload_bp.get("/{file_id:str}")
async def get_upload_info(file_id: str):
    """Get info about a specific upload."""
    info = uploads_store.get(file_id)
    if info is None:
        raise NotFound(f"File {file_id} not found")
    return json(info)
