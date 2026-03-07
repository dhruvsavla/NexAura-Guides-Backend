import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    secret_key: str
    frontend_url: str = "http://localhost:3000" # Added a default fallback!
    openai_api_key: str                         # Added this line!

    class Config:
        # Dynamically choose the file based on the OS environment
        env_file = ".env.prod" if os.getenv("APP_ENV") == "production" else ".env.dev"
        env_file_encoding = "utf-8"
        extra = "ignore" # Optional: This tells Pydantic to ignore any other extra variables in your .env file instead of crashing

# Instantiate the settings once
settings = Settings()