from sqlalchemy import Column, Integer, ForeignKey, String
from app.db import Base

class DependencyEdge(Base):
    __tablename__ = "dependency_edges"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    from_file_id = Column(Integer, ForeignKey("repo_files.id"), nullable=False)
    to_file_id = Column(Integer, ForeignKey("repo_files.id"), nullable=False)
    edge_type = Column(String, default="import")