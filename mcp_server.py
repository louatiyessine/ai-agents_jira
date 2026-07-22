# mcp_server.py
import asyncio
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