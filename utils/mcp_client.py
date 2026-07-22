# utils/mcp_client.py
import asyncio
import json
import os
import re
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

# Sécurité : dossier racine auquel l'agent a accès en lecture/écriture via le
# serveur MCP filesystem. Restreint volontairement à l'espace de travail
# (au lieu de tout C:\) pour éviter qu'un mauvais prompt touche des fichiers
# système. Surchargeable via la variable d'environnement MCP_FS_ROOT.
FS_ALLOWED_DIR = os.getenv("MCP_FS_ROOT", r"C:\licence informatique")


def _get_server_params():
    """Retourne les paramètres des 3 serveurs MCP."""
    return (
        StdioServerParameters(
            command="python",
            args=["mcp_server.py"],
            env=None
        ),
        StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", FS_ALLOWED_DIR],
            env=None
        ),
        StdioServerParameters(
            command="uvx",
            args=["mcp-atlassian"],
            env={
                "JIRA_URL": f"https://{os.getenv('JIRA_DOMAIN')}",
                "JIRA_USERNAME": os.getenv("JIRA_EMAIL"),
                "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN")
            }
        )
    )


def _parse_llm_response(raw: str, fallback: str) -> dict:
    """
    Parse la réponse JSON du LLM de façon robuste.
    Gère les cas : ```json```, ``` ```, ou JSON brut.
    Utilisé par Gemini ET Llama — pas de duplication.
    """
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    else:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)

    try:
        parsed = json.loads(raw)
        if not parsed.get("use_tool"):
            return {"tool_name": None,
                    "direct_response": parsed.get("direct_response", "")}
        return {"tool_name": parsed["tool_name"],
                "tool_args": parsed["tool_args"]}
    except json.JSONDecodeError:
        return {"tool_name": None, "direct_response": fallback}


def _build_prompt(messages: list, tools: list) -> str:
    """
    Construit le prompt envoyé au LLM.
    Utilisé par Gemini ET Llama — pas de duplication.
    """
    tools_description = json.dumps(tools, indent=2, ensure_ascii=False)
    historique = "\n".join([
        f"{m['role'].upper()} : {m['content']}"
        for m in messages
    ])
    return f"""Tu es un assistant avec accès aux outils suivants :

OUTILS JIRA (préfixe jira__) : pipeline complet — analyse + prompt IA + réponse structurée
OUTILS FILESYSTEM (préfixe fs__) : lire, créer, modifier des fichiers sur le PC
OUTILS ATLASSIAN (préfixe atlassian__) : accès direct à Jira

IMPORTANT — pour trouver un dossier ou un projet par nom avec fs__search_files,
utilise TOUJOURS un motif récursif "**/NOM" (par exemple "**/CASS TSYP13").
Un motif simple comme "*NOM*" ne descend PAS dans les sous-dossiers et ne trouvera rien.

Liste complète :
{tools_description}

Historique :
{historique}

Réponds UNIQUEMENT avec un JSON valide :
Si tu as besoin d'un outil :
{{"use_tool": true, "tool_name": "nom_outil", "tool_args": {{}}}}
Si tu as terminé :
{{"use_tool": false, "direct_response": "explication"}}"""


async def _ask_llm(messages: list, tools: list, agent: str) -> dict:
    """
    Envoie le prompt au LLM choisi.
    Si Gemini retourne 429 (quota dépassé),
    bascule automatiquement sur Llama.
    """
    prompt = _build_prompt(messages, tools)

    if agent == "gemini":
        try:
            from google import genai
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"temperature": 0.1}
            )
            raw = response.text.strip()
            return _parse_llm_response(raw, raw)

        except Exception as e:
            # Si quota dépassé → bascule sur Llama automatiquement
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("Quota Gemini dépassé — bascule automatique sur Llama...")
                agent = "llama"
            else:
                raise e

    # Llama — local, gratuit, sans limite
    import requests
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=60
        )
        raw = response.json()["response"].strip()
        return _parse_llm_response(raw, raw)

    except Exception as e:
        raise RuntimeError(f"Llama aussi indisponible : {str(e)}")


