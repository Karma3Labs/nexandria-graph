from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):  
    NEXANDRIA_URL:str = 'https://api.nexandria.com'
    NEXANDRIA_API_KEY:str = 'nexandria'
    NEXANDRIA_MAX_CONCURRENCY: int = 5
    NEXANDRIA_TIMEOUT_MS: int = 60
    NEXANDRIA_RATE_LIMIT:int = 12

    LOG_LEVEL: str = 'INFO'

    ADDRESS_SKIP_LIST: str = '/tmp/non_eoa_address.txt'
    RELOAD_FREQ_SECS: int = 3600

    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=('.env', '.env.prod')
    )

settings = Settings()