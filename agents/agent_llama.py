import ollama

MODEL_NAME = "llama3.2"
def repondre_sans_rag(question):
    try:
        reponse = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": question}]
        )
    except Exception as erreur:
        print(f"[agent_llama] Erreur Ollama : {erreur}")
        return {
            "reponse": "Le service Llama (Ollama) est indisponible. Vérifiez qu'Ollama tourne bien sur votre machine.",
            "tokens_entree": 0,
            "tokens_sortie": 0,
            "tokens_total": 0,
        }

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