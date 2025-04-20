from io import BytesIO, StringIO
import os
import csv
from mistralai import Mistral
import pdfplumber

DEBUG_FOLDER = "debug"
os.makedirs(DEBUG_FOLDER, exist_ok=True)

with open('MISTRAL_API_KEY.txt', 'r') as file:
    api_key = file.read().strip()

client = Mistral(api_key)

HEADER_LINE_1 = ["Nom du fournisseur", "Numéro Siret Fournisseur", "Numéro du BL fournisseur", "Référence de commande", "Date de livraison"] # 5 colonnes
HEADER_LINE_3 = ["Référence fournisseur","Libellé du produit","DLC / DLUO / DLM","Nombre de colis","Poids net","Nombre de pièce","Unité","Numéro de Lot"] # 8 colonnes

def extract_text_from_pdf(byte):

    # Ouverture du PDF
    pdf = pdfplumber.open(BytesIO(byte))

    # Extraction du texte
    text = ""
    for page in pdf.pages:
        text += page.extract_text()

    return text

def generate_csv_from_text(text, agent):
    # Envoie de la requête à l'API
    chat_response = client.agents.complete(
        agent_id=agent,
        messages = [
            {
                "role": "user",
                "content": text,
            },
        ]
    )
    # Récupération de la réponse
    content = chat_response.choices[0].message.content

    # ✅ Gère les deux cas : texte simple OU liste de chunks
    if isinstance(content, list):
        # On concatène tous les morceaux de type "text"
        response = "".join(chunk.get("text", "") for chunk in content if chunk.get("type") == "text")
    else:
        response = content


    return response

def format_csv(raw_csv_string: str) -> str:
    """
    Force la structure du CSV retourné par l'IA.
    - Impose les 3 premières lignes (en-têtes fixes).
    - S'assure que les lignes de données (à partir de la 4ème) ont 8 colonnes.
    - Garantit un minimum de 3 lignes dans le résultat final.
    """
    processed_rows = [
        HEADER_LINE_1,
        [""] * len(HEADER_LINE_1), 
        HEADER_LINE_3
    ]
    
    try:
        # Utiliser io.StringIO pour lire la chaîne comme un fichier
        csvfile = StringIO(raw_csv_string)
        reader = csv.reader(csvfile)
        rows = list(reader)

        if len(rows) > 1 :
            target_cols = len(HEADER_LINE_1) # Nombre de colonnes de la 1ère ligne d'en-tête
            row = rows[1] # 2ème ligne
            num_cols = len(row) # Nombre de colonnes de la 2ème ligne 
            if target_cols > num_cols:
                row += [""] * (target_cols - num_cols)
                print(f"Warning: Ligne 1 complétée (avait {num_cols} colonnes): {row}")
            elif target_cols < num_cols:
                row = row[:target_cols]
                print(f"Warning: Ligne 1 tronquée (avait {num_cols} colonnes): {row}")
            processed_rows[1] = row # Remplacer la ligne vide par la 2ème ligne de l'IA

        for row in rows[3:]: # Traiter les lignes de données à partir de la 3ème ligne de l'IA
            if not any(field.strip() for field in row): # Ignorer lignes complètement vides
                 continue
                 
            num_cols = len(row)
            target_cols = len(HEADER_LINE_3) # Nombre de colonnes de la 1ère ligne d'en-tête

            if num_cols == target_cols:
                processed_rows.append(row)
            elif num_cols > target_cols:
                # Tronquer la ligne si elle a trop de colonnes
                processed_rows.append(row[:target_cols])
                print(f"Warning: Ligne IA tronquée (avait {num_cols} colonnes): {row}")
            else: # num_cols < target_cols
                # Compléter la ligne avec des chaînes vides si pas assez de colonnes
                processed_rows.append(row + [""] * (target_cols - num_cols))
                print(f"Warning: Ligne IA complétée (avait {num_cols} colonnes): {row}")

    except Exception as e:
        # En cas d'erreur de parsing CSV (si l'IA renvoie n'importe quoi)
        print(f"Erreur lors du parsing du CSV de l'IA: {e}. Utilisation des en-têtes par défaut uniquement.")
        # 'processed_rows' contient déjà les 3 lignes d'en-tête par défaut.

    # Reconvertir la liste de listes en chaîne CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerows(processed_rows)
    
    return output.getvalue()



def generate_csv_from_pdf(byte, agent_id, debug=False):
    text = extract_text_from_pdf(byte)
    if debug:
        path = os.path.join(DEBUG_FOLDER, "debug.txt")
        with open(path, 'w', encoding='utf-8') as text_file:
            text_file.write(text)
    csv = generate_csv_from_text(text, agent_id)
    formated_csv = format_csv(csv)
    if debug:
        path = os.path.join(DEBUG_FOLDER, "debug.csv")
        with open(path, 'w', encoding='utf-8', newline='') as csv_file:
            csv_file.write(formated_csv)
    return formated_csv
