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
    """Cherche le contexte pertinent dans les documents, puis demande à Gemini de répondre en se basant sur ce contexte."""
    contexte = rechercher_contexte(question, k=3)

    prompt = f"""Tu es un assistant qui répond aux questions en te basant UNIQUEMENT sur le contexte fourni ci-dessous.
Si la réponse ne se trouve pas dans le contexte, dis clairement que tu ne sais pas, ne l'invente pas.

CONTEXTE :
{contexte}

QUESTION :
{question}

RÉPONSE :"""

    reponse = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

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