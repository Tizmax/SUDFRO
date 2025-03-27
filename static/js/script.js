/// upload.html
function handleFiles(files) {
    selectedFiles = Array.from(files).filter(file => file.type === "application/pdf");

    fileList.innerHTML = "";
    selectedFiles.forEach(file => {
        let li = document.createElement("li");
        li.textContent = file.name;
        fileList.appendChild(li);
    });

    if (selectedFiles.length === 0) {
        alert("Veuillez sélectionner uniquement des fichiers PDF.");
    }
}

function uploadFiles() {
    if (selectedFiles.length === 0) {
        alert("Aucun fichier sélectionné.");
        return;
    }

    let formData = new FormData();
    selectedFiles.forEach(file => formData.append("files", file));

    let uploadedFiles = [];

    // Affichage initial des fichiers avec icône ⏳
    document.getElementById("fileList").innerHTML = selectedFiles
        .map((file, index) => `<li>${file.name} <span id="file-${file.name}" class="file-status pending">⏳</span></li>`)
        .join("");

    fetch("/upload", { method: "POST", body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.files) {
                uploadedFiles = data.files; 
                checkProcessingStatus(uploadedFiles);  
            }
        })
        .catch(() => alert("Erreur lors du téléversement."));
}

// Vérification dynamique des statuts
function checkProcessingStatus(filenames) {
    let interval = setInterval(() => {
    if (filenames.length === 0) {
        clearInterval(interval);
        return;
    }

    fetch("/check_status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filenames })
    })
    .then(response => response.json())
    .then(statusData => {
        let stillProcessing = [];

        filenames.forEach(filename => {
            let statusElement = document.getElementById(`file-${filename}`);
            if (!statusElement) return; // Ignore si l'élément n'existe pas

            if (statusData[filename] === "done") {
                statusElement.textContent = "✅";
                statusElement.classList.remove("pending");
                statusElement.classList.add("done");
            } else if (statusData[filename] === "error") {
                statusElement.textContent = "❌";
                statusElement.classList.remove("pending");
                statusElement.classList.add("error");
            } else {
                stillProcessing.push(filename); // ✅ On garde les fichiers qui sont encore en traitement
            }
        });

        if (stillProcessing.length === 0) {
            clearInterval(interval);
        } else {
            filenames = stillProcessing; 
        }
    });
    }, 2000); // Vérification toutes les 2 secondes
}

async function debugFiles() {
    await submitForm("/debug");
}

async function submitForm(action) {
    if (selectedFiles.length === 0) {
        alert("Aucun fichier sélectionné.");
        return;
    }

    let formData = new FormData();
    selectedFiles.forEach(file => formData.append("files", file));

    let response = await fetch(action, {
        method: "POST",
        body: formData
    });

    if (response.redirected) {
        window.location.href = response.url;  // 🔄 Redirection pour le Debug
    } else if (response.ok) {
        alert("Fichiers téléversés avec succès !");
        fileList.innerHTML = "";
        selectedFiles = [];
    } else {
        alert("Erreur lors du traitement !");
    }
}

/// debug_result.html

// Génère le tableau issu du CSV avec les données modifiables
function generateTable(csv) {
    const tableBody = document.getElementById("tableBody");
    const headerRow = document.getElementById("headerRow");

    tableBody.innerHTML = "";
    headerRow.innerHTML = "";

    let rows = csv.split("\n").map(row => row.split(","));

    // Création de la 1ère ligne comme en-tête
    rows[0].forEach(col => {
        let th = document.createElement("th");
        th.textContent = col;
        headerRow.appendChild(th);
    });

    // Création des autres lignes
    rows.slice(1).forEach((row, rowIndex) => {
        let tr = document.createElement("tr");

        row.forEach(cell => {
            let td = document.createElement(rowIndex === 1 ? "th" : "td"); // 3ème ligne = <th> au lieu de <td>
            td.textContent = cell;

            if (rowIndex === 1) {
                td.style.fontWeight = "bold"; // Mise en gras pour la 3ème ligne (index 2 du CSV)
            } else {
                td.contentEditable = "true"; // Toutes les autres cellules restent modifiables
            }

            tr.appendChild(td);
        });

        tableBody.appendChild(tr);
    });
}

// Enregistre les modifications du tableau dans le CSV
function saveCsv() {
    let newCsvData = [];

    let headerCells = document.querySelectorAll("#headerRow th");
    let headerRow = Array.from(headerCells).map(cell => cell.textContent);
    newCsvData.push(headerRow.join(",")); 

    const rows = document.querySelectorAll("#tableBody tr");

    rows.forEach(row => {
    let rowData = [];
    row.querySelectorAll("td, th").forEach(cell => { 
        rowData.push(cell.textContent);
    });
    newCsvData.push(rowData.join(","));
    });

    fetch("/update_csv", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        filename: "{{ csv_filename }}",  // ✅ Vérifie que cette valeur est bien transmise par le backend
        content: newCsvData.join("\n")
    })
    })
    .then(response => response.json())
    .then(data => {
    if (data.success) {
        window.location.href = "/debug_final"; // ✅ Redirection sans paramètre
    } else {
        alert("Erreur lors de l'enregistrement du CSV");
    }
    });
}

/// debug_final.html
function copyToClipboard(elementId) {
    let textarea = document.getElementById(elementId);
    textarea.select();
    document.execCommand("copy");
    alert("Copié dans le presse-papier !");
}