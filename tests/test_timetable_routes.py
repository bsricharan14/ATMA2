import sys
import os
import unittest
from unittest.mock import patch
from app import create_app
from config import TestConfig
from database import get_db_connection
from routes.timetable_routes import generate_timetable_for_semester

# Ensure project root is in sys.path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Dummy classes to simulate database failures without using MagicMock.
class DummyCursor:
    def execute(self, *args, **kwargs):
        raise Exception("Database error")

    def fetchone(self):
        return None

    def fetchall(self):
        return []

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


# Dummy cursor for simulating "semester not found" scenario.
class DummyCursor2:
    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class TestTimetableRoutes(unittest.TestCase):
    def setUp(self):
        # Create an application with the test configuration.
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        # Create a test semester via the endpoint, including break data.
        sem_data = {
            "sem_name": "Timetable Test Semester",
            "start_time": "08:00:00",
            "end_time": "12:00:00",  # 4 slots per day: 08-09, 09-10, 10-11, 11-12
            "slot_duration": "60",
            "working_days": ["Monday", "Tuesday"],
            # Include break timing so that break mapping is exercised.
            "break_name[]": ["Lunch Break"],
            "break_start[]": ["10:00:00"],
            "break_end[]": ["10:30:00"],
        }
        response = self.client.post(
            "/semesters/create", data=sem_data, follow_redirects=False
        )
        location = response.headers.get("Location", "")
        if "sem_id=" in location:
            self.sem_id = location.split("sem_id=")[-1]
        else:
            self.sem_id = "1"  # fallback

        # Add a class (room) via the endpoint.
        class_data = {"class_name[]": ["Test Room"], "capacity[]": ["50"]}
        self.client.post(
            f"/semesters/add_classes?sem_id={self.sem_id}", data=class_data
        )

        # Add a course via the endpoint.
        # Test Course: 40 students; max_minutes_per_week=120, max_minutes_per_day=60.
        course_data = {
            "course_name[]": ["Test Course"],
            "course_abbr[]": ["TC"],
            "num_students[]": ["40"],
            "max_minutes_per_week[]": ["120"],  # 2 slots total
            "max_minutes_per_day[]": ["60"],  # 1 slot per day
            "min_minutes_per_day[]": ["60"],
        }
        self.client.post(f"/semesters/add_courses/{self.sem_id}", data=course_data)

    def tearDown(self):
        # Clean up: delete the test semester (cascading deletion).
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

    def test_view_timetable_without_sem_id(self):
        response = self.client.get("/timetable/view")
        self.assertIn(response.status_code, [302, 303])

    def test_view_timetable_semester_not_found(self):
        with patch("routes.timetable_routes.get_db_connection") as mock_get_db:
            dummy_conn = DummyConn()
            dummy_cursor = DummyCursor2()
            dummy_conn.cursor = lambda *args, **kwargs: dummy_cursor
            mock_get_db.return_value = dummy_conn

            response = self.client.get("/timetable/view?sem_id=99999")

            self.assertIn(response.status_code, [302, 303])

    def test_view_timetable_with_valid_sem_id(self):
        response = self.client.get(f"/timetable/view?sem_id={self.sem_id}")
        self.assertIn(response.status_code, [200, 302, 303])

    def test_view_timetable_with_course_and_class(self):
        response = self.client.get(
            f"/timetable/view?sem_id={self.sem_id}&course_id=1&class_id=1"
        )
        self.assertIn(response.status_code, [200, 302, 303])

    def test_view_timetable_exception(self):
        with patch(
            "routes.timetable_routes.get_db_connection",
            side_effect=Exception("View Error"),
        ):
            response = self.client.get(f"/timetable/view?sem_id={self.sem_id}")
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"View Error", response.data)

    def test_generate_without_sem_id(self):
        response = self.client.post("/timetable/generate", data={})
        self.assertIn(response.status_code, [302, 303])

    def test_generate_with_semester_and_db(self):
        response = self.client.post(
            "/timetable/generate", data={"semester_id": self.sem_id}
        )
        self.assertIn(response.status_code, [302, 303])
        with self.app.app_context():
            grid = generate_timetable_for_semester(self.sem_id)
            expected_count = 0
            assignments = []
            for day, classes in grid.items():
                for cls_id, slots in classes.items():
                    for i, slot in enumerate(slots):
                        if slot is not None and not slot.get("break", False):
                            expected_count += 1
                            assignments.append((day, cls_id, i + 1, slot))
            self.assertEqual(
                expected_count,
                2,
                f"Expected 2 assignments but got {expected_count}. Assignments: {assignments}",
            )
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM timetable WHERE sem_id = %s", (self.sem_id,))
            records = cursor.fetchall()
            db_count = len(records)
            cursor.close()
            conn.close()
            self.assertEqual(
                db_count,
                expected_count,
                f"Database record count ({db_count}) does not match expected ({expected_count})",
            )

    def test_generate_exception_and_rollback(self):
        with patch("routes.timetable_routes.get_db_connection", side_effect=DummyConn):
            response = self.client.post(
                "/timetable/generate", data={"semester_id": self.sem_id}
            )
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Database error", response.data)

    def test_generate_timetable_for_semester_no_semester(self):
        with patch("routes.timetable_routes.get_db_connection") as mock_get_db:
            dummy_conn = DummyConn()
            dummy_cursor = DummyCursor2()
            dummy_conn.cursor = lambda *args, **kwargs: dummy_cursor
            mock_get_db.return_value = dummy_conn
            grid = generate_timetable_for_semester("nonexistent")
            self.assertEqual(grid, {})

    def test_manage_timetable_break_mapping(self):
        # Create a new semester with break data and add a class so that grid is not empty.
        with self.app.app_context():
            sem_data = {
                "sem_name": "Break Mapping Test",
                "start_time": "08:00:00",
                "end_time": "10:00:00",  # 2 slots: 08-09 and 09-10
                "slot_duration": "60",
                "working_days": ["Monday"],
                "break_name[]": ["Morning Break"],
                "break_start[]": ["08:00:00"],
                "break_end[]": ["09:00:00"],
            }
            response = self.client.post(
                "/semesters/create", data=sem_data, follow_redirects=False
            )
            new_sem_id = response.headers.get("Location").split("sem_id=")[-1]
            # Add a class for this new semester.
            class_data = {"class_name[]": ["Break Test Room"], "capacity[]": ["50"]}
            self.client.post(
                f"/semesters/add_classes?sem_id={new_sem_id}", data=class_data
            )
            grid = generate_timetable_for_semester(new_sem_id)
            self.assertIn("Monday", grid)
            monday_dict = grid["Monday"]
            self.assertTrue(len(monday_dict) > 0, "No classes found in Monday's grid")
            class_id = next(iter(monday_dict))
            slots = monday_dict[class_id]
            # Check that the first slot is marked as a break.
            self.assertIsNotNone(slots[0])
            self.assertTrue(
                ("break" in slots[0] and slots[0]["break"] is True)
                or (
                    isinstance(slots[0], dict)
                    and slots[0].get("break_name") == "Morning Break"
                )
            )

    def test_view_timetable_with_filters(self):
        query_params = f"?sem_id={self.sem_id}&course_id=1&class_id=1"
        response = self.client.get("/timetable/view" + query_params)
        self.assertIn(response.status_code, [200, 302, 303])


if __name__ == "__main__":
    unittest.main()
