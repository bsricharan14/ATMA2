from flask import Blueprint, render_template, jsonify

bp = Blueprint("index", __name__, template_folder="../templates")


@bp.route("/", methods=["GET"])
def home():
    try:
        return render_template("index.html"), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        return render_template("dashboard.html"), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
