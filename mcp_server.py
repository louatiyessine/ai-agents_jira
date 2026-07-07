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
        # ─────────────────────────────────────
# OUTIL 5 : search_project
# Cherche un dossier projet sur tout le PC
# selon un nom ou mot-clé
# ─────────────────────────────────────
types.Tool(
    name="search_project",
    description="Cherche un dossier projet sur le PC selon un nom ou mot-clé. Retourne les chemins trouvés.",
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

# ─────────────────────────────────────
# OUTIL 6 : list_project_files
# Liste tous les fichiers d'un projet
# pour que l'agent comprenne sa structure
# ─────────────────────────────────────
types.Tool(
    name="list_project_files",
    description="Liste tous les fichiers d'un dossier projet pour comprendre sa structure.",
    inputSchema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Chemin absolu du dossier projet"
            }
        },
        "required": ["project_path"]
    }
),

# ─────────────────────────────────────
# OUTIL 7 : read_file
# Lit le contenu d'un fichier existant
# pour comprendre le code avant de le modifier
# ─────────────────────────────────────
types.Tool(
    name="read_file",
    description="Lit le contenu d'un fichier existant dans un projet.",
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Chemin absolu du fichier à lire"
            }
        },
        "required": ["file_path"]
    }
),

# ─────────────────────────────────────
# OUTIL 8 : create_file
# Crée un nouveau fichier avec du contenu
# dans le projet trouvé
# ─────────────────────────────────────
types.Tool(
    name="create_file",
    description="Crée un nouveau fichier avec du contenu dans un projet sur le PC.",
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Chemin absolu complet du fichier à créer"
            },
            "content": {
                "type": "string",
                "description": "Contenu à écrire dans le fichier"
            }
        },
        "required": ["file_path", "content"]
    }
),

# ─────────────────────────────────────
# OUTIL 9 : modify_file
# Modifie un fichier existant
# pour corriger un bug ou ajouter du code
# ─────────────────────────────────────
types.Tool(
    name="modify_file",
    description="Modifie le contenu d'un fichier existant dans un projet (correction de bug, ajout de code).",
    inputSchema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Chemin absolu du fichier à modifier"
            },
            "new_content": {
                "type": "string",
                "description": "Nouveau contenu complet du fichier"
            },
            "reason": {
                "type": "string",
                "description": "Explication de ce qui a été modifié et pourquoi"
            }
        },
        "required": ["file_path", "new_content", "reason"]
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

        # ─────────────────────────────────────
        # Exécution OUTIL 5 : search_project
        # ─────────────────────────────────────
        elif name == "search_project":
            import os
            project_name = arguments["project_name"].lower()
            resultats = []

            # Dossiers racines à explorer sur Windows
            racines = [
                os.path.expanduser("~"),  # C:\Users\Admin
                "C:\\",
                "D:\\" if os.path.exists("D:\\") else None,
            ]
            racines = [r for r in racines if r]

            for racine in racines:
                try:
                    for root, dirs, files in os.walk(racine):
                        # Ignorer les dossiers système pour aller plus vite
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
                                chemin_complet = os.path.join(root, d)
                                resultats.append(chemin_complet)
                                if len(resultats) >= 5:  # Max 5 résultats
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

        # ─────────────────────────────────────
        # Exécution OUTIL 6 : list_project_files
        # ─────────────────────────────────────
        elif name == "list_project_files":
            import os
            project_path = arguments["project_path"]

            if not os.path.exists(project_path):
                return [types.TextContent(
                    type="text",
                    text=f"Dossier introuvable : {project_path}"
                )]

            lignes = [f"Structure du projet : {project_path}\n"]
            for root, dirs, files in os.walk(project_path):
                # Ignorer les dossiers inutiles
                dirs[:] = [
                    d for d in dirs
                    if d not in ["node_modules", ".git", "__pycache__", "venv", ".venv"]
                ]
                niveau = root.replace(project_path, "").count(os.sep)
                indent = "    " * niveau
                lignes.append(f"{indent}{os.path.basename(root)}/")
                sous_indent = "    " * (niveau + 1)
                for f in files:
                    lignes.append(f"{sous_indent}{f}")

            return [types.TextContent(type="text", text="\n".join(lignes))]

        # ─────────────────────────────────────
        # Exécution OUTIL 7 : read_file
        # ─────────────────────────────────────
        elif name == "read_file":
            import os
            file_path = arguments["file_path"]

            if not os.path.exists(file_path):
                return [types.TextContent(
                    type="text",
                    text=f"Fichier introuvable : {file_path}"
                )]

            with open(file_path, "r", encoding="utf-8") as f:
                contenu = f.read()

            texte = f"Contenu de {file_path} :\n\n{contenu}"
            return [types.TextContent(type="text", text=texte)]

        # ─────────────────────────────────────
        # Exécution OUTIL 8 : create_file
        # ─────────────────────────────────────
        elif name == "create_file":
            import os
            file_path = arguments["file_path"]
            content = arguments["content"]

            # Créer les dossiers parents si nécessaires
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            texte = f"Fichier créé avec succès : {file_path}"
            return [types.TextContent(type="text", text=texte)]

        # ─────────────────────────────────────
        # Exécution OUTIL 9 : modify_file
        # ─────────────────────────────────────
        elif name == "modify_file":
            import os
            file_path = arguments["file_path"]
            new_content = arguments["new_content"]
            reason = arguments["reason"]

            if not os.path.exists(file_path):
                return [types.TextContent(
                    type="text",
                    text=f"Fichier introuvable : {file_path}"
                )]

            # Sauvegarder l'ancienne version avant modification
            with open(file_path, "r", encoding="utf-8") as f:
                ancien_contenu = f.read()

            backup_path = file_path + ".backup"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(ancien_contenu)

            # Écrire le nouveau contenu
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            texte = f"""Fichier modifié avec succès : {file_path}
Backup sauvegardé : {backup_path}

Raison de la modification :
{reason}"""
            return [types.TextContent(type="text", text=texte)]

        # ─────────────────────────────────────
        # Outil inconnu
        # ─────────────────────────────────────
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