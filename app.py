from flask import Flask, request, jsonify, render_template, redirect, url_for
import os
import time
import threading
import uuid
import json
from pdftocsv import generate_csv_from_pdf
from csvtotxt import format_txt_from_csv

app = Flask(__name__)
history_lock = threading.Lock() # Verrou pour la gestion de l'historique
agents_lock = threading.Lock() # Verrou pour la gestion de l'historique

UPLOAD_FOLDER = "uploads"
DEBUG_FOLDER = "debug"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DEBUG_FOLDER, exist_ok=True)
HISTORY_FILE = "history.json"
AGENTS_FILE = "agents.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)


@app.route("/get_history", methods=["GET"])
def get_history():
    return jsonify(load_history())

@app.route("/clear_history", methods=["POST"])
def clear_history():
    
    with history_lock:  # 🔒 Bloque l'accès à l'historique pendant l'écriture
        history = load_history()

        # Garde seulement les jobs qui ne sont PAS "done"
        history = [entry for entry in history if entry["status"] == "processing"]

        save_history(history)  # 📝 Sauvegarde le nouveau JSON

    return jsonify({"success": True})


def add_to_history(job_id, filename, status="processing"):
    """Ajoute un job à l'historique en évitant les problèmes de concurrence"""
    with history_lock:  # 🔒 Bloque l'accès à l'historique pendant l'écriture

        history = load_history()  # Charge l'historique actuel

        # Vérifie si le job est déjà présent
        for entry in history:
            if entry["job_id"] == job_id:
                if entry["status"] in ["done", "processing"]: 
                    return False # Ne rien faire si déjà présent 
                else : # Si il y a eu une erreur on permet de recommencer
                    entry["status"] = status
                    return True

        history.append({"job_id": job_id, "filename": filename, "status": status})  # Ajoute le job
        save_history(history)  # Sauvegarde proprement
        return True

def update_history_status(job_id, new_status):
    """Modifie le statut d'un job spécifique dans l'historique"""
    with history_lock:  # 🔒 Sécurise l'accès au fichier JSON
        history = load_history()  # Charge l'historique
        for entry in history:
            if entry["job_id"] == job_id:
                entry["status"] = new_status  # 📝 Met à jour le statut
                break
        save_history(history)  # Sauvegarde proprement


