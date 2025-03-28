document.addEventListener("DOMContentLoaded", function () {
    const addBreakBtn = document.getElementById("add_break_btn");
    const breakNameInput = document.getElementById("break_name_input");
    const breakStartInput = document.getElementById("break_start_input");
    const breakEndInput = document.getElementById("break_end_input");
    const breakTableBody = document.getElementById("break-table").querySelector("tbody");
    const hiddenBreakInputsContainer = document.getElementById("hidden-break-inputs");
    let breakCounter = 0;
    function addBreakRow(name, start, end) {
        breakCounter++;
        const row = document.createElement("tr");
        row.setAttribute("data-id", breakCounter);
        row.innerHTML = `
        <td>${name}</td>
        <td>${start}</td>
        <td>${end}</td>
        <td><button type="button" class="remove-break btn">Remove</button></td>
      `;
        breakTableBody.appendChild(row);
        const hiddenName = document.createElement("input");
        hiddenName.type = "hidden";
        hiddenName.name = "break_name[]";
        hiddenName.value = name;
        hiddenName.setAttribute("data-id", breakCounter);
        const hiddenStart = document.createElement("input");
        hiddenStart.type = "hidden";
        hiddenStart.name = "break_start[]";
        hiddenStart.value = start;
        hiddenStart.setAttribute("data-id", breakCounter);
        const hiddenEnd = document.createElement("input");
        hiddenEnd.type = "hidden";
        hiddenEnd.name = "break_end[]";
        hiddenEnd.value = end;
        hiddenEnd.setAttribute("data-id", breakCounter);
        hiddenBreakInputsContainer.append(hiddenName, hiddenStart, hiddenEnd);
    }
    addBreakBtn.addEventListener("click", function () {
        const name = breakNameInput.value.trim();
        const start = breakStartInput.value;
        const end = breakEndInput.value;
        if (!name || !start || !end) {
            alert("Fill all break fields.");
            return;
        }
        addBreakRow(name, start, end);
        breakNameInput.value = "";
        breakStartInput.value = "";
        breakEndInput.value = "";
    });
    document.getElementById("break-table").addEventListener("click", function (e) {
        if (e.target.classList.contains("remove-break")) {
            const row = e.target.closest("tr");
            const id = row.getAttribute("data-id");
            row.remove();
            document.querySelectorAll(`[data-id="${id}"]`).forEach(el => el.remove());
        }
    });
});