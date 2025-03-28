from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_db_connection
import io
import csv

bp = Blueprint("semester", __name__, template_folder="../templates")


@bp.route("/create", methods=["GET", "POST"])
def create_semester():
    if request.method == "GET":
        return render_template("create_semester.html"), 200

    try:
        sem_name = request.form.get("sem_name", "").strip()
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        slot_duration = request.form.get("slot_duration")
        working_days = request.form.getlist("working_days")

        if not all([sem_name, start_time, end_time, slot_duration, working_days]):
            flash("All fields are required", "danger")
            return render_template("create_semester.html"), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            working_days_str = ",".join(working_days)

            semester_query = """
            INSERT INTO semesters (sem_name, start_time, end_time, working_days, slot_duration)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(
                semester_query,
                (sem_name, start_time, end_time, working_days_str, slot_duration),
            )
            sem_id = cursor.lastrowid

            # Handle break timings
            break_names = request.form.getlist("break_name[]")
            break_starts = request.form.getlist("break_start[]")
            break_ends = request.form.getlist("break_end[]")
            break_query = """
            INSERT INTO break_timings (sem_id, break_name, start_time, end_time)
            VALUES (%s, %s, %s, %s)
            """
            for bname, bstart, bend in zip(break_names, break_starts, break_ends):
                if all([bname, bstart, bend]):
                    cursor.execute(break_query, (sem_id, bname.strip(), bstart, bend))

            conn.commit()
            flash("Semester created successfully!", "success")
            return redirect(url_for("semester.add_classes", sem_id=sem_id)), 303
        except Exception as e:
            conn.rollback()
            raise e
    except Exception as e:
        return jsonify({"error": f"Error creating semester: {str(e)}"}), 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()


@bp.route("/manage_semesters", methods=["GET"])
def manage_semesters():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM semesters")
        semesters = cursor.fetchall()
        return render_template("manage_semesters.html", semesters=semesters), 200
    except Exception as e:
        flash(f"Error retrieving semesters: {str(e)}", "danger")
        return render_template("manage_semesters.html", semesters=[]), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route("/delete", methods=["POST"])
def delete():
    sem_id = request.form.get("semester_id")
    if not sem_id:
        flash("Semester ID is missing.", "danger")
        return redirect(url_for("semester.manage_semesters")), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM courses WHERE sem_id = %s", (sem_id,))
            cursor.execute("DELETE FROM classes WHERE sem_id = %s", (sem_id,))
            cursor.execute("DELETE FROM semesters WHERE sem_id = %s", (sem_id,))
            conn.commit()
            flash("Semester deleted successfully!", "success")
            return redirect(url_for("semester.manage_semesters")), 303
        except Exception as e:
            conn.rollback()
            raise e
    except Exception as e:
        return jsonify({"error": f"Error deleting semester: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route("/add_classes", methods=["GET", "POST"])
def add_classes():
    sem_id = request.args.get("sem_id")
    if not sem_id:
        flash("Semester ID is missing.", "danger")
        return redirect(url_for("semester.manage_semesters"))

    if request.method == "POST":
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                class_names = request.form.getlist("class_name[]")
                capacities = request.form.getlist("capacity[]")

                class_query = """
                INSERT INTO classes (sem_id, class_name, capacity)
                VALUES (%s, %s, %s)
                """
                for cname, cap in zip(class_names, capacities):
                    cname = cname.strip()
                    cap = cap.strip()
                    if cname and cap:
                        try:
                            capacity_value = int(cap)
                        except ValueError:
                            capacity_value = 0
                        if capacity_value > 0:
                            cursor.execute(class_query, (sem_id, cname, capacity_value))

                csv_file = request.files.get("csv_upload")
                if csv_file and csv_file.filename != "":
                    stream = io.StringIO(
                        csv_file.stream.read().decode("UTF8"), newline=None
                    )
                    reader = csv.reader(stream)
                    next(reader)  # Skip header row
                    for row in reader:
                        if len(row) >= 2:
                            cname = row[0].strip()
                            cap = row[1].strip()
                            if cname and cap:
                                try:
                                    capacity_value = int(cap)
                                except ValueError:
                                    capacity_value = 0
                                if capacity_value > 0:
                                    cursor.execute(
                                        class_query, (sem_id, cname, capacity_value)
                                    )

                conn.commit()
                flash("Classes added successfully!", "success")
                return redirect(url_for("semester.add_courses", sem_id=sem_id)), 303
            except Exception as e:
                conn.rollback()
                raise e
        except Exception as e:
            return jsonify({"error": f"Error adding classes: {str(e)}"}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("add_classes.html", sem_id=sem_id)


@bp.route("/add_courses/<sem_id>", methods=["GET", "POST"])
def add_courses(sem_id):
    if request.method == "POST":
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            try:
                csv_file = request.files.get("csv_upload")
                if (
                    csv_file
                    and csv_file.filename
                    and csv_file.filename.endswith(".csv")
                ):
                    stream = io.StringIO(
                        csv_file.stream.read().decode("UTF8"), newline=None
                    )
                    reader = csv.reader(stream)
                    next(reader)
                    for row in reader:
                        if len(row) >= 6:
                            cursor.execute(
                                """
                            INSERT INTO courses (sem_id, course_name, num_students, max_minutes_per_week, max_minutes_per_day, min_minutes_per_day, course_abbr)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                                (
                                    sem_id,
                                    row[0].strip(),
                                    row[1].strip(),
                                    row[2].strip(),
                                    row[3].strip(),
                                    row[4].strip(),
                                    row[5].strip(),
                                ),
                            )

                course_names = request.form.getlist("course_name[]")
                course_abbr = request.form.getlist("course_abbr[]")
                num_students_list = request.form.getlist("num_students[]")
                max_minutes_week = request.form.getlist("max_minutes_per_week[]")
                max_minutes_day = request.form.getlist("max_minutes_per_day[]")
                min_minutes_day = request.form.getlist("min_minutes_per_day[]")

                for i in range(len(course_names)):
                    if (
                        i < len(course_names)
                        and i < len(course_abbr)
                        and i < len(num_students_list)
                        and i < len(max_minutes_week)
                        and i < len(max_minutes_day)
                        and i < len(min_minutes_day)
                    ):
                        cursor.execute(
                            """
                        INSERT INTO courses (sem_id, course_name, num_students, max_minutes_per_week, max_minutes_per_day, min_minutes_per_day, course_abbr)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                            (
                                sem_id,
                                course_names[i].strip(),
                                num_students_list[i].strip(),
                                max_minutes_week[i].strip(),
                                max_minutes_day[i].strip(),
                                min_minutes_day[i].strip(),
                                course_abbr[i].strip(),
                            ),
                        )

                conn.commit()
                flash("Courses added successfully!", "success")
                return redirect(url_for("semester.manage_semesters")), 303
            except Exception as e:
                conn.rollback()
                raise e
        except Exception as e:
            return jsonify({"error": f"Error adding courses: {str(e)}"}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("add_courses.html", sem_id=sem_id)