async def _run_mcp_core(user_message: str, agent: str = "gemini") -> dict:
    """
    Cycle MCP complet — trois serveurs, boucle d'exécution stable.
    Retourne un dict structuré : {"actions": [...], "final": "..."}.
    Chaque action = {"tool": nom, "args": {...}, "result": texte}.
    """
    jira_params, fs_params, atl_params = _get_server_params()

    async with stdio_client(jira_params) as (jr, jw):
        async with ClientSession(jr, jw) as jira_session:
            await jira_session.initialize()
            jira_tools = [
                {"name": f"jira__{t.name}", "description": t.description,
                 "parameters": t.inputSchema}
                for t in (await jira_session.list_tools()).tools
            ]

            async with stdio_client(fs_params) as (fr, fw):
                async with ClientSession(fr, fw) as fs_session:
                    await fs_session.initialize()
                    fs_tools = [
                        {"name": f"fs__{t.name}", "description": t.description,
                         "parameters": t.inputSchema}
                        for t in (await fs_session.list_tools()).tools
                    ]

                    # mcp-atlassian est optionnel
                    atlassian_tools = []
                    atlassian_session = None
                    atlassian_cm = None

                    try:
                        atlassian_cm = stdio_client(atl_params)
                        ar, aw = await atlassian_cm.__aenter__()
                        atlassian_session = ClientSession(ar, aw)
                        await atlassian_session.__aenter__()
                        await atlassian_session.initialize()
                        atlassian_tools = [
                            {"name": f"atlassian__{t.name}",
                             "description": t.description,
                             "parameters": t.inputSchema}
                            for t in (await atlassian_session.list_tools()).tools
                        ]
                        print(f"mcp-atlassian : {len(atlassian_tools)} outils")
                    except Exception as e:
                        print(f"mcp-atlassian non disponible : {e}")

                    all_tools = jira_tools + fs_tools + atlassian_tools
                    actions = []
                    messages = [{"role": "user", "content": user_message}]

                    try:
                        for _ in range(15):
                            tool_call = await _ask_llm(messages, all_tools, agent)

                            if not tool_call.get("tool_name"):
                                final = tool_call.get("direct_response", "")
                                return {"actions": actions, "final": final}

                            tool_name = tool_call["tool_name"]
                            tool_args = tool_call["tool_args"]

                            try:
                                if tool_name.startswith("jira__"):
                                    result = await jira_session.call_tool(
                                        tool_name.replace("jira__", ""), tool_args)
                                elif tool_name.startswith("fs__"):
                                    result = await fs_session.call_tool(
                                        tool_name.replace("fs__", ""), tool_args)
                                elif tool_name.startswith("atlassian__"):
                                    if not atlassian_session:
                                        result_text = "mcp-atlassian non disponible."
                                        continue
                                    result = await atlassian_session.call_tool(
                                        tool_name.replace("atlassian__", ""), tool_args)
                                else:
                                    result_text = f"Outil inconnu : {tool_name}"
                                    continue

                                result_text = result.content[0].text

                            except Exception as e:
                                result_text = f"Erreur {tool_name} : {str(e)}"

                            actions.append({"tool": tool_name,
                                          "args": tool_args,
                                          "result": result_text})
                            messages.append({
                                "role": "assistant",
                                "content": f"J'ai utilisé '{tool_name}'. Résultat : {result_text}"
                            })
                            messages.append({
                                "role": "user",
                                "content": "Continue si nécessaire."
                            })

                    finally:
                        for obj in [atlassian_session, atlassian_cm]:
                            if obj:
                                try:
                                    await obj.__aexit__(None, None, None)
                                except Exception:
                                    pass

                    return {"actions": actions,
                            "final": "Limite de 15 actions atteinte."}


async def run_mcp_query(user_message: str, agent: str = "gemini") -> str:
    """Version texte (compatibilité) — formate les actions + la réponse finale."""
    data = await _run_mcp_core(user_message, agent)
    actions, final = data["actions"], data["final"]
    if actions:
        resume = "\n".join([
            f"- {a['tool']} : {a['result'][:120]}..."
            for a in actions
        ])
        return f"Actions effectuées :\n{resume}\n\n---\n\n{final}"
    return final


async def run_mcp_plan(user_message: str, agent: str = "gemini") -> str:
    """Analyse le ticket et retourne le plan SANS exécuter."""
    jira_params, _, _ = _get_server_params()

    async with stdio_client(jira_params) as (jr, jw):
        async with ClientSession(jr, jw) as jira_session:
            await jira_session.initialize()
            ticket_key = "SCRUM-" + user_message.split("SCRUM-")[1].split()[0] \
                if "SCRUM-" in user_message else ""
            ticket_result = await jira_session.call_tool(
                "solve_jira_ticket", {"ticket_key": ticket_key}
            )
            ticket_info = ticket_result.content[0].text

    from google import genai
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""Analyse ce ticket et décris ce que tu vas faire sur les fichiers,
sans rien exécuter.

{ticket_info}

Format :
Plan d'action :
1. [action 1]
2. [action 2]""",
        config={"temperature": 0.1}
    )
    return response.text.strip()


def query_via_mcp(user_message: str, agent: str = "gemini") -> str:
    """Version synchrone pour Flask."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_mcp_query(user_message, agent))
        finally:
            loop.close()
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Erreur MCP client : {str(e)}")


def query_via_mcp_plan(user_message: str, agent: str = "gemini") -> str:
    """Version synchrone pour Flask."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_mcp_plan(user_message, agent))
        finally:
            loop.close()
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Erreur MCP plan : {str(e)}")


def query_via_mcp_structured(user_message: str, agent: str = "gemini") -> dict:
    """
    Version synchrone STRUCTURÉE pour Flask.
    Retourne {"actions": [...], "final": "..."} — utilisé par l'interface Angular
    pour afficher chaque outil MCP réellement appelé (la démarche).
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run_mcp_core(user_message, agent))
        finally:
            loop.close()
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Erreur MCP structuré : {str(e)}")