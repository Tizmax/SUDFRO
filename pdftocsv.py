from io import BytesIO
import os
from mistralai import Mistral
import pdfplumber

DEBUG_FOLDER = "debug"
os.makedirs(DEBUG_FOLDER, exist_ok=True)

with open('MISTRAL_API_KEY.txt', 'r') as file:
    api_key = file.read().strip()

client = Mistral(api_key)

def extract_text_from_pdf(byte):

    # Ouverture du PDF
    pdf = pdfplumber.open(BytesIO(byte))

    # Extraction du texte
    text = ""
    for page in pdf.pages:
        text += page.extract_text()

    return text

def generate_csv_from_text(text):
    # Envoie de la requête à l'API
    chat_response = client.agents.complete(
        agent_id="ag:3fdcd4c2:20250306:sudfro:01656dd4",
        messages = [
            {
                "role": "user",
                "content": text,
            },
        ]
    )

    # Récupération de la réponse de l'API
    response = chat_response.choices[0].message.content

    return response

def generate_csv_from_pdf(byte, debug=False):
    text = extract_text_from_pdf(byte)
    if debug:
        path = os.path.join(DEBUG_FOLDER, "debug.txt")
        with open(path, 'w', encoding='utf-8') as text_file:
            text_file.write(text)
    csv = generate_csv_from_text(text)
    if debug:
        path = os.path.join(DEBUG_FOLDER, "debug.csv")
        with open(path, 'w', encoding='utf-8') as csv_file:
            csv_file.write(csv)
    return csv
