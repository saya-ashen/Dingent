from functools import lru_cache

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dingent.core.managers.user_secret_manager import UserSecretManager


class Settings(BaseSettings):
    """
    应用的核心配置模型。
    从环境变量或 .env 文件加载配置。
    """

    # Pydantic v2 的配置方式，用于从 .env 文件加载
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

    # --- 1. 核心部署配置 ---
    # 应用的运行环境: "development", "staging", "production"
    ENVIRONMENT: str = "development"
    # 后端服务监听的端口
    BACKEND_PORT: int = 8000

    # --- 2. 项目元数据 ---
    PROJECT_NAME: str = "Dingent"
    API_V1_STR: str = "/api/v1"

    # --- 3. 数据库配置 ---
    # 数据库连接字符串
    # 示例: "postgresql+asyncpg://user:password@host:port/db"
    # 对于本地开发，SQLite 是一个好的开始
    DATABASE_URL: str = "sqlite:///./dingent.db"

    # --- 4. 关键安全配置 ---
    # 应用的全局主加密密钥，用于保护用户个人密钥
    # 这个值没有默认值，必须在环境中设置，否则应用会启动失败
    APP_MASTER_KEY: SecretStr

    # FIXME:
    # @field_validator("APP_MASTER_KEY")
    # @classmethod
    # def validate_master_key(cls, v: SecretStr) -> SecretStr:
    #     """验证主密钥是否是有效的 Fernet 密钥格式。"""
    #     if not v:
    #         raise ValueError("APP_MASTER_KEY cannot be empty.")
    #     try:
    #         # 一个有效的 Fernet 密钥是 32 字节且经过 URL-safe base64 编码的
    #         key_bytes = base64.urlsafe_b64decode(v.get_secret_value())
    #         if len(key_bytes) != 32:
    #             raise ValueError("Master key must be exactly 32 bytes long after decoding.")
    #         return v
    #     except Exception as e:
    #         raise ValueError(f"Invalid APP_MASTER_KEY. It must be a URL-safe base64-encoded 32-byte key. Error: {e}")

    # --- 5. 派生属性和单例服务 ---
    @computed_field(return_type=UserSecretManager)
    @property
    def user_secret_manager(self) -> UserSecretManager:
        """
        一个计算属性，它使用加载的 APP_MASTER_KEY 创建并返回
        一个 UserSecretManager 的单例实例。
        应用的其余部分应该使用这个实例，而不是自己创建。
        """
        # .get_secret_value() 用于安全地取出 SecretStr 中的真实值
        return UserSecretManager(self.APP_MASTER_KEY.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
