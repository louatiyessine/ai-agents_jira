import os
import requests
from dotenv import load_dotenv

load_dotenv()

AGENT1_API_KEY = os.getenv("AGENT1_API_KEY")
AGENT2_API_KEY = os.getenv("AGENT2_API_KEY")
BASE_URL_INTERNE = "http://127.0.0.1:5000"


def appeler_agent_interne(agent_cible, question):
    """Tout appel à un agent, même interne au projet, passe par son API officielle et sa clé."""
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