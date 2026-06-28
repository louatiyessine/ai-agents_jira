import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.agent_client import appeler_agent_interne
def lancer_dialogue(sujet, nombre_tours=3):
    """Fait dialoguer Agent 1 (Gemini+RAG) et Agent 2 (Llama, sans RAG) sur un sujet donné."""
    historique = []
    stats_totales = {
        "gemini_tokens": 0,
        "llama_tokens": 0,
    }

    message_actuel = sujet

    for tour in range(nombre_tours):
        resultat_gemini = appeler_agent_interne("gemini", message_actuel)
        historique.append({
            "tour": tour + 1,
            "agent": "Agent 1 (Gemini + RAG)",
            "message": resultat_gemini["reponse"],
            "tokens": resultat_gemini["tokens_total"],
        })
        stats_totales["gemini_tokens"] += resultat_gemini["tokens_total"]

        message_actuel = resultat_gemini["reponse"]

        resultat_llama = appeler_agent_interne("llama", message_actuel)
        historique.append({
            "tour": tour + 1,
            "agent": "Agent 2 (Llama, sans RAG)",
            "message": resultat_llama["reponse"],
            "tokens": resultat_llama["tokens_total"],
        })
        stats_totales["llama_tokens"] += resultat_llama["tokens_total"]

        message_actuel = resultat_llama["reponse"]

    return {
        "historique": historique,
        "stats_totales": stats_totales,
    }
if __name__ == "__main__":
    sujet_test = "Parle-moi de la politique de congés de l'entreprise."
    resultat = lancer_dialogue(sujet_test, nombre_tours=2)

    print("=== DIALOGUE ENTRE LES AGENTS ===")
    print("Sujet initial :", sujet_test)
    print()

    for entree in resultat["historique"]:
        print(f"[Tour {entree['tour']}] {entree['agent']} ({entree['tokens']} tokens) :")
        print(entree["message"])
        print()

    print("=== STATISTIQUES TOTALES ===")
    print("Tokens consommés par Gemini :", resultat["stats_totales"]["gemini_tokens"])
    print("Tokens consommés par Llama :", resultat["stats_totales"]["llama_tokens"])