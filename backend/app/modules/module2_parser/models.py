from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base

class ParsedSymbol(Base):
    __tablename__ = "parsed_symbols"

    id = Column(Integer, primary_key=True, index=True)
    repo_file_id = Column(Integer, ForeignKey("repo_files.id"), nullable=False)
    symbol_type = Column(String, nullable=False)   # "function" | "class" | "import"
    name = Column(String, nullable=False)
    lineno = Column(Integer, nullable=False)
    docstring = Column(Text, nullable=True)