import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
def lire_ticket(cle_ticket):
    """Récupère les informations d'un ticket Jira via son identifiant (ex: SCRUM-1)."""
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{cle_ticket}"

    reponse = requests.get(
        url,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Accept": "application/json"}
    )

    if reponse.status_code != 200:
        raise ValueError(f"Impossible de lire le ticket {cle_ticket}. Code : {reponse.status_code}")

    donnees = reponse.json()

    titre = donnees["fields"]["summary"]
    description_brute = donnees["fields"].get("description")
    type_ticket = donnees["fields"]["issuetype"]["name"]
    statut = donnees["fields"]["status"]["name"]

    description = extraire_texte_description(description_brute)

    return {
        "cle": cle_ticket,
        "titre": titre,
        "description": description,
        "type": type_ticket,
        "statut": statut,
    }
def extraire_texte_description(description_brute):
    """Convertit le format JSON structuré de la description Jira en texte brut simple."""
    if not description_brute:
        return "(Aucune description fournie)"

    morceaux_texte = []

    def parcourir(noeud):
        if isinstance(noeud, dict):
            if noeud.get("type") == "text":
                morceaux_texte.append(noeud.get("text", ""))
            for enfant in noeud.get("content", []):
                parcourir(enfant)
        elif isinstance(noeud, list):
            for element in noeud:
                parcourir(element)

    parcourir(description_brute)
    return " ".join(morceaux_texte)