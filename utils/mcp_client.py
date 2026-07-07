# utils/mcp_client.py
import asyncio
import json
import os
from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()


async def run_mcp_query(user_message: str, agent: str = "gemini") -> str:
    """
    Cycle MCP complet :
    1. Lance le serveur MCP
    2. Récupère la liste des outils
    3. Envoie la question + outils au LLM
    4. Le LLM décide quel outil utiliser
    5. Exécute l'outil
    6. Renvoie le résultat au LLM
    7. Retourne la réponse finale
    """

    # ─────────────────────────────────────
    # Étape 1 : Connexion au serveur MCP
    # On lance mcp_server.py comme sous-processus
    # ─────────────────────────────────────
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # ─────────────────────────────────────
            # Étape 2 : Récupérer la liste des outils
            # Le serveur déclare ses outils disponibles
            # ─────────────────────────────────────
            await session.initialize()
            tools_response = await session.list_tools()

            # On convertit les outils MCP en format que Gemini comprend
            tools_for_llm = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
                for tool in tools_response.tools
            ]

            # ─────────────────────────────────────
            # Étape 3 & 4 : Envoyer la question au LLM
            # Le LLM reçoit la question + les outils disponibles
            # Il décide s'il doit utiliser un outil
            # ─────────────────────────────────────
            if agent == "gemini":
                tool_call = await _ask_gemini_with_tools(user_message, tools_for_llm)
            else:
                tool_call = await _ask_llama_with_tools(user_message, tools_for_llm)

            # ─────────────────────────────────────
            # Étape 5 : Le client reçoit la demande d'outil du LLM
            # Si le LLM ne veut pas utiliser d'outil → réponse directe
            # ─────────────────────────────────────
            if not tool_call:
                return tool_call.get("direct_response", "Aucune réponse générée.")

            tool_name = tool_call["tool_name"]
            tool_args = tool_call["tool_args"]

            # ─────────────────────────────────────
            # Étape 6 : Exécuter l'outil sur le serveur MCP
            # ─────────────────────────────────────
            tool_result = await session.call_tool(tool_name, tool_args)
            result_text = tool_result.content[0].text

            # ─────────────────────────────────────
            # Étape 7 & 8 : Renvoyer le résultat au LLM
            # Le LLM génère la réponse finale avec le résultat de l'outil
            # ─────────────────────────────────────
            if agent == "gemini":
                final_response = await _gemini_final_response(
                    user_message, tool_name, result_text
                )
            else:
                final_response = await _llama_final_response(
                    user_message, tool_name, result_text
                )

            return final_response


# ─────────────────────────────────────
# GEMINI : Étape 3-4
# Envoie la question + outils, récupère le choix d'outil du LLM
# ─────────────────────────────────────
async def _ask_gemini_with_tools(message: str, tools: list) -> dict:
    from google import genai

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    tools_description = json.dumps(tools, indent=2, ensure_ascii=False)

    prompt = f"""Tu es un assistant intelligent avec accès aux outils suivants :

{tools_description}

Question de l'utilisateur : {message}

Si la question nécessite un outil, réponds UNIQUEMENT avec ce JSON :
{{"use_tool": true, "tool_name": "nom_outil", "tool_args": {{...}}}}

Si tu peux répondre directement sans outil, réponds UNIQUEMENT avec :
{{"use_tool": false, "direct_response": "ta réponse ici"}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(raw)

    if not parsed.get("use_tool"):
        return {"tool_name": None, "tool_args": None,
                "direct_response": parsed.get("direct_response", "")}

    return {
        "tool_name": parsed["tool_name"],
        "tool_args": parsed["tool_args"]
    }
# ─────────────────────────────────────
# GEMINI : Étape 7-8
# Reçoit le résultat de l'outil et génère la réponse finale
# ─────────────────────────────────────
async def _gemini_final_response(original_message: str, tool_used: str, tool_result: str) -> str:
    from google import genai

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    prompt = f"""L'utilisateur a demandé : {original_message}

Tu as utilisé l'outil '{tool_used}' qui a retourné :
{tool_result}

Formule maintenant une réponse claire et complète à l'utilisateur basée sur ce résultat.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


# ─────────────────────────────────────
# LLAMA : Étape 3-4
# Même logique mais via Ollama local
# ─────────────────────────────────────
async def _ask_llama_with_tools(message: str, tools: list) -> dict:
    import requests

    tools_description = json.dumps(tools, indent=2, ensure_ascii=False)

    prompt = f"""Tu es un assistant intelligent avec accès aux outils suivants :

{tools_description}

Question de l'utilisateur : {message}

Si la question nécessite un outil, réponds UNIQUEMENT avec ce JSON :
{{"use_tool": true, "tool_name": "nom_outil", "tool_args": {{...}}}}

Si tu peux répondre directement sans outil, réponds UNIQUEMENT avec :
{{"use_tool": false, "direct_response": "ta réponse ici"}}
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": prompt, "stream": False}
    )

    raw = response.json()["response"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(raw)

    if not parsed.get("use_tool"):
        return {"tool_name": None, "tool_args": None,
                "direct_response": parsed.get("direct_response", "")}

    return {
        "tool_name": parsed["tool_name"],
        "tool_args": parsed["tool_args"]
    }


# ─────────────────────────────────────
# LLAMA : Étape 7-8
# ─────────────────────────────────────
async def _llama_final_response(original_message: str, tool_used: str, tool_result: str) -> str:
    import requests

    prompt = f"""L'utilisateur a demandé : {original_message}

Tu as utilisé l'outil '{tool_used}' qui a retourné :
{tool_result}

Formule maintenant une réponse claire et complète à l'utilisateur basée sur ce résultat.
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": prompt, "stream": False}
    )

    return response.json()["response"]


# ─────────────────────────────────────
# Fonction synchrone pour Flask
# Flask n'est pas async, donc on wrappe
# ─────────────────────────────────────
def query_via_mcp(user_message: str, agent: str = "gemini") -> str:
    import traceback
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_mcp_query(user_message, agent))
        finally:
            loop.close()
    except Exception as e:
        # Affiche l'erreur complète dans le terminal Flask
        traceback.print_exc()
        raise RuntimeError(f"Erreur MCP client : {str(e)}")