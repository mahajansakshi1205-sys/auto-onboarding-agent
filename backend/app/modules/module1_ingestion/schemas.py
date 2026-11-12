from pydantic import BaseModel, HttpUrl

class IngestRequest(BaseModel):
    repo_url: HttpUrl

class RepoFileOut(BaseModel):
    relative_path: str
    extension: str | None
    size_bytes: int
    line_count: int

    class Config:
        from_attributes = True

class RepositoryOut(BaseModel):
    id: int
    url: str
    owner: str
    name: str
    status: str
    error_message: str | None
    file_count: int | None = None

    class Config:
        from_attributes = True