import os
import sys
from werkzeug.utils import secure_filename
from rag.rag_engine import ajouter_document
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from agents.agent_jira import traiter_ticket
sys.path.append(os.path.dirname(__file__))
import requests
from agents.agent_gemini import repondre_avec_rag
from agents.agent_llama import repondre_sans_rag
from agents.dialogue import lancer_dialogue
from utils.cost_calculator import generer_rapport_comparaison

app = Flask(__name__, static_folder="static")
CORS(app)
AGENT1_API_KEY = os.getenv("AGENT1_API_KEY")
AGENT2_API_KEY = os.getenv("AGENT2_API_KEY")

BASE_URL_INTERNE = "http://127.0.0.1:5000"


def appeler_agent_interne(agent_cible, question):
    """Tout appel à un agent, même venant de ce serveur, passe par son API officielle et sa clé."""
    if agent_cible == "gemini":
        url = f"{BASE_URL_INTERNE}/api/agent1/chat"
        cle = AGENT1_API_KEY
    elif agent_cible == "llama":
        url = f"{BASE_URL_INTERNE}/api/agent2/chat"
        cle = AGENT2_API_KEY
    else:
        raise ValueError(f"Agent inconnu : {agent_cible}")

    reponse = requests.post(
        url,
        json={"question": question},
        headers={"X-API-Key": cle}
    )
    return reponse.json()
def cle_valide(cle_recue, cle_attendue):
    """Vérifie que la clé API fournie correspond à la clé attendue pour cet agent."""
    return cle_recue is not None and cle_recue == cle_attendue
@app.route("/")
def accueil():
    """Sert la page principale du chatbot."""
    return send_from_directory("static", "index.html")
@app.route("/api/chat", methods=["POST"])
def chat():
    """Reçoit une question et la transmet à l'agent choisi via son API officielle."""
    donnees = request.get_json()
    question = donnees.get("question")
    agent_choisi = donnees.get("agent", "gemini")

    if not question:
        return jsonify({"erreur": "Le champ 'question' est requis."}), 400

    if agent_choisi not in ("gemini", "llama"):
        return jsonify({"erreur": f"Agent inconnu : {agent_choisi}. Utilisez 'gemini' ou 'llama'."}), 400

    resultat = appeler_agent_interne(agent_choisi, question)
    return jsonify(resultat)
@app.route("/api/agent1/chat", methods=["POST"])
def agent1_chat():
    """API dédiée à l'Agent 1 (Gemini + RAG). Nécessite une clé API valide."""
    cle_fournie = request.headers.get("X-API-Key")
    if not cle_valide(cle_fournie, AGENT1_API_KEY):
        return jsonify({"erreur": "Clé API invalide ou manquante pour l'Agent 1."}), 401

    donnees = request.get_json()
    question = donnees.get("question")

    if not question:
        return jsonify({"erreur": "Le champ 'question' est requis."}), 400

    resultat = repondre_avec_rag(question)
    return jsonify(resultat)


@app.route("/api/agent2/chat", methods=["POST"])
def agent2_chat():
    """API dédiée à l'Agent 2 (Llama, sans RAG). Nécessite une clé API valide."""
    cle_fournie = request.headers.get("X-API-Key")
    if not cle_valide(cle_fournie, AGENT2_API_KEY):
        return jsonify({"erreur": "Clé API invalide ou manquante pour l'Agent 2."}), 401

    donnees = request.get_json()
    question = donnees.get("question")

    if not question:
        return jsonify({"erreur": "Le champ 'question' est requis."}), 400

    resultat = repondre_sans_rag(question)
    return jsonify(resultat)
@app.route("/api/dialogue", methods=["POST"])
def dialogue():
    """Lance un dialogue entre Agent 1 et Agent 2 sur un sujet donné."""
    donnees = request.get_json()
    sujet = donnees.get("sujet")
    nombre_tours = donnees.get("nombre_tours", 3)

    if not sujet:
        return jsonify({"erreur": "Le champ 'sujet' est requis."}), 400

    resultat = lancer_dialogue(sujet, nombre_tours=nombre_tours)
    return jsonify(resultat)
@app.route("/api/compare", methods=["POST"])
def compare():
    """Envoie la même question aux deux agents (via leur API officielle) et retourne un rapport de comparaison."""
    donnees = request.get_json()
    question = donnees.get("question")

    if not question:
        return jsonify({"erreur": "Le champ 'question' est requis."}), 400

    resultat_gemini = appeler_agent_interne("gemini", question)
    resultat_llama = appeler_agent_interne("llama", question)

    rapport = generer_rapport_comparaison(resultat_gemini, resultat_llama, question)
    return jsonify(rapport)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "rag", "documents")
EXTENSIONS_AUTORISEES = {"pdf", "txt"}

def extension_autorisee(nom_fichier):
    return "." in nom_fichier and nom_fichier.rsplit(".", 1)[1].lower() in EXTENSIONS_AUTORISEES


@app.route("/api/upload", methods=["POST"])
def upload():
    """Reçoit un fichier PDF ou TXT, le sauvegarde, et l'ajoute à la base RAG."""
    if "fichier" not in request.files:
        return jsonify({"erreur": "Aucun fichier reçu."}), 400

    fichier = request.files["fichier"]

    if fichier.filename == "":
        return jsonify({"erreur": "Nom de fichier vide."}), 400

    if not extension_autorisee(fichier.filename):
        return jsonify({"erreur": "Seuls les fichiers .pdf et .txt sont acceptés."}), 400

    nom_securise = secure_filename(fichier.filename)
    chemin_sauvegarde = os.path.join(UPLOAD_DIR, nom_securise)
    fichier.save(chemin_sauvegarde)

    nombre_chunks = ajouter_document(chemin_sauvegarde)

    return jsonify({
        "message": f"Fichier '{nom_securise}' ajouté avec succès.",
        "chunks_ajoutes": nombre_chunks
    })
@app.route("/api/jira", methods=["POST"])
def jira():
    """Lit un ticket Jira, analyse son intention, et envoie un prompt construit à l'agent choisi."""
    donnees = request.get_json()
    cle_ticket = donnees.get("cle_ticket")
    agent_cible = donnees.get("agent_cible", "gemini")

    if not cle_ticket:
        return jsonify({"erreur": "Le champ 'cle_ticket' est requis."}), 400

    try:
        resultat = traiter_ticket(cle_ticket, agent_cible=agent_cible)
    except Exception as erreur:
        return jsonify({"erreur": f"Erreur lors du traitement du ticket : {str(erreur)}"}), 500

    return jsonify(resultat)
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)