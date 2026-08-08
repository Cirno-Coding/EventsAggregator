from app.core.config import Settings, get_settings


def get_app_settings() -> Settings:
    """Вернуть общие настройки приложения для FastAPI dependecy"""
    return get_settings()
