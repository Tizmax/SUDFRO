from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
import os
import time
from datetime import datetime
from pdftocsv import generate_csv_from_pdf
from csvtotxt import format_txt_from_csv

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
DEBUG_FOLDER = "debug"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 🟢 Page d'upload
@app.route("/")
def upload_page():
    return render_template("upload.html")

# 🟢 Page liste des fichiers
@app.route("/files")
def list_page():
    return render_template("liste.html")

# 🟢 Route pour téléverser et traiter un fichier (comme "Importer dans l'ERP")
@app.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        return "Aucun fichier trouvé", 400
    
    files = request.files.getlist("files")  

    for file in files:
        if file.filename == "" or not file.filename.endswith(".pdf"):
            return "Fichier invalide", 400
        
        # 🔹 Génération du CSV
        csv_content = generate_csv_from_pdf(file.read(), debug=False)

        # 🔹 Génération du TXT
        txt_filename = file.filename.replace('.pdf', '.txt')
        txt_path = os.path.join(UPLOAD_FOLDER, txt_filename)
        txt_content = format_txt_from_csv(csv_content)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)

    return "Fichier téléversé avec succès", 200

# 🟢 Route pour téléverser et rediriger vers Debug
@app.route("/debug", methods=["POST"])
def debug_file():
    if "files" not in request.files:
        return "Aucun fichier trouvé", 400
    
    files = request.files.getlist("files")  

    if len(files) > 1:
        return 'Un seul fichier est autorisé pour le mode debug', 400
    
    file = files[0]

    if file.filename == "" or not file.filename.endswith(".pdf"):
        return "Fichier invalide", 400
    
    
    generate_csv_from_pdf(file.read(), debug=True)

    return redirect(url_for("debug_result_page"))

# 🟢 Page de résultat du Debug
@app.route("/debug_result")
def debug_result_page():
    csv_file = "debug.csv"
    txt_file = "debug.txt"

    csv_content = ""
    txt_content = ""

    # Charger le contenu du CSV et TXT
    try:
        with open(os.path.join(DEBUG_FOLDER, csv_file), "r", encoding="utf-8") as f:
            csv_content = f.read()
    except:
        csv_content = "Impossible de charger le fichier CSV."

    try:
        with open(os.path.join(DEBUG_FOLDER, txt_file), "r", encoding="utf-8") as f:
            txt_content = f.read()
    except:
        txt_content = "Impossible de charger le fichier TXT."

    return render_template("debug_result.html", csv_content=csv_content, txt_content=txt_content, csv_filename=csv_file)

@app.route("/update_csv", methods=["POST"])
def update_csv():
    data = request.get_json()
    filename = data.get("filename")
    content = data.get("content")

    if not filename or not content:
        return jsonify({"error": "Données manquantes"}), 400

    file_path = os.path.join(DEBUG_FOLDER, filename)
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"message": "Fichier mis à jour avec succès"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