def load_agents():
    """Charge les agents depuis le fichier JSON (format dictionnaire)."""
    with agents_lock:
        try:
            if os.path.exists(AGENTS_FILE):
                with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
                    # Charger directement le dictionnaire
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    else:
                        print(f"Warning: {AGENTS_FILE} ne contient pas un objet JSON valide. Retour d'un dict vide.")
                        # Optionnel : essayer de corriger ou écraser avec un dict vide
                        # save_agents_data({}) # Attention: écrase les données existantes si invalides
                        return {}
            else:
                # Si le fichier n'existe pas, créer un fichier avec un objet vide
                with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                return {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erreur lors de la lecture de {AGENTS_FILE}: {e}")
            return {} # Retourner un dictionnaire vide en cas d'erreur

def save_agents_data(agents_dict):
    """Sauvegarde le dictionnaire des agents dans le fichier JSON."""
    if not isinstance(agents_dict, dict):
        print("Erreur: save_agents_data attend un dictionnaire.")
        return False
    with agents_lock:
        try:
            with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
                # trier les clés du dictionnaire avant de sauvegarder
                agents_dict = dict(sorted(agents_dict.items()))
                json.dump(agents_dict, f, indent=2, ensure_ascii=False) # Sauvegarder le dictionnaire
            return True
        except IOError as e:
            print(f"Erreur lors de l'écriture de {AGENTS_FILE}: {e}")
            return False
    
def agentid_by_filename(filename):
    """Trouve un agent par son nom dans le fichier JSON."""
    with agents_lock:
        try:
            with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for name,id in data.items():
                    if name in filename:
                        return id
                return data.get("Default")  # Return default agent ID if no specific match found
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erreur lors de la lecture de {AGENTS_FILE}: {e}")
    return None

# ➡️ Page principale
@app.route("/")
def upload_page():
    return render_template("upload.html")


def process_file(task_id, filename, file_content, debug=False):
    """ Fonction exécutée en arrière-plan pour traiter le fichier PDF """
    
    add = add_to_history(task_id, filename)  # ⏳ Marque comme en cours
    if not add:
        return
    try:
        # Choix du meilleur agent
        agent_id = agentid_by_filename(filename)

        print(f"Agent ID trouvé pour {filename}: {agent_id}")

        # Conversion PDF → CSV
        csv_content = generate_csv_from_pdf(file_content, agent_id, debug)

        if not debug:
            # Conversion CSV → TXT
            txt_content = format_txt_from_csv(csv_content)

            # Sauvegarde du fichier TXT
            txt_filename = filename.replace(".pdf", ".txt").replace(".PDF", ".txt")
            txt_path = os.path.join(UPLOAD_FOLDER, txt_filename)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(txt_content)

        update_history_status(task_id, 'done')  # ✅ Marque comme terminé

    except Exception as e:
        update_history_status(task_id, 'error') # ✅ Marque comme terminé
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
        
        task_id = str(uuid.uuid4())
        threading.Thread(target=process_file, args=(task_id, filename, file_content)).start()
        time.sleep(3) # 🚨 Nécessaire pour ne pas surcharger l'API de requêtes

    
    return jsonify({"message": "Fichiers reçus, traitement en cours", "files": file_names}), 200



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
    
    filename = file.filename.replace(' ', '_')
    file_content = file.read()

    task_id = str(uuid.uuid4())
    threading.Thread(target=process_file, args=(task_id, filename, file_content, True)).start()

    return redirect(url_for("debug_result_page", task_id=task_id))

# ➡️ Page de résultat du Debug
@app.route("/debug_result")
def debug_result_page():
    task_id = request.args.get('task_id')
    if not task_id:
        return "ID de tâche manquant", 400
        
    return render_template("debug_result.html", task_id=task_id)

# ➡️ API pour vérifier le statut d'une tâche de debug
@app.route("/debug_status/<task_id>")
def debug_status(task_id):
    """Vérifie le statut d'une tâche de debug spécifique"""
    with history_lock:
        history = load_history()
        
        # Chercher le job par son ID
        for entry in history:
            if entry["job_id"] == task_id:
                if entry["status"] == "done":
                    # Lire le contenu du fichier CSV de debug
                    try:
                        csv_path = os.path.join(DEBUG_FOLDER, "debug.csv")
                        with open(csv_path, "r", encoding="utf-8") as f:
                            csv_content = f.read()
                        return jsonify({
                            "status": "finished",
                            "result": csv_content
                        })
                    except Exception as e:
                        return jsonify({
                            "status": "failed",
                            "result": f"Erreur lors de la lecture du fichier: {str(e)}"
                        })
                elif entry["status"] == "error":
                    return jsonify({
                        "status": "failed", 
                        "result": "Erreur lors du traitement du fichier"
                    })
                else:  # processing
                    return jsonify({
                        "status": "processing",
                        "result": "Traitement en cours..."
                    })
        
        # Si le job n'est pas trouvé
        return jsonify({
            "status": "failed",
            "result": "Tâche introuvable"
        })

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


@app.route('/agents')
def agents():
    """Affiche la page de gestion des agents."""
    agents_list = load_agents()
    return render_template('agents.html', agents=agents_list)

@app.route('/save_agents', methods=['POST'])
def save_agents_route():
    """Reçoit les données des agents depuis le client et les sauvegarde."""
    try:
        agents_data = request.get_json()
        if not isinstance(agents_data, dict):
             raise ValueError("Les données reçues ne sont pas un dictionnaire.")
        # Ajouter une validation plus poussée si nécessaire (champs requis, format ID...)

        if save_agents_data(agents_data):
            return jsonify({"status": "ok", "message": "Agents sauvegardés avec succès."})
        else:
            return jsonify({"status": "error", "message": "Erreur lors de la sauvegarde des agents."}), 500
    except Exception as e:
        print(f"Erreur dans /save_agents: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
