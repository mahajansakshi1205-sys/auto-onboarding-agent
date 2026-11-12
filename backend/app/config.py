from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/app.db"
    repo_storage_dir: str = "./data/repos"
    github_token: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = "./data/chroma"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
settings = Settings()