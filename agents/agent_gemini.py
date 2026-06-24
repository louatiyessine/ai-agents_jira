import os
import sys
from google import genai
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from rag.rag_engine import rechercher_contexte

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"


def repondre_avec_rag(question):
    contexte = rechercher_contexte(question, k=3)

    prompt = f"""Tu es un assistant utile. Voici un contexte qui peut t'aider si la question s'y rapporte :

CONTEXTE :
{contexte}

Si la question concerne ce contexte, base ta réponse UNIQUEMENT sur les informations qu'il contient, et dis clairement si une information demandée n'y figure pas. Si la question n'a rien à voir avec ce contexte (salutations, question générale, conversation libre), réponds normalement avec tes connaissances générales, sans mentionner le contexte.

QUESTION :
{question}

RÉPONSE :"""

    try:
        reponse = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
    except Exception as erreur:
        return {
            "reponse": "Le service Gemini est temporairement surchargé. Merci de réessayer dans quelques secondes.",
            "tokens_entree": 0,
            "tokens_sortie": 0,
            "tokens_reflexion": 0,
            "tokens_total": 0,
        }

    usage = reponse.usage_metadata

    return {
        "reponse": reponse.text,
        "tokens_entree": usage.prompt_token_count,
        "tokens_sortie": usage.candidates_token_count or 0,
        "tokens_reflexion": usage.thoughts_token_count or 0,
        "tokens_total": usage.total_token_count,
    }

if __name__ == "__main__":
    question_test = "Combien de jours de congés ai-je par an ?"
    resultat = repondre_avec_rag(question_test)

    print("QUESTION :", question_test)
    print("\nRÉPONSE :", resultat["reponse"])
    print("\n--- Statistiques tokens ---")
    print("Tokens entrée :", resultat["tokens_entree"])
    print("Tokens sortie :", resultat["tokens_sortie"])
    print("Tokens réflexion (thinking) :", resultat["tokens_reflexion"])
    print("Tokens total :", resultat["tokens_total"])