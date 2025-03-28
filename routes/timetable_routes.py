from flask import Blueprint, render_template, request, flash, redirect, url_for
from database import get_db_connection
from datetime import datetime, timedelta

bp = Blueprint("timetable", __name__, template_folder="../templates")

WORKING_DAYS_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


@bp.route("/view", methods=["GET"])
def view_timetable():
    sem_id = request.args.get("sem_id")
    course_id = request.args.get("course_id")
    class_id = request.args.get("class_id")

    # Initialize empty data structures
    timetable = {}
    courses = []
    classes = []
    time_slots = []
    working_days = []
    breaks = []
    selected_course = None
    selected_class = None

    if not sem_id:
        flash("Semester ID is required to view the timetable.", "danger")
        return redirect(url_for("index.dashboard"))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch semester details
        cursor.execute(
            """
        SELECT start_time, end_time, slot_duration, working_days
        FROM semesters
        WHERE sem_id = %s
        """,
            (sem_id,),
        )
        sem = cursor.fetchone()

        if not sem:
            flash("Semester not found.", "danger")
            return redirect(url_for("index.dashboard"))

        # Generate time slots
        start_time = datetime.strptime(str(sem["start_time"]), "%H:%M:%S")
        end_time = datetime.strptime(str(sem["end_time"]), "%H:%M:%S")
        slot_duration = sem["slot_duration"]

        # Handle working days
        if isinstance(sem["working_days"], str):
            days = [day.strip() for day in sem["working_days"].split(",")]
        elif isinstance(sem["working_days"], set):
            days = list(sem["working_days"])
        else:
            days = []

        # Sort working days according to standard order
        working_days = sorted(
            days,
            key=lambda x: WORKING_DAYS_ORDER.index(x)
            if x in WORKING_DAYS_ORDER
            else len(WORKING_DAYS_ORDER),
        )

        # Generate time slots
        current = start_time
        while current < end_time:
            next_time = current + timedelta(minutes=slot_duration)
            time_slots.append(
                f"{current.strftime('%H:%M')} - {next_time.strftime('%H:%M')}"
            )
            current = next_time

        # Fetch break timings
        cursor.execute(
            """
        SELECT break_name, start_time, end_time
        FROM break_timings
        WHERE sem_id = %s
        """,
            (sem_id,),
        )
        break_list = cursor.fetchall()

        # Create break mapping for each time slot
        break_mapping = {}
        for b in break_list:
            b_start = datetime.strptime(str(b["start_time"]), "%H:%M:%S")
            b_end = datetime.strptime(str(b["end_time"]), "%H:%M:%S")
            for i, slot in enumerate(time_slots):
                slot_start_str, slot_end_str = slot.split(" - ")
                slot_start = datetime.strptime(slot_start_str, "%H:%M")
                slot_end = datetime.strptime(slot_end_str, "%H:%M")
                if slot_start >= b_start and slot_end <= b_end:
                    break_mapping[i] = {"break": True, "break_name": b["break_name"]}

        # Initialize timetable grid with breaks
        timetable = {
            day: [break_mapping.get(i, None) for i in range(len(time_slots))]
            for day in working_days
        }

        # Fetch courses and classes
        cursor.execute(
            "SELECT course_id, course_name FROM courses WHERE sem_id = %s", (sem_id,)
        )
        courses = cursor.fetchall()
        cursor.execute(
            "SELECT class_id, class_name FROM classes WHERE sem_id = %s", (sem_id,)
        )
        classes = cursor.fetchall()

        # Fetch timetable entries if course_id or class_id is provided
        if course_id or class_id:
            query = """
            SELECT t.day, t.slot_id, c.course_name, c.course_abbr, cl.class_name
            FROM timetable t
            JOIN courses c ON t.course_id = c.course_id
            JOIN classes cl ON t.class_id = cl.class_id
            WHERE t.sem_id = %s
            """
            params = [sem_id]

            if course_id:
                cursor.execute(
                    "SELECT course_name FROM courses WHERE course_id = %s", (course_id,)
                )
                selected_course = cursor.fetchone()
                query += " AND t.course_id = %s"
                params.append(course_id)

            if class_id:
                cursor.execute(
                    "SELECT class_name FROM classes WHERE class_id = %s", (class_id,)
                )
                selected_class = cursor.fetchone()
                query += " AND t.class_id = %s"
                params.append(class_id)

            cursor.execute(query, tuple(params))
            results = cursor.fetchall()

            # Populate timetable grid preserving breaks
            for entry in results:
                day = entry["day"]
                slot_idx = int(entry["slot_id"]) - 1
                if (
                    day in timetable
                    and 0 <= slot_idx < len(timetable[day])
                    and not break_mapping.get(slot_idx)
                ):
                    timetable[day][slot_idx] = {
                        "course_name": entry["course_name"],
                        "course_abbr": entry["course_abbr"],
                        "room_name": entry["class_name"],
                    }

        return render_template(
            "view_timetable.html",
            selected_class=selected_class if class_id else None,
            selected_course=selected_course if course_id else None,
            sem_id=sem_id,
            timetable=timetable,
            courses=courses,
            classes=classes,
            time_slots=time_slots,
            working_days=working_days,
            breaks=break_list if "break_list" in locals() else [],
        )
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=str(e)), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route("/generate", methods=["POST"])
def generate():
    sem_id = request.form.get("semester_id")
    if not sem_id:
        flash("Semester ID is missing.", "danger")
        return redirect(url_for("semester.manage_semesters"))

    # Compute the timetable grid using our in-file algorithm.
    grid = generate_timetable_for_semester(sem_id)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM timetable WHERE sem_id = %s", (sem_id,))

            # Save the generated timetable to the database.
            # Grid structure: { day: { class_id: [slot, slot, ...] } }
            for day, classes_dict in grid.items():
                for class_id, slots in classes_dict.items():
                    for i, slot in enumerate(slots):
                        # Insert only if the slot is not empty and not a break marker.
                        if slot is not None and not slot.get("break", False):
                            cursor.execute(
                                """
                            INSERT INTO timetable (sem_id, class_id, day, slot_id, course_id)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                                (sem_id, class_id, day, i + 1, slot["course_id"]),
                            )
            conn.commit()
            flash("Timetable generated successfully!", "success")
            return redirect(url_for("timetable.view_timetable", sem_id=sem_id))
        except Exception as e:
            conn.rollback()
            raise e
    except Exception as e:
        flash("Error generating timetable: " + str(e), "danger")
        return render_template("error.html", error=str(e)), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Timetable Generation Algorithm (integrated in this file)


def generate_timetable_for_semester(sem_id):
    """
    Compute a timetable grid for the given semester.
    Grid structure: { day: { class_id: [slot, slot, ...] } }.
    This function takes into account both daily and weekly slot limits for each course.
    It returns a grid where break slots are marked (and skipped for assignments).
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch semester details.
        cursor.execute(
            """
            SELECT start_time, end_time, slot_duration, working_days
            FROM semesters
            WHERE sem_id = %s
        """,
            (sem_id,),
        )
        sem = cursor.fetchone()
        if not sem:
            return {}

        # Convert times.
        start_time = datetime.strptime(str(sem["start_time"]), "%H:%M:%S")
        end_time = datetime.strptime(str(sem["end_time"]), "%H:%M:%S")
        slot_duration = sem["slot_duration"]

        # Generate time slot labels.
        time_slots = []
        current = start_time
        while current < end_time:
            next_time = current + timedelta(minutes=slot_duration)
            time_slots.append(
                f"{current.strftime('%H:%M')} - {next_time.strftime('%H:%M')}"
            )
            current = next_time

        # Process working_days.
        if sem["working_days"]:
            if isinstance(sem["working_days"], set):
                working_days = list(sem["working_days"])
            else:
                working_days = sem["working_days"].split(",")
        else:
            working_days = []

        # Fetch break timings and build mapping for break slots.
        cursor.execute(
            "SELECT break_name, start_time, end_time FROM break_timings WHERE sem_id = %s",
            (sem_id,),
        )
        break_list = cursor.fetchall()
        break_mapping = {}
        for b in break_list:
            b_start = datetime.strptime(str(b["start_time"]), "%H:%M:%S")
            b_end = datetime.strptime(str(b["end_time"]), "%H:%M:%S")
            for i, slot in enumerate(time_slots):
                slot_start_str, slot_end_str = slot.split(" - ")
                slot_start = datetime.strptime(slot_start_str, "%H:%M")
                slot_end = datetime.strptime(slot_end_str, "%H:%M")
                if slot_start >= b_start and slot_end <= b_end:
                    break_mapping[i] = b["break_name"]

        # Initialize grid: { day: { class_id: [slot, slot, ...] } }
        grid = {}
        for day in working_days:
            grid[day] = {}
            for cls in sorted(
                get_classes_for_semester(cursor, sem_id), key=lambda x: x["capacity"]
            ):
                grid[day][cls["class_id"]] = [
                    {"break": True, "break_name": break_mapping[i]}
                    if i in break_mapping
                    else None
                    for i in range(len(time_slots))
                ]

        # Fetch courses using the daily constraint.
        cursor.execute(
            """
            SELECT course_id, course_name, max_minutes_per_day, max_minutes_per_week, num_students
            FROM courses
            WHERE sem_id = %s
        """,
            (sem_id,),
        )
        courses = cursor.fetchall()
        # Sort courses by max_minutes_per_day descending (higher daily need first).
        courses.sort(key=lambda x: x["max_minutes_per_day"], reverse=True)

        # Greedy assignment: For each course, assign slots per day up to daily limit,
        # ensuring total assignments don't exceed weekly limit.
        for course in courses:
            course_id = course["course_id"]
            daily_limit = course["max_minutes_per_day"] // slot_duration
            weekly_limit = course["max_minutes_per_week"] // slot_duration
            weekly_assigned = 0
            course_strength = course["num_students"]

            # For each working day, try to assign slots in best-fit rooms.
            for day in working_days:
                if weekly_assigned >= weekly_limit:
                    break
                daily_assigned = 0
                # Iterate over classes (rooms) sorted by capacity.
                for cls in sorted(
                    get_classes_for_semester(cursor, sem_id),
                    key=lambda x: x["capacity"],
                ):
                    if cls["capacity"] < course_strength:
                        continue  # Room too small.
                    # Iterate over time slots.
                    for i in range(len(time_slots)):
                        if (
                            weekly_assigned >= weekly_limit
                            or daily_assigned >= daily_limit
                        ):
                            break
                        if i in break_mapping:
                            continue
                        if grid[day][cls["class_id"]][i] is None:
                            grid[day][cls["class_id"]][i] = {
                                "course_id": course_id,
                                "course_name": course["course_name"],
                            }
                            weekly_assigned += 1
                            daily_assigned += 1
                    if daily_assigned >= daily_limit:
                        # Move to next day after filling daily limit in one room (or combination).
                        break
        return grid
    except Exception as e:
        print("Error in generate_timetable_for_semester:", e)
        return {}
    finally:
        cursor.close()
        conn.close()


def get_classes_for_semester(cursor, sem_id):
    """
    Helper function to fetch classes for the given semester.
    """
    cursor.execute(
        "SELECT class_id, capacity FROM classes WHERE sem_id = %s", (sem_id,)
    )
    return cursor.fetchall()
