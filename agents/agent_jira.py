import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()
AGENT1_API_KEY = os.getenv("AGENT1_API_KEY")
AGENT2_API_KEY = os.getenv("AGENT2_API_KEY")
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
def analyser_intention(ticket):
    """Détermine l'intention du ticket (corriger un bug, générer du code, ou analyse générale)."""
    texte_complet = (ticket["titre"] + " " + ticket["description"]).lower()

    mots_cles_bug = ["bug", "erreur", "corriger", "ne fonctionne pas", "problème", "fix"]
    mots_cles_generation = ["créer", "générer", "ajouter une fonctionnalité", "implémenter", "nouveau"]

    if ticket["type"].lower() == "bug" or any(mot in texte_complet for mot in mots_cles_bug):
        return "correction_bug"
    elif any(mot in texte_complet for mot in mots_cles_generation):
        return "generation_code"
    else:
        return "analyse_generale"


def construire_prompt(ticket):
    """Construit un prompt ingénieur senior adapté à l'intention détectée dans le ticket."""
    intention = analyser_intention(ticket)
    # lezem llm yraja3 prompt "propmtToDevolopAgent" this will be sent to the gemimi agent
    # donc prompt hedhi lezemha tetbaddel bech trajja3 "propmtToDevolopAgent"  
    en_tete = f"""Tu es un expert en ingénierie de prompts.
Analyse ce ticket Jira et génère un prompt professionnel et précis 
qui sera envoyé à un agent IA pour accomplir la tâche décrite.

Le prompt généré doit :
- Être directement exécutable par un agent IA
- Contenir toutes les informations nécessaires du ticket
- Être adapté exactement au type de tâche demandée


Ticket : {ticket['cle']}
Titre : {ticket['titre']}
Type : {ticket['type']}
Statut : {ticket['statut']}
Description : {ticket['description']}
"""

    if intention == "correction_bug":
        instruction = """Analyse ce ticket en tant qu'ingénieur senior et réponds avec la structure suivante :

Diagnostic :
Explique la cause probable du bug de façon précise et technique.

Solution proposée :
Décris la correction à apporter, avec un exemple de code si pertinent.

Points d'attention :
Mentionne les effets de bord potentiels ou les tests à effectuer.

Critères de validation :
Liste les conditions qui confirment que le bug est résolu."""

    elif intention == "generation_code":
        instruction = """Analyse ce ticket en tant qu'ingénieur senior et réponds avec la structure suivante :

Compréhension du besoin :
Reformule ce qui est demandé pour confirmer ta compréhension.

Approche technique :
Explique ton choix d'implémentation et pourquoi.

Code généré :
Fournis le code complet, propre et commenté.

Intégration :
Indique comment intégrer ce code dans le projet existant."""

    else:
        instruction = """Analyse ce ticket en tant qu'ingénieur senior et réponds avec la structure suivante :

Résumé du ticket :
Explique clairement ce qui est demandé.

Analyse technique :
Identifie les enjeux techniques, les dépendances ou les risques.

Plan d'action :
Propose des étapes concrètes pour traiter ce ticket.

Recommandations :
Ajoute toute suggestion pertinente basée sur ton expérience."""

    return en_tete + instruction, intention
def envoyer_a_agent(prompt, agent_cible="gemini", base_url="http://127.0.0.1:5000"):
    """Envoie le prompt construit à l'agent choisi, via son API dédiée, avec la clé API correspondante."""
    if agent_cible == "gemini":
        url = f"{base_url}/api/agent1/chat"
        cle_api = AGENT1_API_KEY
    elif agent_cible == "llama":
        url = f"{base_url}/api/agent2/chat"
        cle_api = AGENT2_API_KEY
    else:
        raise ValueError(f"Agent cible inconnu : {agent_cible}. Utilisez 'gemini' ou 'llama'.")

    reponse = requests.post(
        url,
        json={"question": prompt},
        headers={"X-API-Key": cle_api}
    )

    if reponse.status_code != 200:
        raise ValueError(f"Erreur lors de l'appel à l'agent {agent_cible}. Code : {reponse.status_code}")

    return reponse.json()
def traiter_ticket(cle_ticket, agent_cible="gemini"):
    """Pipeline complet : lit le ticket, analyse l'intention, construit le prompt, et l'envoie à l'agent choisi."""
    ticket = lire_ticket(cle_ticket)
    prompt, intention = construire_prompt(ticket)
    resultat_agent = envoyer_a_agent(prompt, agent_cible=agent_cible)

    return {
        "ticket": ticket,
        "intention_detectee": intention,
        "agent_utilise": agent_cible,
        "reponse_agent": resultat_agent["reponse"],
        "tokens_total": resultat_agent.get("tokens_total", 0),
    }
if __name__ == "__main__":
    resultat = traiter_ticket("SCRUM-1", agent_cible="gemini")

    print("=== TICKET ===")
    print(resultat["ticket"]["titre"])
    print()
    print("=== INTENTION DÉTECTÉE ===")
    print(resultat["intention_detectee"])
    print()
    print("=== RÉPONSE DE L'AGENT ===")
    print(resultat["reponse_agent"])
    print()
    print("Tokens utilisés :", resultat["tokens_total"])