import os


class Config:
    SECRET_KEY = os.urandom(24)
    DATABASE_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
    DATABASE_USER = os.getenv("DATABASE_USER", "root")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "project")


class TestConfig(Config):
    TESTING = True
    # Use a separate database name for tests
    DATABASE_NAME = os.getenv("TEST_DATABASE_NAME", "test_database")
