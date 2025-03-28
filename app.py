from flask import Flask
from routes.index_routes import bp as index_bp
from routes.semester_routes import bp as semester_bp
from routes.timetable_routes import bp as timetable_bp
from config import Config


def create_app(config=None):
    app = Flask(__name__)
    # Load default configuration
    app.config.from_object(Config)

    # If config is provided, check its type.
    if config:
        if isinstance(config, dict):
            app.config.update(config)
        else:
            # Assume it's a config object
            app.config.from_object(config)

    # Register blueprints with optional URL prefixes.
    app.register_blueprint(index_bp)
    app.register_blueprint(semester_bp, url_prefix="/semesters")
    app.register_blueprint(timetable_bp, url_prefix="/timetable")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
