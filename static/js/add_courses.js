document.addEventListener("DOMContentLoaded", function () {
    const addCourseBtn = document.getElementById("add_course_btn");
    const courseNameInput = document.getElementById("course_name_input");
    const courseAbbrInput = document.getElementById("course_abbr_input");
    const numStudentsInput = document.getElementById("num_students_input");
    const maxMinutesWeekInput = document.getElementById("max_minutes_week_input");
    const maxMinutesDayInput = document.getElementById("max_minutes_day_input");
    const minMinutesDayInput = document.getElementById("min_minutes_day_input");
    const courseTableBody = document.getElementById("course-table").querySelector("tbody");
    const hiddenInputsContainer = document.getElementById("hidden-inputs");
    let courseCounter = 0;

    function addCourseRow(name, abbr, students, maxWeek, maxDay, minDay) {
        courseCounter++;
        const row = document.createElement("tr");
        row.setAttribute("data-id", courseCounter);
        row.innerHTML = `
        <td>${name}</td>
        <td>${abbr}</td>
        <td>${students}</td>
        <td>${maxWeek}</td>
        <td>${maxDay}</td>
        <td>${minDay}</td>
        <td><button type="button" class="remove-course btn">Remove</button></td>
      `;
        courseTableBody.appendChild(row);
        const createHidden = (n, v) => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = n;
            input.value = v;
            input.setAttribute("data-id", courseCounter);
            return input;
        };
        hiddenInputsContainer.append(
            createHidden("course_name[]", name),
            createHidden("course_abbr[]", abbr),
            createHidden("num_students[]", students),
            createHidden("max_minutes_per_week[]", maxWeek),
            createHidden("max_minutes_per_day[]", maxDay),
            createHidden("min_minutes_per_day[]", minDay)
        );
    }

    addCourseBtn.addEventListener("click", function () {
        const name = courseNameInput.value.trim();
        const abbr = courseAbbrInput.value.trim();
        const students = numStudentsInput.value.trim();
        const maxWeek = maxMinutesWeekInput.value.trim();
        const maxDay = maxMinutesDayInput.value.trim();
        const minDay = minMinutesDayInput.value.trim();
        if (!name || !abbr || !students || !maxWeek || !maxDay || !minDay) {
            alert("Please fill all fields.");
            return;
        }
        addCourseRow(name, abbr, students, maxWeek, maxDay, minDay);
        courseNameInput.value = "";
        courseAbbrInput.value = "";
        numStudentsInput.value = "";
        maxMinutesWeekInput.value = "";
        maxMinutesDayInput.value = "";
        minMinutesDayInput.value = "";
    });

    document.getElementById("course-table").addEventListener("click", function (e) {
        if (e.target.classList.contains("remove-course")) {
            const row = e.target.closest("tr");
            const id = row.getAttribute("data-id");
            row.remove();
            document.querySelectorAll(`[data-id="${id}"]`).forEach(el => el.remove());
        }
    });
});