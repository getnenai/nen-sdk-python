from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SessionInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    href: str
    active: bool
    interactive: bool


class Desktop(BaseModel):
    model_config = ConfigDict(frozen=True)

    desktop_id: str
    desktop_type: str
    status: str
    workspace_id: str
    instance_id: str = ""
    public_ip: str = ""
    private_ip: str = ""
    name: str = ""
    controller_arn: str = ""
    session: SessionInfo | None = None
    created_at: int = 0
    updated_at: int = 0


class DeleteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    desktop_id: str
    status: str


class ExecuteResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    status: str = ""
    output: str = ""
    error: str = ""
    base64_image: str = ""


class ToolSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    parameters: dict = {}


class File(BaseModel):
    """A single entry from GET /desktops/{id}/files.

    ``modified`` is a Unix-epoch float with fractional seconds (the
    controller emits sub-second resolution from the on-disk mtime).
    ``is_dir`` is true for directory entries; the field defaults to
    False so older servers that omit it stay deserializable.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    size: int
    modified: float
    is_dir: bool = False


class UploadFileResponse(BaseModel):
    """Response from POST /desktops/{id}/files/{name}."""

    model_config = ConfigDict(frozen=True)

    success: bool
    size: int
    filename: str
