from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/denial_recovery"
    secret_key: str = "dev-secret-change-me"
    upload_dir: str = "storage/uploads"

    # --- LLM provider abstraction -----------------------------------------
    # LLM_PROVIDER selects which chat model backend LangChain uses.
    # Supported: "ollama" (local, default), "anthropic", "groq".
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:8b"
    llm_temperature: float = 0.1

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"  # kept for backward compatibility with older .env files
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # --- Embeddings / RAG ---------------------------------------------------
    # EMBEDDING_PROVIDER: "local" (dependency-free hashing embedding, default,
    # always works offline) or "ollama" (uses an Ollama embedding model).
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    vectorstore_dir: str = "storage/vectorstore"
    policy_data_dir: str = "data/policies"
    evidence_data_dir: str = "data/evidence"
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 4

    # --- Workflow / graph -----------------------------------------------------
    confidence_threshold: float = 0.90
    high_value_threshold: float = 100000
    # When True (default, recommended for healthcare demos) every appeal -
    # regardless of AI confidence - pauses at the human review gate before
    # submission. When False, high-confidence + low-value appeals may be
    # auto-approved without a human click (still logged in the audit trail).
    require_human_approval: bool = True
    checkpoint_db_path: str = "storage/checkpoints.sqlite"
    estimated_cloud_cost_per_1k_tokens_usd: float = 0.001
    rocketrider_enabled: bool = True
    rocketrider_pipeline_name: str = "denial-recovery-load-bearing.pipe"
    rocketrider_webhook_key: str = ""

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
