import sys
import os
import unittest
from app import create_app
from database import get_db_connection
from routes.timetable_routes import generate_timetable_for_semester
from config import TestConfig

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestTimetableRoutes(unittest.TestCase):
    def setUp(self):
        # Create an application with the test configuration.
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        # Create a test semester using the exposed endpoint.
        sem_data = {
            "sem_name": "Timetable Test Semester",
            "start_time": "08:00:00",
            "end_time": "12:00:00",  # This yields 4 slots per day: 08-09, 09-10, 10-11, 11-12
            "slot_duration": "60",
            "working_days": ["Monday", "Tuesday"],
        }
        response = self.client.post(
            "/semesters/create", data=sem_data, follow_redirects=False
        )
        location = response.headers.get("Location", "")
        if "sem_id=" in location:
            self.sem_id = location.split("sem_id=")[-1]
        else:
            self.sem_id = "1"  # Fallback

        # Add a class via the endpoint.
        class_data = {"class_name[]": ["Test Room"], "capacity[]": ["50"]}
        self.client.post(
            f"/semesters/add_classes?sem_id={self.sem_id}", data=class_data
        )

        # Add a course via the endpoint.
        # Test Course: 40 students; max_minutes_per_week=120, max_minutes_per_day=60.
        # With slot duration 60, that means at most 2 slots (1 per day) can be assigned.
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
        # Clean up: delete the test semester (cascades to classes, courses, timetable, etc.)
        with self.app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM semesters WHERE sem_id = %s", (self.sem_id,))
            conn.commit()
            cursor.close()
            conn.close()

    def test_view_timetable_without_sem_id(self):
        # Calling view without sem_id should redirect.
        response = self.client.get("/timetable/view")
        self.assertIn(response.status_code, [302, 303])

    def test_view_timetable_with_valid_sem_id(self):
        # Should return the timetable view (even if no timetable entries yet).
        response = self.client.get(f"/timetable/view?sem_id={self.sem_id}")
        self.assertIn(response.status_code, [200, 302, 303])

    def test_generate_without_sem_id(self):
        # Posting to generate without a semester_id should redirect.
        response = self.client.post("/timetable/generate", data={})
        self.assertIn(response.status_code, [302, 303])

    def test_generate_with_semester_and_db(self):
        # Call the generate endpoint.
        response = self.client.post(
            "/timetable/generate", data={"semester_id": self.sem_id}
        )
        self.assertIn(response.status_code, [302, 303])

        # Compute the expected grid using the generation function.
        with self.app.app_context():
            grid = generate_timetable_for_semester(self.sem_id)
            expected_count = 0
            assignments = []  # Record which day/class/slot got an assignment.
            for day, classes in grid.items():
                for cls_id, slots in classes.items():
                    for i, slot in enumerate(slots):
                        if slot is not None and not slot.get("break", False):
                            expected_count += 1
                            assignments.append((day, cls_id, i + 1, slot))

            # For our test course, we expect exactly 2 assignments (one per day: Monday and Tuesday).
            self.assertEqual(
                expected_count,
                2,
                f"Expected 2 assignments but got {expected_count}. Assignments: {assignments}",
            )

            # Query the database to count timetable entries for this semester.
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM timetable WHERE sem_id = %s", (self.sem_id,))
            timetable_records = cursor.fetchall()
            db_count = len(timetable_records)
            cursor.close()
            conn.close()

            self.assertEqual(
                db_count,
                expected_count,
                f"Database timetable record count ({db_count}) does not match expected grid count ({expected_count}).",
            )


if __name__ == "__main__":
    unittest.main()
