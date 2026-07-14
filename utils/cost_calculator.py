TARIFS = {
    "gemini-2.5-flash": {
        "prix_entree_par_million": 0.30,
        "prix_sortie_par_million": 2.50,
    },
    "llama3.2-local-reel": {
        "prix_entree_par_million": 0.00,
        "prix_sortie_par_million": 0.00,
    },
    "llama3.2-si-api-payante": {
        "prix_entree_par_million": 0.06,
        "prix_sortie_par_million": 0.06,
    },
}
def calculer_cout(tokens_entree, tokens_sortie, nom_modele):
    """Calcule le coût simulé en dollars, à partir des tokens et du tarif du modèle."""
    if nom_modele not in TARIFS:
        raise ValueError(f"Modèle inconnu : {nom_modele}. Modèles disponibles : {list(TARIFS.keys())}")

    tarif = TARIFS[nom_modele]

    cout_entree = (tokens_entree / 1_000_000) * tarif["prix_entree_par_million"]
    cout_sortie = (tokens_sortie / 1_000_000) * tarif["prix_sortie_par_million"]
    cout_total = cout_entree + cout_sortie

    return {
        "cout_entree": round(cout_entree, 6),
        "cout_sortie": round(cout_sortie, 6),
        "cout_total": round(cout_total, 6),
    }
def generer_rapport_comparaison(resultat_gemini, resultat_llama, question):
    """Compare les performances et coûts entre l'Agent 1 (Gemini+RAG) et l'Agent 2 (Llama, sans RAG) sur une même question."""

    cout_gemini = calculer_cout(
        resultat_gemini["tokens_entree"],
        resultat_gemini["tokens_sortie"] + resultat_gemini.get("tokens_reflexion", 0),
        "gemini-2.5-flash"
    )

    cout_llama_reel = calculer_cout(
        resultat_llama["tokens_entree"],
        resultat_llama["tokens_sortie"],
        "llama3.2-local-reel"
    )

    cout_llama_simule = calculer_cout(
        resultat_llama["tokens_entree"],
        resultat_llama["tokens_sortie"],
        "llama3.2-si-api-payante"
    )

    return {
        "question": question,
        "agent_1_gemini": {
            "reponse": resultat_gemini["reponse"],
            "tokens_total": resultat_gemini["tokens_total"],
            "cout_usd": cout_gemini["cout_total"],
        },
        "agent_2_llama": {
            "reponse": resultat_llama["reponse"],
            "tokens_total": resultat_llama["tokens_total"],
            "cout_reel_usd": cout_llama_reel["cout_total"],
            "cout_si_api_payante_usd": cout_llama_simule["cout_total"],
        },
        "ecart_cout_usd": round(cout_gemini["cout_total"] - cout_llama_simule["cout_total"], 6),
    }
if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

    from agents.agent_gemini import repondre_avec_rag
    from agents.agent_llama import repondre_sans_rag

    question_test = "Combien de jours de congés ai-je par an ?"

    resultat_gemini = repondre_avec_rag(question_test)
    resultat_llama = repondre_sans_rag(question_test)

    rapport = generer_rapport_comparaison(resultat_gemini, resultat_llama, question_test)

    print("=== RAPPORT DE COMPARAISON ===")
    print("Question :", rapport["question"])
    print()
    print("--- Agent 1 (Gemini + RAG) ---")
    print("Réponse :", rapport["agent_1_gemini"]["reponse"])
    print("Tokens :", rapport["agent_1_gemini"]["tokens_total"])
    print("Coût : $", rapport["agent_1_gemini"]["cout_usd"])
    print()
    print("--- Agent 2 (Llama, sans RAG) ---")
    print("Réponse :", rapport["agent_2_llama"]["reponse"])
    print("Tokens :", rapport["agent_2_llama"]["tokens_total"])
    print("Coût réel : $", rapport["agent_2_llama"]["cout_reel_usd"])
    print("Coût si API payante équivalente : $", rapport["agent_2_llama"]["cout_si_api_payante_usd"])
    print()
    print("Écart de coût (Gemini vs Llama simulé) : $", rapport["ecart_cout_usd"])