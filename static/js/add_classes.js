document.addEventListener("DOMContentLoaded", function () {
    const addClassBtn = document.getElementById("add_class_btn");
    const classNameInput = document.getElementById("class_name_input");
    const capacityInput = document.getElementById("capacity_input");
    const classTableBody = document.getElementById("class-table").querySelector("tbody");
    const hiddenInputsContainer = document.getElementById("hidden-inputs");
    let classCounter = 0;

    function addClassRow(className, capacity) {
        classCounter++;
        const row = document.createElement("tr");
        row.setAttribute("data-id", classCounter);
        row.innerHTML = `
            <td>${className}</td>
            <td>${capacity}</td>
            <td><button type="button" class="remove-class btn">Remove</button></td>
        `;
        classTableBody.appendChild(row);
        const hiddenClassInput = document.createElement("input");
        hiddenClassInput.type = "hidden";
        hiddenClassInput.name = "class_name[]";
        hiddenClassInput.value = className;
        hiddenClassInput.setAttribute("data-id", classCounter);
        const hiddenCapacityInput = document.createElement("input");
        hiddenCapacityInput.type = "hidden";
        hiddenCapacityInput.name = "capacity[]";
        hiddenCapacityInput.value = capacity;
        hiddenCapacityInput.setAttribute("data-id", classCounter);
        hiddenInputsContainer.appendChild(hiddenClassInput);
        hiddenInputsContainer.appendChild(hiddenCapacityInput);
    }

    addClassBtn.addEventListener("click", function () {
        const className = classNameInput.value.trim();
        const capacity = capacityInput.value.trim();
        if (className === "" || capacity === "") {
            alert("Please enter both class name and capacity.");
            return;
        }
        addClassRow(className, capacity);
        classNameInput.value = "";
        capacityInput.value = "";
    });

    classTableBody.addEventListener("click", function (event) {
        if (event.target.classList.contains("remove-class")) {
            const row = event.target.closest("tr");
            const id = row.getAttribute("data-id");
            row.remove();
            const hiddenInputs = hiddenInputsContainer.querySelectorAll(`[data-id="${id}"]`);
            hiddenInputs.forEach(input => input.remove());
        }
    });
});