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
    Cycle MCP complet — deux serveurs ouverts une seule fois :
    - mcp_server.py     : outils Jira + search_project
    - server-filesystem : lire/créer/modifier fichiers sur le PC
    """

    jira_server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None
    )

    filesystem_server_params = StdioServerParameters(
        command="npx",
        args=[
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "C:\\"
        ],
        env=None
    )

    # ─────────────────────────────────────
    # On ouvre les deux serveurs UNE SEULE fois
    # et on garde la connexion pendant toute la boucle
    # ─────────────────────────────────────
    async with stdio_client(jira_server_params) as (jira_read, jira_write):
        async with ClientSession(jira_read, jira_write) as jira_session:
            await jira_session.initialize()

            async with stdio_client(filesystem_server_params) as (fs_read, fs_write):
                async with ClientSession(fs_read, fs_write) as fs_session:
                    await fs_session.initialize()

                    # ─────────────────────────────────────
                    # Récupérer tous les outils des deux serveurs
                    # ─────────────────────────────────────
                    jira_response = await jira_session.list_tools()
                    fs_response = await fs_session.list_tools()

                    jira_tools = [
                        {
                            "name": f"jira__{tool.name}",
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                        for tool in jira_response.tools
                    ]

                    fs_tools = [
                        {
                            "name": f"fs__{tool.name}",
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                        for tool in fs_response.tools
                    ]

                    all_tools = jira_tools + fs_tools

                    # ─────────────────────────────────────
                    # Boucle d'exécution — stable
                    # Le LLM peut enchaîner plusieurs outils
                    # sans rouvrir les serveurs
                    # ─────────────────────────────────────
                    actions = []
                    messages = [{"role": "user", "content": user_message}]

                    for _ in range(10):  # max 10 actions

                        if agent == "gemini":
                            tool_call = await _ask_gemini_with_tools(
                                messages, all_tools
                            )
                        else:
                            tool_call = await _ask_llama_with_tools(
                                messages, all_tools
                            )

                        # Le LLM a terminé — réponse finale
                        if not tool_call.get("tool_name"):
                            final = tool_call.get("direct_response", "")
                            if actions:
                                resume = "\n".join([
                                    f"- {a['tool']} : {a['result'][:120]}..."
                                    for a in actions
                                ])
                                return (
                                    f"Actions effectuées :\n{resume}"
                                    f"\n\n---\n\n{final}"
                                )
                            return final

                        tool_name = tool_call["tool_name"]
                        tool_args = tool_call["tool_args"]

                        # ─────────────────────────────────────
                        # Exécuter sur le bon serveur
                        # sans rouvrir la connexion
                        # ─────────────────────────────────────
                        try:
                            if tool_name.startswith("jira__"):
                                real_name = tool_name.replace("jira__", "")
                                result = await jira_session.call_tool(
                                    real_name, tool_args
                                )
                            elif tool_name.startswith("fs__"):
                                real_name = tool_name.replace("fs__", "")
                                result = await fs_session.call_tool(
                                    real_name, tool_args
                                )
                            else:
                                result_text = f"Outil inconnu : {tool_name}"
                                continue

                            result_text = result.content[0].text

                        except Exception as e:
                            result_text = f"Erreur lors de l'exécution de {tool_name} : {str(e)}"

                        # Garder trace de chaque action
                        actions.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result_text
                        })

                        # Ajouter dans le contexte pour le prochain tour
                        messages.append({
                            "role": "assistant",
                            "content": (
                                f"J'ai utilisé '{tool_name}' avec les paramètres {tool_args}. "
                                f"Résultat : {result_text}"
                            )
                        })
                        messages.append({
                            "role": "user",
                            "content": "Continue avec la prochaine étape si nécessaire."
                        })

                    return "Limite de 10 actions atteinte."
# ─────────────────────────────────────
# GEMINI : Étape 3-4
# Envoie la question + outils, récupère le choix d'outil du LLM
# ─────────────────────────────────────
async def _ask_gemini_with_tools(messages: list, tools: list) -> dict:
    from google import genai
    import re
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    tools_description = json.dumps(tools, indent=2, ensure_ascii=False)

    historique = "\n".join([
        f"{m['role'].upper()} : {m['content']}"
        for m in messages
    ])

    prompt = f"""Tu es un assistant avec accès aux outils suivants :

OUTILS JIRA (préfixe jira__) :
Ces outils permettent de lire et traiter des tickets Jira.

OUTILS FILESYSTEM (préfixe fs__) :
Ces outils permettent de lire, créer et modifier des fichiers sur le PC.

Liste complète des outils :
{tools_description}

Historique de la conversation :
{historique}

IMPORTANT : Tu dois répondre UNIQUEMENT avec un objet JSON valide, rien d'autre.
Pas de texte avant, pas de texte après, pas de markdown.

Si tu as besoin d'un outil :
{{"use_tool": true, "tool_name": "nom_outil", "tool_args": {{}}}}

Si tu as terminé :
{{"use_tool": false, "direct_response": "explication de ce que tu as fait"}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"temperature": 0.1}
    )

    raw = response.text.strip()

    # ─────────────────────────────────────
    # Nettoyage robuste — plusieurs cas possibles
    # ─────────────────────────────────────

    # Cas 1 : bloc ```json ... ```
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()

    # Cas 2 : bloc ``` ... ```
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    # Cas 3 : extraire le premier objet JSON trouvé dans le texte
    else:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Si toujours pas parseable → réponse directe
        return {
            "tool_name": None,
            "direct_response": response.text.strip()
        }

    if not parsed.get("use_tool"):
        return {
            "tool_name": None,
            "direct_response": parsed.get("direct_response", "")
        }

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

async def run_mcp_plan(user_message: str, agent: str = "gemini") -> str:
    """
    Analyse le ticket et retourne le plan d'action
    SANS exécuter quoi que ce soit.
    """
    jira_server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None
    )

    async with stdio_client(jira_server_params) as (jira_read, jira_write):
        async with ClientSession(jira_read, jira_write) as jira_session:
            await jira_session.initialize()

            # Lire le ticket via le serveur Jira
            ticket_result = await jira_session.call_tool(
                "solve_jira_ticket",
                {"ticket_key": "SCRUM-" + user_message.split("SCRUM-")[1].split()[0]
                if "SCRUM-" in user_message else ""}
            )
            ticket_info = ticket_result.content[0].text

    # Demander à Gemini de planifier sans exécuter
    from google import genai
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    prompt = f"""Analyse ce ticket Jira et dis-moi exactement ce que tu vas faire 
sur les fichiers du PC, sans rien exécuter.

Informations du ticket :
{ticket_info}

Réponds avec un plan clair et concis :
- Quels fichiers tu vas créer
- Quels fichiers tu vas modifier et pourquoi
- Ce que tu vas ajouter/changer dans chaque fichier

Format de réponse :
Plan d'action :
1. [action 1]
2. [action 2]
...

NE PAS exécuter les actions, juste les décrire."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"temperature": 0.1}
    )

    return response.text.strip()


def query_via_mcp_plan(user_message: str, agent: str = "gemini") -> str:
    """Version synchrone pour Flask."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_mcp_plan(user_message, agent))
    finally:
        loop.close()
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