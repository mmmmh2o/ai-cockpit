"""应用配置"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 服务器
    host: str = "0.0.0.0"
    port: int = 8080
    auth_token: str = "sk-dev-token"
    debug: bool = True

    # 浏览器
    max_concurrent: int = 5
    screenshot_fps: int = 1
    screenshot_quality: int = 40
    default_timeout: int = 30000
    headless: bool = False

    # 路径
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Path("./data")
    profiles_dir: Path = Path("./data/profiles")
    db_path: Path = Path("./data/cockpit.db")
    logs_dir: Path = Path("./data/logs")

    class Config:
        env_prefix = "COCKPIT_"
        env_file = ".env"

    def ensure_dirs(self):
        """确保所有必要目录存在"""
        for d in [self.data_dir, self.profiles_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
