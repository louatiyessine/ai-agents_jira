import os
import sys

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.append(os.path.dirname(__file__))

from agents.agent_gemini import repondre_avec_rag
from agents.agent_llama import repondre_sans_rag
from agents.dialogue import lancer_dialogue
from utils.cost_calculator import generer_rapport_comparaison

app = Flask(__name__, static_folder="static")
CORS(app)
@app.route("/")
def accueil():
    """Sert la page principale du chatbot."""
    return send_from_directory("static", "index.html")
@app.route("/api/chat", methods=["POST"])
def chat():
    """Reçoit une question et l'envoie à l'agent choisi (gemini ou llama)."""
    donnees = request.get_json()
    question = donnees.get("question")
    agent_choisi = donnees.get("agent", "gemini")

    if not question:
        return jsonify({"erreur": "Le champ 'question' est requis."}), 400

    if agent_choisi == "gemini":
        resultat = repondre_avec_rag(question)
    elif agent_choisi == "llama":
        resultat = repondre_sans_rag(question)
    else:
        return jsonify({"erreur": f"Agent inconnu : {agent_choisi}. Utilisez 'gemini' ou 'llama'."}), 400

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
    """Envoie la même question aux deux agents et retourne un rapport de comparaison complet."""
    donnees = request.get_json()
    question = donnees.get("question")

    if not question:
        return jsonify({"erreur": "Le champ 'question' est requis."}), 400

    resultat_gemini = repondre_avec_rag(question)
    resultat_llama = repondre_sans_rag(question)

    rapport = generer_rapport_comparaison(resultat_gemini, resultat_llama, question)
    return jsonify(rapport)
if __name__ == "__main__":
    app.run(debug=True, port=5000)