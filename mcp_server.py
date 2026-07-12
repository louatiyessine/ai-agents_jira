# mcp_server.py
import asyncio
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from agents.agent_jira import traiter_ticket

server = Server("technova-jira")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [

        # ─────────────────────────────────────
        # OUTIL 1 : solve_jira_ticket
        # Notre valeur ajoutée unique :
        # analyser_intention + construire_prompt
        # + appel à Gemini/Llama
        # Aucun serveur officiel ne fait ça
        # ─────────────────────────────────────
        types.Tool(
            name="solve_jira_ticket",
            description=(
                "Pipeline complet sur un ticket Jira : lit le ticket, "
                "détecte l'intention (bug/feature/analyse), "
                "génère un prompt professionnel via IA (promptToDevelopAgent), "
                "et retourne une réponse structurée d'ingénieur senior."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_key": {
                        "type": "string",
                        "description": "La clé du ticket Jira, ex: SCRUM-1"
                    },
                    "agent": {
                        "type": "string",
                        "description": "L'agent IA à utiliser : 'gemini' ou 'llama'",
                        "enum": ["gemini", "llama"],
                        "default": "gemini"
                    }
                },
                "required": ["ticket_key"]
            }
        ),

        # ─────────────────────────────────────
        # OUTIL 2 : search_project
        # Cherche un projet sur le PC par nom
        # Aucun serveur officiel ne fait ça non plus
        # ─────────────────────────────────────
        types.Tool(
            name="search_project",
            description=(
                "Cherche un dossier projet sur le PC par nom ou mot-clé. "
                "Parcourt les disques durs et retourne les chemins trouvés."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Nom ou mot-clé du projet à chercher sur le PC"
                    }
                },
                "required": ["project_name"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:

        if name == "solve_jira_ticket":
            agent_cible = arguments.get("agent", "gemini")
            resultat = traiter_ticket(
                cle_ticket=arguments["ticket_key"],
                agent_cible=agent_cible
            )
            labels = {
                "correction_bug":   "Correction de bug",
                "generation_code":  "Génération de code",
                "analyse_generale": "Analyse générale"
            }
            texte = f"""Résolution du ticket {resultat['ticket']['cle']}

Titre : {resultat['ticket']['titre']}
Intention : {labels.get(resultat['intention_detectee'], resultat['intention_detectee'])}
Agent utilisé : {resultat['agent_utilise'].capitalize()}
Tokens consommés : {resultat['tokens_total']}

---

{resultat['reponse_agent']}
"""
            return [types.TextContent(type="text", text=texte)]

        elif name == "search_project":
            project_name = arguments["project_name"].lower()
            resultats = []

            racines = [
                os.path.expanduser("~"),
                "C:\\",
                "D:\\" if os.path.exists("D:\\") else None,
            ]
            racines = [r for r in racines if r]

            for racine in racines:
                try:
                    for root, dirs, files in os.walk(racine):
                        dirs[:] = [
                            d for d in dirs
                            if d not in [
                                "Windows", "System32", "Program Files",
                                "Program Files (x86)", "AppData", "node_modules",
                                ".git", "__pycache__", "venv", ".venv"
                            ]
                        ]
                        for d in dirs:
                            if project_name in d.lower():
                                resultats.append(os.path.join(root, d))
                                if len(resultats) >= 5:
                                    break
                        if len(resultats) >= 5:
                            break
                except PermissionError:
                    continue

            if not resultats:
                texte = f"Aucun projet trouvé avec le nom '{arguments['project_name']}'."
            else:
                lignes = [f"Projets trouvés pour '{arguments['project_name']}' :"]
                for r in resultats:
                    lignes.append(f"- {r}")
                texte = "\n".join(lignes)

            return [types.TextContent(type="text", text=texte)]

        else:
            return [types.TextContent(
                type="text",
                text=f"Outil inconnu : {name}"
            )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Erreur '{name}' : {str(e)}"
        )]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())