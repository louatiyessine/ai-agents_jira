import ollama

MODEL_NAME = "llama3.2"
def repondre_sans_rag(question):
    """Envoie directement la question à Llama 3.2, sans RAG, sans contexte documentaire."""
    reponse = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": question}
        ]
    )

    tokens_entree = reponse["prompt_eval_count"]
    tokens_sortie = reponse["eval_count"]

    return {
        "reponse": reponse["message"]["content"],
        "tokens_entree": tokens_entree,
        "tokens_sortie": tokens_sortie,
        "tokens_total": tokens_entree + tokens_sortie,
    }
if __name__ == "__main__":
    question_test = "Combien de jours de congés ai-je par an ?"
    resultat = repondre_sans_rag(question_test)

    print("QUESTION :", question_test)
    print("\nRÉPONSE :", resultat["reponse"])
    print("\n--- Statistiques tokens ---")
    print("Tokens entrée :", resultat["tokens_entree"])
    print("Tokens sortie :", resultat["tokens_sortie"])
    print("Tokens total :", resultat["tokens_total"])