import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    owner = Column(String, nullable=False)
    name = Column(String, nullable=False)
    local_path = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | cloning | ready | failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    files = relationship("RepoFile", back_populates="repository", cascade="all, delete-orphan")

class RepoFile(Base):
    __tablename__ = "repo_files"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    relative_path = Column(String, nullable=False)
    extension = Column(String, nullable=True)
    size_bytes = Column(Integer, default=0)
    line_count = Column(Integer, default=0)

    repository = relationship("Repository", back_populates="files")