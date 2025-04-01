from flask import Flask, request, jsonify, render_template, redirect, url_for
import os
import time
import threading
from pdftocsv import generate_csv_from_pdf
from csvtotxt import format_txt_from_csv

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
DEBUG_FOLDER = "debug"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DEBUG_FOLDER, exist_ok=True)

# ➡️ Page principale
@app.route("/")
def upload_page():
    return render_template("upload.html")


processing_status = {}  # Stocke l'état des fichiers traités

def process_file(filename, file_content):
    """ Fonction exécutée en arrière-plan pour traiter le fichier PDF """
    global processing_status
    processing_status[filename] = "processing"  # ⏳ Marque comme en cours
    try:
        # Conversion PDF → CSV
        csv_content = generate_csv_from_pdf(file_content, debug=True)

        # Conversion CSV → TXT
        txt_content = format_txt_from_csv(csv_content)

        # Sauvegarde du fichier TXT
        txt_filename = filename.replace(".pdf", ".txt").replace(".PDF", ".txt")
        txt_path = os.path.join(UPLOAD_FOLDER, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        processing_status[filename] = "done"  # ✅ Marque comme terminé

    except Exception as e:
        processing_status[filename] = "error"  # ❌ Marque comme erreur
        print(f"Error processing file {filename}: {e}")
        


# 🔄️ Lance le traitement des fichiers
@app.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        return jsonify({"error": "Aucun fichier trouvé"}), 400

    files = request.files.getlist("files")
    file_names = []

    for file in files:
        if file.filename == "" or not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Fichier invalide"}), 400

        filename = file.filename.replace(' ', '_')

        file_names.append(filename)
        file_content = file.read() 

        # Lancement du traitement en arrière-plan (Thread)
        threading.Thread(target=process_file, args=(filename, file_content)).start()
        time.sleep(3) # 🚨 Nécessaire pour ne pas surcharger l'API de requêtes

    
    return jsonify({"message": "Fichiers reçus, traitement en cours", "files": file_names}), 200

# ⬅️ Requête sur le statut de traitement des fichiers
@app.route("/check_status", methods=["POST"])   
def check_status():
    data = request.get_json()
    filenames = data.get("filenames", [])

    status = {filename: processing_status.get(filename, "unknown") for filename in filenames}
    return jsonify(status)


# 🔄️ Traite partiellement le fichier sélectionné et renvoie sur la page de débug
@app.route("/debug", methods=["POST"])
def debug_file():
    if "files" not in request.files:
        return "Aucun fichier trouvé", 400
    
    files = request.files.getlist("files")  

    if len(files) > 1:
        return 'Un seul fichier est autorisé pour le mode debug', 400
    
    file = files[0]

    if file.filename == "" or not file.filename.lower().endswith(".pdf"):
        return "Fichier invalide", 400
    
    
    generate_csv_from_pdf(file.read(), debug=True)

    return redirect(url_for("debug_result_page"))

# ➡️ Page de résultat du Debug
@app.route("/debug_result")
def debug_result_page():
    csv_file = "debug.csv"

    csv_content = ""

    # Charger le contenu du CSV et TXT
    try:
        with open(os.path.join(DEBUG_FOLDER, csv_file), "r", encoding="utf-8") as f:
            csv_content = f.read()
    except:
        csv_content = "Impossible de charger le fichier CSV."

    return render_template("debug_result.html", csv_content=csv_content, csv_filename=csv_file)

# 🔄️ Applique les modifications au fichier CSV
@app.route("/update_csv", methods=["POST"])
def update_csv():
    data = request.get_json()
    content = data.get("content")

    filename = "debug.csv"
    file_path = os.path.join(DEBUG_FOLDER, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return jsonify({"success": True})
    
@app.route('/debug_final')
def debug_final():
    filename = "debug.csv"  

    csv_path = os.path.join(DEBUG_FOLDER, filename)
    txt_path = csv_path.replace(".csv", ".txt")

    csv_content = open(csv_path, "r", encoding="utf-8").read() if os.path.exists(csv_path) else "Fichier CSV introuvable"
    txt_content = open(txt_path, "r", encoding="utf-8").read() if os.path.exists(txt_path) else "Fichier TXT introuvable"

    return render_template('debug_final.html', csv_content=csv_content, txt_content=txt_content)


if __name__ == "__main__":
    app.run(debug=True)
