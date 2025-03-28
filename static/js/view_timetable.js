// Toggle dropdown visibility based on selection
document.querySelectorAll('input[name="viewType"]').forEach(function (elem) {
    elem.addEventListener("change", function (event) {
        if (event.target.value === "class") {
            document.getElementById('class-dropdown').style.display = 'block';
            document.getElementById('course-dropdown').style.display = 'none';
        } else {
            document.getElementById('class-dropdown').style.display = 'none';
            document.getElementById('course-dropdown').style.display = 'block';
        }
    });
});

function fetchTimetable() {
    let viewType = document.querySelector('input[name="viewType"]:checked').value;
    let semId = document.getElementById('semesterId').value;

    if (!semId) {
        alert("Semester ID is missing. Please select a semester first.");
        window.location.href = "{{ url_for('semester.manage_semesters') }}";
        return;
    }

    let url = `/timetable/view?sem_id=${semId}`;

    if (viewType === "class") {
        let classId = document.getElementById('classSelect').value;
        if (!classId) {
            alert("Please select a room.");
            return;
        }
        url += `&class_id=${classId}`;
    } else {
        let courseId = document.getElementById('courseSelect').value;
        if (!courseId) {
            alert("Please select a course.");
            return;
        }
        url += `&course_id=${courseId}`;
    }

    window.location.href = url;
}

function downloadTimetable() {
    alert("Download functionality not yet implemented.");
}

// Initialize correct dropdown visibility on page load
window.addEventListener('DOMContentLoaded', function () {
    let courseId = new URLSearchParams(window.location.search).get('course_id');
    if (courseId) {
        document.querySelector('input[value="course"]').checked = true;
        document.getElementById('class-dropdown').style.display = 'none';
        document.getElementById('course-dropdown').style.display = 'block';
    }
});