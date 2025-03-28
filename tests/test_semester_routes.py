import sys
import os
import io
import unittest
from unittest.mock import patch
from werkzeug.datastructures import FileStorage
from app import create_app
from config import TestConfig
from database import get_db_connection

# Ensure the project root is in sys.path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Dummy classes to simulate a database failure.
class DummyCursor:
    def execute(self, *args, **kwargs):
        raise Exception("Database error")

    def close(self):
        pass


class DummyConn:
    def __init__(self):
        self.rollback_called = False

    def cursor(self, *args, **kwargs):
        return DummyCursor()

    def commit(self):
        pass

    def rollback(self):
        self.rollback_called = True

    def close(self):
        pass


class TestSemesterRoutes(unittest.TestCase):
    def setUp(self):
        # Create an application with the test configuration.
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        # Create a test semester using the exposed endpoint.
        data = {
            "sem_name": "Test Semester",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "slot_duration": "60",
            "working_days": ["Monday"],
        }
        response = self.client.post(
            "/semesters/create", data=data, follow_redirects=False
        )
        location = response.headers.get("Location", "")
        if "sem_id=" in location:
            self.sem_id = location.split("sem_id=")[-1]
        else:
            self.sem_id = "1"  # Fallback

    def tearDown(self):
        # Clean up: delete the test semester if it still exists.
        with self.app.app_context():
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM semesters WHERE sem_id = %s", (self.sem_id,)
                )
                conn.commit()
            except Exception:
                pass
            finally:
                try:
                    cursor.close()
                    conn.close()
                except Exception:
                    pass

    def test_create_semester_get(self):
        response = self.client.get("/semesters/create")
        self.assertEqual(response.status_code, 200)

    def test_create_semester_post_and_db(self):
        data = {
            "sem_name": "Another Semester",
            "start_time": "09:00:00",
            "end_time": "16:00:00",
            "slot_duration": "60",
            "working_days": ["Tuesday"],
        }
        response = self.client.post(
            "/semesters/create", data=data, follow_redirects=False
        )
        self.assertIn(response.status_code, [302, 303])
        location = response.headers.get("Location", "")
        self.assertIn("sem_id=", location)
        new_sem_id = location.split("sem_id=")[-1]
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM semesters WHERE sem_id = %s", (new_sem_id,))
            sem_record = cursor.fetchone()
            self.assertIsNotNone(sem_record)
            self.assertEqual(sem_record["sem_name"], "Another Semester")
            cursor.close()
            conn.close()

    def test_create_semester_post_with_missing_fields(self):
        data = {
            "sem_name": "Incomplete Semester",
            "start_time": "09:00:00",
            "end_time": "16:00:00",
            "slot_duration": "60"
            # working_days missing
        }
        response = self.client.post("/semesters/create", data=data)
        self.assertEqual(response.status_code, 400)

    def test_create_semester_exception(self):
        data = {
            "sem_name": "Exception Semester",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "slot_duration": "60",
            "working_days": ["Monday"],
        }
        with patch(
            "routes.semester_routes.get_db_connection",
            side_effect=Exception("DB Error"),
        ):
            response = self.client.post("/semesters/create", data=data)
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Error creating semester: DB Error", response.data)

    def test_create_semester_with_breaks(self):
        data = {
            "sem_name": "Break Semester",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "slot_duration": "60",
            "working_days": ["Monday", "Tuesday"],
            "break_name[]": ["Lunch", ""],  # one valid, one missing
            "break_start[]": ["12:00:00", "13:00:00"],
            "break_end[]": ["13:00:00", "14:00:00"],
        }
        response = self.client.post(
            "/semesters/create", data=data, follow_redirects=False
        )
        self.assertIn(response.status_code, [302, 303])
        new_sem_id = response.headers.get("Location").split("sem_id=")[-1]
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM break_timings WHERE sem_id = %s", (new_sem_id,)
            )
            breaks = cursor.fetchall()
            self.assertEqual(
                len(breaks), 1
            )  # Only the complete break should be inserted.
            cursor.close()
            conn.close()

    def test_manage_semesters_get(self):
        response = self.client.get("/semesters/manage_semesters")
        self.assertEqual(response.status_code, 200)

    def test_delete_semester_and_db(self):
        response = self.client.post(
            "/semesters/delete", data={"semester_id": self.sem_id}
        )
        self.assertIn(response.status_code, [302, 303])
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM semesters WHERE sem_id = %s", (self.sem_id,))
            sem_record = cursor.fetchone()
            self.assertIsNone(sem_record)
            cursor.close()
            conn.close()

    def test_delete_missing_semester_id(self):
        response = self.client.post("/semesters/delete", data={})
        self.assertEqual(response.status_code, 400)

    def test_delete_exception(self):
        with patch(
            "routes.semester_routes.get_db_connection",
            side_effect=Exception("Delete Error"),
        ):
            response = self.client.post(
                "/semesters/delete", data={"semester_id": self.sem_id}
            )
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Error deleting semester: Delete Error", response.data)

    def test_add_classes_manually_and_db(self):
        data = {"class_name[]": ["Room A"], "capacity[]": ["30"]}
        response = self.client.post(
            f"/semesters/add_classes?sem_id={self.sem_id}", data=data
        )
        self.assertIn(response.status_code, [302, 303])
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM classes WHERE sem_id = %s AND class_name = %s",
                (self.sem_id, "Room A"),
            )
            class_record = cursor.fetchone()
            self.assertIsNotNone(class_record)
            self.assertEqual(int(class_record["capacity"]), 30)
            cursor.close()
            conn.close()

    def test_add_classes_csv_and_db(self):
        csv_content = "class_name,class_capacity\nRoom B,40\n"
        csv_file = FileStorage(
            stream=io.BytesIO(csv_content.encode("utf-8")),
            filename="classes.csv",
            content_type="text/csv",
        )
        data = {"csv_upload": csv_file}
        response = self.client.post(
            f"/semesters/add_classes?sem_id={self.sem_id}", data=data
        )
        self.assertIn(response.status_code, [302, 303])
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM classes WHERE sem_id = %s AND class_name = %s",
                (self.sem_id, "Room B"),
            )
            class_record = cursor.fetchone()
            self.assertIsNotNone(class_record)
            self.assertEqual(int(class_record["capacity"]), 40)
            cursor.close()
            conn.close()

    def test_add_classes_missing_sem_id(self):
        response = self.client.get("/semesters/add_classes")
        self.assertIn(response.status_code, [302, 303])

    def test_add_classes_exception(self):
        # Simulate DB failure in add_classes by patching get_db_connection to return our DummyConn.
        with patch(
            "routes.semester_routes.get_db_connection", side_effect=lambda: DummyConn()
        ):
            data = {"class_name[]": ["Room C"], "capacity[]": ["50"]}
            response = self.client.post(
                f"/semesters/add_classes?sem_id={self.sem_id}", data=data
            )
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Error adding classes: Database error", response.data)

    def test_add_courses_manually_and_db(self):
        data = {
            "course_name[]": ["Math 101"],
            "course_abbr[]": ["MTH101"],
            "num_students[]": ["25"],
            "max_minutes_per_week[]": ["180"],
            "max_minutes_per_day[]": ["60"],
            "min_minutes_per_day[]": ["60"],
        }
        response = self.client.post(f"/semesters/add_courses/{self.sem_id}", data=data)
        self.assertIn(response.status_code, [302, 303])
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM courses WHERE sem_id = %s AND course_name = %s",
                (self.sem_id, "Math 101"),
            )
            course_record = cursor.fetchone()
            self.assertIsNotNone(course_record)
            self.assertEqual(int(course_record["num_students"]), 25)
            cursor.close()
            conn.close()

    def test_add_courses_csv_and_db(self):
        csv_content = (
            "course_name,num_students,max_minutes_per_week,max_minutes_per_day,min_minutes_per_day,course_abbr\n"
            "Physics 101,30,180,60,60,PHY101\n"
        )
        csv_file = FileStorage(
            stream=io.BytesIO(csv_content.encode("utf-8")),
            filename="courses.csv",
            content_type="text/csv",
        )
        data = {"csv_upload": csv_file}
        response = self.client.post(f"/semesters/add_courses/{self.sem_id}", data=data)
        self.assertIn(response.status_code, [302, 303])
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM courses WHERE sem_id = %s AND course_name = %s",
                (self.sem_id, "Physics 101"),
            )
            course_record = cursor.fetchone()
            self.assertIsNotNone(course_record)
            self.assertEqual(course_record["course_abbr"], "PHY101")
            self.assertEqual(int(course_record["num_students"]), 30)
            cursor.close()
            conn.close()

    def test_add_courses_missing_sem_id(self):
        response = self.client.get("/semesters/add_courses/")
        self.assertEqual(response.status_code, 404)

    def test_add_courses_exception(self):
        with patch(
            "routes.semester_routes.get_db_connection",
            side_effect=Exception("Add Courses Error"),
        ):
            data = {
                "course_name[]": ["Chemistry 101"],
                "course_abbr[]": ["CHEM101"],
                "num_students[]": ["20"],
                "max_minutes_per_week[]": ["120"],
                "max_minutes_per_day[]": ["60"],
                "min_minutes_per_day[]": ["60"],
            }
            response = self.client.post(
                f"/semesters/add_courses/{self.sem_id}", data=data
            )
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Error adding courses: Add Courses Error", response.data)

    def test_manage_semester_exception(self):
        # Simulate ValueError when converting capacity by patching int.
        with patch(
            "routes.semester_routes.int", side_effect=ValueError("Invalid conversion")
        ):
            data = {
                "class_name[]": ["Test Class"],
                "capacity[]": [
                    "invalid"
                ],  # This should trigger ValueError and lead to capacity_value = 0.
            }
            response = self.client.post(
                f"/semesters/add_classes?sem_id={self.sem_id}", data=data
            )
            # Since capacity_value becomes 0, the INSERT is skipped and the form re-renders.
            self.assertEqual(response.status_code, 303)


if __name__ == "__main__":
    unittest.main()
