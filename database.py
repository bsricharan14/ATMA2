import mysql.connector
from flask import current_app


def get_db_connection():
    db_config = {
        "host": current_app.config.get("DATABASE_HOST", "127.0.0.1"),
        "user": current_app.config.get("DATABASE_USER", "root"),
        "password": current_app.config.get("DATABASE_PASSWORD", "password"),
        "database": current_app.config.get("DATABASE_NAME", "project"),
    }
    return mysql.connector.connect(**db_config)
