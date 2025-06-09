import csv
import io

GLN = "1234567890123"
SPACE = ' '  # Caractère de remplissage
NB_COLONNES = 8  # Nombre de colonnes au total

def format_txt_from_csv(csv_content):
    """ Convertit une chaîne CSV en une chaîne TXT formatée """

    csvfile = io.StringIO(csv_content)
    reader = csv.reader(csvfile)
    rows = list(reader)
    formatted_lines = []

    ## Récupération des données de l'en-tête
    numBL = rows[1][2]  
    numCommande = rows[1][3]  
    dateBL = rows[1][4]

    ## Formatage des données de l'en-tête
    numBL = fill(numBL, SPACE, 10)
    dateBL = DDMMYYYY_to_YYYYMMDD(dateBL)

    ## Création de l'en-tête
    formatted_lines.append(f"HINT{SPACE * 53}{GLN}")
    formatted_lines.append("HGEN")
    formatted_lines.append(f"HPTYDP{SPACE}{GLN}")
    formatted_lines.append(f"HREFON{SPACE}{numCommande}")
    formatted_lines.append(f"HREFDQ{SPACE}{numBL}{SPACE * 31}{dateBL}")
    formatted_lines.append("HDELLIV")

    ## Itération sur les articles
    for i in range(3, len(rows)):
        # Remplissage des colonnes manquantes
        rows[i].extend([""] * (NB_COLONNES - len(rows[i]))) 

        refFournisseur = rows[i][0] 
        dateLimite = rows[i][2]
        NbColis = rows[i][3]
        poids = rows[i][4]
        quantite = rows[i][5]
        numLot = rows[i][6]

        refFournisseur = fill(refFournisseur, SPACE, 20)
        dateLimite = DDMMYYYY_to_YYYYMMDD(dateLimite)
        NbColis = fill(NbColis.split('.')[0], '0', 8, left=True)
        if '.' in poids:
            p1, p2 = poids.split('.')
        else:
            p1, p2 = poids, '0'
        poids = fill(p1, '0', 4, left=True) + '.' + fill(p2, '0', 3)
        if quantite == '' or float(quantite) == 0.0:
            ## Si la quantité est vide ou nulle, on la remplace par le poids
            quantite =  fill(p1, '0', 11, left=True) + '.' + fill(p2, '0', 3)
            # Et l'unite devient KGM
            unite = 'KGM'
        else:
            ## Sinon on garde l'ancienne quantité (en PCE)
            if '.' in quantite:
                q1, q2 = quantite.split('.')
            else:
                q1, q2 = quantite, '0'
            quantite =  fill(q1, '0', 11, left=True) + '.' + fill(q2, '0', 3)
            unite = 'PCE'
        numLot = fill(numLot, SPACE, 20)

        formatted_lines.append(f"DPIDBX{SPACE * 39}CT{SPACE*2}{NbColis}{poids}{'0'*8}{numLot}{SPACE * 26}{dateLimite}")
        formatted_lines.append(f"DART000001{SPACE*3}{refFournisseur}{SPACE * 56}{quantite}{SPACE*3}{unite}")
        formatted_lines.append("")

    return "\n".join(formatted_lines) 


def DDMMYYYY_to_YYYYMMDD(date):
    return date[6:] + date[3:5] + date[:2]

def fill(string, filler, length, left=False):
    return string + filler * (length-len(string)) if not left else filler * (length-len(string)) + string


