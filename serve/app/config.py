from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr

class Settings(BaseSettings):  
    NEXANDRIA_URL: str = 'https://api.nexandria.com'
    NEXANDRIA_API_KEY: SecretStr = 'nexandria'
    NEXANDRIA_MAX_CONCURRENCY: int = 5
    NEXANDRIA_TIMEOUT_MS: int = 5000

    GO_EIGENTRUST_URL:str = 'http://localhost:8080'
    GO_EIGENTRUST_TIMEOUT_MS:int = 3000
    EIGENTRUST_ALPHA:float = 0.5
    EIGENTRUST_EPSILON:float = 1.0
    EIGENTRUST_MAX_ITER:int = 50
    EIGENTRUST_FLAT_TAIL:int = 2
    
    DEFAULT_TRANSFER_VALUE: float = 0.0001

    LOG_LEVEL: str = 'INFO'

    NON_EOA_LIST: str = '/tmp/non_eoa_address.csv'
    RELOAD_FREQ_SECS: int = 3600

    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=('.env', '.env.prod')
    )

    @computed_field
    def NEXANDRIA_TIMEOUT_SECS(self) -> str:
        return self.NEXANDRIA_TIMEOUT_MS/1000.0

settings = Settings()