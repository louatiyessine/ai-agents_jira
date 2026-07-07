# mcp_server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from agents.agent_jira import (
    lire_ticket,
    analyser_intention,
    construire_prompt,
    traiter_ticket
)

server = Server("technova-jira")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [

        # ─────────────────────────────────────
        # OUTIL 1 : read_jira_ticket
        # Lit le ticket et retourne ses infos brutes
        # Utile pour juste consulter un ticket sans l'analyser
        # ─────────────────────────────────────
        types.Tool(
            name="read_jira_ticket",
            description="Lit un ticket Jira et retourne son titre, description, type et statut.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_key": {
                        "type": "string",
                        "description": "La clé du ticket Jira, ex: SCRUM-1"
                    }
                },
                "required": ["ticket_key"]
            }
        ),

        # ─────────────────────────────────────
        # OUTIL 2 : analyze_jira_ticket
        # Détecte l'intention sans appeler un agent IA
        # Utile pour un pré-diagnostic rapide
        # ─────────────────────────────────────
        types.Tool(
            name="analyze_jira_ticket",
            description="Lit un ticket Jira et détecte automatiquement son intention : correction_bug, generation_code, ou analyse_generale.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_key": {
                        "type": "string",
                        "description": "La clé du ticket Jira, ex: SCRUM-1"
                    }
                },
                "required": ["ticket_key"]
            }
        ),

        # ─────────────────────────────────────
        # OUTIL 3 : solve_jira_ticket
        # Pipeline complet : lecture + analyse + réponse IA structurée
        # C'est l'outil principal, celui qu'on utilisera le plus
        # ─────────────────────────────────────
        types.Tool(
            name="solve_jira_ticket",
            description=(
                "Pipeline complet sur un ticket Jira : lit le ticket, détecte l'intention, "
                "et génère une réponse structurée d'ingénieur senior via Gemini ou Llama."
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
                        "description": "L'agent IA à utiliser : 'gemini' (défaut) ou 'llama'",
                        "enum": ["gemini", "llama"],
                        "default": "gemini"
                    }
                },
                "required": ["ticket_key"]
            }
        ),

        # ─────────────────────────────────────
        # OUTIL 4 : list_jira_tickets
        # Liste les tickets d'un projet Jira
        # Utile pour avoir une vue d'ensemble avant de traiter
        # ─────────────────────────────────────
        types.Tool(
            name="list_jira_tickets",
            description="Liste les tickets récents d'un projet Jira (ex: SCRUM).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "La clé du projet Jira, ex: SCRUM"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Nombre maximum de tickets à retourner (défaut: 10)",
                        "default": 10
                    }
                },
                "required": ["project_key"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    try:

        # ─────────────────────────────────────
        # Exécution OUTIL 1 : read_jira_ticket
        # ─────────────────────────────────────
        if name == "read_jira_ticket":
            ticket = lire_ticket(arguments["ticket_key"])
            texte = f"""## Ticket {ticket['cle']}

**Titre** : {ticket['titre']}
**Type** : {ticket['type']}
**Statut** : {ticket['statut']}

**Description** :
{ticket['description']}
"""
            return [types.TextContent(type="text", text=texte)]

        # ─────────────────────────────────────
        # Exécution OUTIL 2 : analyze_jira_ticket
        # ─────────────────────────────────────
        elif name == "analyze_jira_ticket":
            ticket = lire_ticket(arguments["ticket_key"])
            intention = analyser_intention(ticket)

            # Traduction lisible de l'intention
            labels = {
                "correction_bug":   " Correction de bug",
                "generation_code":  " Génération de code / nouvelle feature",
                "analyse_generale": " Analyse générale"
            }

            texte = f"""## Analyse du ticket {ticket['cle']}

**Titre** : {ticket['titre']}
**Intention détectée** : {labels.get(intention, intention)}

> Le ticket sera traité avec le prompt "ingénieur senior" adapté à cette intention.
> Utilise l'outil `solve_jira_ticket` pour obtenir la réponse complète.
"""
            return [types.TextContent(type="text", text=texte)]

        # ─────────────────────────────────────
        # Exécution OUTIL 3 : solve_jira_ticket
        # ─────────────────────────────────────
        elif name == "solve_jira_ticket":
            agent_cible = arguments.get("agent", "gemini")
            resultat = traiter_ticket(
                cle_ticket=arguments["ticket_key"],
                agent_cible=agent_cible
            )

            labels = {
                "correction_bug":   " Correction de bug",
                "generation_code":  " Génération de code",
                "analyse_generale": " Analyse générale"
            }

            texte = f"""## Résolution du ticket {resultat['ticket']['cle']}

**Titre** : {resultat['ticket']['titre']}
**Intention** : {labels.get(resultat['intention_detectee'], resultat['intention_detectee'])}
**Agent utilisé** : {resultat['agent_utilise'].capitalize()}
**Tokens consommés** : {resultat['tokens_total']}

---

{resultat['reponse_agent']}
"""
            return [types.TextContent(type="text", text=texte)]

        # ─────────────────────────────────────
        # Exécution OUTIL 4 : list_jira_tickets
        # ─────────────────────────────────────
        elif name == "list_jira_tickets":
            import os, requests
            from requests.auth import HTTPBasicAuth

            project_key = arguments["project_key"]
            max_results = arguments.get("max_results", 10)

            url = f"https://{os.getenv('JIRA_DOMAIN')}/rest/api/3/search"
            params = {
                "jql": f"project={project_key} ORDER BY created DESC",
                "maxResults": max_results,
                "fields": "summary,status,issuetype,assignee"
            }

            reponse = requests.get(
                url,
                auth=HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN")),
                headers={"Accept": "application/json"},
                params=params
            )

            if reponse.status_code != 200:
                raise ValueError(f"Erreur Jira API : {reponse.status_code}")

            tickets = reponse.json().get("issues", [])

            if not tickets:
                return [types.TextContent(type="text", text=f"Aucun ticket trouvé dans le projet {project_key}.")]

            lignes = [f"## Tickets du projet {project_key}\n"]
            for t in tickets:
                cle     = t["key"]
                titre   = t["fields"]["summary"]
                statut  = t["fields"]["status"]["name"]
                type_t  = t["fields"]["issuetype"]["name"]
                lignes.append(f"- **{cle}** [{type_t} — {statut}] : {titre}")

            return [types.TextContent(type="text", text="\n".join(lignes))]

        else:
            return [types.TextContent(type="text", text=f"Outil inconnu : {name}")]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Erreur '{name}' : {str(e)}")]


# ─────────────────────────────────────
# POINT D'ENTRÉE — lance le serveur MCP
# Flask (app.py) se lance séparément,
# les deux coexistent sans conflit
# ─────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())