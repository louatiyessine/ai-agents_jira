# Projet de stage — Agents IA TechNova

## En une phrase

Ce projet met en place trois assistants intelligents qui travaillent ensemble : deux d'entre eux peuvent répondre à des questions (l'un en s'appuyant sur les documents internes de l'entreprise, l'autre de façon plus libre), et le troisième sait lire un ticket de suivi de bugs (Jira) pour demander automatiquement aux deux premiers de corriger un problème ou d'écrire du code.

## Pourquoi ce projet existe

Lors d'un stage, on m'a demandé de construire un système où plusieurs intelligences artificielles collaborent, plutôt que d'utiliser une seule IA isolée. L'idée est de se rapprocher de ce qui se fait en entreprise : des services indépendants, chacun avec une responsabilité précise, qui communiquent entre eux de façon sécurisée — plutôt qu'un seul gros programme qui fait tout.

## Vue d'ensemble — les trois agents

| Agent | Rôle | Particularité |
|---|---|---|
| **Agent 1 — Gemini** | Répond aux questions en s'appuyant sur des documents internes de l'entreprise | Utilise un système de recherche documentaire (RAG) pour rester précis et factuel |
| **Agent 2 — Llama** | Répond aux questions de façon plus générale | Tourne entièrement sur l'ordinateur, gratuit et sans connexion internet |
| **Agent 3 — Jira** | Lit un ticket de suivi (bug ou demande de fonctionnalité) et le transmet à l'agent 1 ou 2 | Ne répond jamais lui-même : il prépare le travail pour un autre agent |

```mermaid
flowchart TB
    U[Utilisateur] --> S[Serveur du projet]
    S --> A1[Agent 1 — Gemini<br/>avec documents internes]
    S --> A2[Agent 2 — Llama<br/>sans documents]
    S --> A3[Agent 3 — Jira<br/>lit les tickets]
    A3 -->|envoie une demande| A1
    A3 -->|ou envoie une demande| A2
    A3 -.->|va chercher le ticket| J[(Jira)]
```

## Étape 1 — Un système de recherche documentaire (RAG)

**Le problème de départ** : une intelligence artificielle ne connaît pas les documents internes d'une entreprise. Si on lui demande "combien de jours de congés ai-je ?", elle ne peut pas savoir la réponse propre à TechNova.

**La solution** : avant de répondre, on fait chercher à l'IA les passages pertinents dans les vrais documents de l'entreprise, puis on lui demande de répondre en se basant sur ce qu'elle a trouvé.

```mermaid
flowchart LR
    D[Documents de<br/>l'entreprise] --> C[Découpage en<br/>petits morceaux]
    C --> E[Transformation en<br/>empreintes numériques]
    E --> B[(Base de<br/>recherche)]
    Q[Question posée] --> B
    B --> R[Passages les<br/>plus pertinents]
```

Concrètement, les documents sont coupés en petits morceaux, chaque morceau est transformé en une sorte d'empreinte numérique qui représente son sens, et le tout est stocké dans une base de recherche. Quand une question arrive, elle est transformée en empreinte de la même façon, et on retrouve les morceaux dont l'empreinte est la plus proche — un peu comme retrouver les chansons les plus proches d'un air qu'on fredonne.

## Étape 2 — Agent 1, qui utilise ce système

L'Agent 1 reçoit une question, va chercher le contexte pertinent dans les documents (étape 1), puis demande à Gemini (le modèle d'intelligence artificielle de Google) de répondre en se basant sur ce contexte. On lui a donné une consigne claire : rester fidèle aux documents quand la question s'y rapporte, et répondre normalement sinon, pour éviter qu'il invente des informations.

**Découverte intéressante pendant les tests** : les modèles Gemini récents font un raisonnement interne avant de répondre, invisible dans le texte final mais qui compte dans la consommation et le coût. Il a fallu adapter la mesure pour ne pas sous-estimer le coût réel d'environ 20 à 30 %.

## Étape 3 — Agent 2, sans système de recherche

L'Agent 2 utilise Llama, un modèle qui tourne directement sur l'ordinateur, sans connexion à un service externe payant. Il répond uniquement avec ses connaissances générales, sans accès aux documents de l'entreprise — volontairement, pour pouvoir comparer les deux approches.

**Ce que la comparaison a montré** : sur la question des congés, l'Agent 1 a répondu exactement "21 jours" (la vraie information de l'entreprise), tandis que l'Agent 2 a inventé une réponse générale sur le droit du travail dans plusieurs pays, sans lien avec l'entreprise réelle. L'Agent 1 coûte environ 15 fois plus cher à utiliser, mais cette fiabilité justifie la différence de coût.

## Étape 4 — Faire dialoguer les deux agents

Les deux agents ont aussi été mis en conversation l'un avec l'autre sur plusieurs tours : l'un répond, l'autre réagit à cette réponse, et ainsi de suite. Un résultat marquant : l'Agent 1, fidèle aux documents, a explicitement signalé que l'Agent 2 avait ajouté des informations non vérifiées — une bonne illustration concrète de l'intérêt d'un système de recherche documentaire pour limiter les erreurs.

## Étape 5 — Mesurer et comparer le coût

Un module dédié convertit la consommation de chaque agent en coût réel, en se basant sur les tarifs officiels publiés par Google. Pour l'Agent 2, qui est réellement gratuit, un coût simulé est aussi calculé (comme s'il était hébergé sur un service payant équivalent), pour permettre une comparaison de valeur entre les deux approches plutôt qu'une comparaison "gratuit contre payant" qui n'apporterait pas d'information utile.

## Étape 6 et 7 — Le serveur et l'interface

Un serveur fait le lien entre une interface de discussion (accessible dans un navigateur, avec un thème sombre) et tout le travail des agents. L'interface propose trois façons d'interagir : poser une question à un agent au choix, comparer les deux agents sur la même question, ou les faire dialoguer entre eux. Un bouton permet aussi d'ajouter directement un nouveau document, qui est immédiatement intégré à la base de recherche.

---

## Mission 2 — Donner à chaque agent sa propre API, et créer l'Agent 3 (Jira)

Après une première présentation, deux nouvelles demandes ont été formulées :

1. Que chaque agent dispose de sa propre adresse d'accès indépendante, protégée par une clé secrète, pour pouvoir être utilisé depuis n'importe quel autre projet ou ordinateur.
2. La création d'un troisième agent capable de lire un ticket Jira et de transmettre la bonne instruction à l'un des deux premiers agents.

### Une adresse et une clé pour chaque agent

Chaque agent a maintenant sa propre adresse d'accès, et chaque adresse exige une clé secrète propre à cet agent pour être utilisée — exactement comme il faut une clé pour utiliser les services de Google ou d'OpenAI. Sans la bonne clé, l'accès est refusé.

```mermaid
flowchart LR
    X[Programme externe] -->|requête + clé| R1[Adresse de<br/>l'Agent 1]
    X -->|requête + clé| R2[Adresse de<br/>l'Agent 2]
    R1 -->|clé correcte| OK1[Réponse]
    R1 -->|clé absente ou fausse| KO1[Accès refusé]
```

Ces deux nouvelles adresses ont été testées directement depuis un terminal, sans passer par l'interface graphique, pour prouver qu'un programme totalement extérieur au projet peut utiliser les agents.

### L'Agent 3 — comment il fonctionne

```mermaid
flowchart TB
    T[(Ticket Jira)] --> L[Lecture du ticket<br/>via Jira]
    L --> AN[Analyse du contenu :<br/>bug ou nouvelle fonctionnalité ?]
    AN --> P[Construction d'une<br/>instruction adaptée]
    P -->|avec la bonne clé| C{Quel agent ?}
    C -->|choix 1| A1[Agent 1 — Gemini]
    C -->|choix 2| A2[Agent 2 — Llama]
    A1 --> RE[Réponse : diagnostic,<br/>correction ou code généré]
    A2 --> RE
```

Concrètement, l'Agent 3 va chercher un ticket sur Jira (le titre, la description, le type), comprend s'il décrit un problème à corriger ou une nouvelle fonctionnalité à créer, prépare un message clair pour résumer cette demande, puis l'envoie à l'Agent 1 ou à l'Agent 2 — en utilisant la même clé secrète que n'importe quel autre programme externe utiliserait.

**Deux tickets de test ont validé ce fonctionnement** :
- Un ticket de type bug (mauvais symbole de devise affiché) : l'agent a correctement diagnostiqué le problème et proposé une correction de code.
- Un ticket demandant une nouvelle fonctionnalité (calcul de remise selon l'ancienneté d'un client) : l'agent a généré une vraie fonction de code complète et testée.

### Une remarque importante reçue de l'encadrant, et sa correction

En présentant ce travail, l'encadrant a fait une observation utile sur l'architecture du projet : à l'époque, le serveur principal communiquait de deux façons différentes avec les agents. Avec l'Agent 3 (Jira), il passait toujours par l'adresse sécurisée et la clé — exactement comme un programme externe le ferait. Mais pour les autres fonctionnalités de l'interface (poser une question, comparer, dialoguer), le serveur appelait directement le code interne des agents, sans passer par cette même adresse sécurisée.

```mermaid
flowchart TB
    subgraph Avant["Avant la correction"]
    S1[Serveur] -->|appel direct au code| AG1[Agent 1]
    S1 -->|appel direct au code| AG2[Agent 2]
    end
    subgraph Apres["Après la correction"]
    S2[Serveur] -->|requête + clé, comme tout le monde| AG3[Agent 1]
    S2 -->|requête + clé, comme tout le monde| AG4[Agent 2]
    end
```

**Ce problème a été corrigé.** Toute communication avec un agent, même venant du propre serveur du projet pour ses propres fonctionnalités d'interface, passe désormais par la même règle : une requête avec une adresse et une clé, plutôt qu'un accès direct au code interne. Une fonction centrale unique (`appeler_agent_interne`) a été créée et est utilisée par toutes les fonctionnalités qui doivent consulter un agent, y compris le dialogue entre les deux agents.

**Un piège technique découvert et corrigé au passage** : en appliquant ce principe une première fois, la règle avait été posée trop largement, y compris sur les adresses qui *sont elles-mêmes* la porte d'entrée officielle de chaque agent. Cela créait une boucle sans fin : l'adresse de l'Agent 1 essayait de s'appeler elle-même indéfiniment pour obtenir sa propre réponse, ce qui bloquait complètement le système. La correction a consisté à bien distinguer deux rôles : les fonctionnalités de l'interface (qui doivent passer par l'adresse sécurisée) d'une part, et l'adresse officielle de chaque agent elle-même (qui doit rester le point où le vrai travail s'exécute, sans quoi rien ne pourrait jamais s'exécuter du tout) d'autre part.

Le résultat final répond à la demande initiale tout en évitant ce piège : les agents sont maintenant véritablement indépendants les uns des autres, chacun pourrait être déplacé sur une autre machine sans casser le reste du projet, et une seule règle de sécurité s'applique de façon cohérente partout.

---

## Mission 3 — Amélioration du prompt de l'Agent Jira et intégration du protocole MCP

Après validation de la mission 2, trois nouvelles améliorations ont été apportées au projet.

### Amélioration 1 — Un prompt généré dynamiquement par l'IA elle-même

**Le problème de départ** : le prompt envoyé à l'Agent 1 ou 2 pour traiter un ticket Jira était écrit manuellement dans le code Python. Ce texte fixe ne s'adaptait pas vraiment au contenu du ticket — il appliquait toujours la même formulation, quel que soit le type de tâche décrite.

**La solution apportée** : au lieu d'écrire le prompt dans le code, on demande maintenant à Gemini de le générer lui-même, en analysant le ticket. Ce prompt généré — appelé `promptToDevelopAgent` — est ensuite transmis à l'Agent 1 ou 2 pour traiter la tâche.

```mermaid
flowchart TB
    T[(Ticket Jira)] --> L[Lecture du ticket]
    L --> I[Détection de l'intention :<br/>bug, code, ou analyse ?]
    I --> G[Gemini génère<br/>le promptToDevelopAgent]
    G --> ENV[Envoi du prompt<br/>à l'agent choisi]
    ENV -->|Agent 1| A1[Gemini — réponse structurée]
    ENV -->|Agent 2| A2[Llama — réponse structurée]
```

Ce fonctionnement en deux temps — un premier appel pour générer le prompt, un second pour exécuter la tâche — est plus flexible : le prompt s'adapte automatiquement à chaque ticket, qu'il décrive un bug, une nouvelle fonctionnalité, ou n'importe quel autre type de tâche.

**La structure de réponse imposée** : selon l'intention détectée, le prompt généré demande à l'agent une réponse organisée en sections précises.

Pour un bug :
- Diagnostic : cause probable du problème
- Solution proposée : correction avec exemple de code
- Points d'attention : effets de bord et tests à effectuer
- Critères de validation : conditions qui confirment que le bug est résolu

Pour une nouvelle fonctionnalité :
- Compréhension du besoin : reformulation de la demande
- Approche technique : stratégie d'implémentation choisie
- Code généré : code complet, propre et commenté
- Intégration : comment intégrer la solution dans le projet existant

Pour une analyse générale :
- Résumé du ticket : ce qui est demandé en termes clairs
- Analyse technique : enjeux, dépendances et risques
- Plan d'action : étapes concrètes et priorisées
- Recommandations : conseils basés sur les meilleures pratiques

**Deux tickets ont validé ce fonctionnement** :
- SCRUM-1 (bug d'affichage de devise) : l'agent a produit un diagnostic complet, deux options de correction avec code JSX, les points d'attention et les critères de validation.
- SCRUM-2 (nouvelle fonctionnalité de calcul de remise) : l'agent a généré une fonction Python complète avec docstring, gestion des erreurs, exemples d'utilisation et cas limites.

### Amélioration 2 — Intégration du protocole MCP

**Ce qu'est MCP** : le Model Context Protocol est un standard ouvert qui permet à un outil d'intelligence artificielle (comme Claude Desktop ou Cursor) d'appeler des fonctions extérieures de façon structurée. Un programme qui expose ses fonctions via MCP devient utilisable depuis n'importe quel client compatible, sans avoir à créer une intégration spécifique à chaque fois.

**Ce qui a été ajouté** : le projet expose maintenant ses fonctionnalités Jira via MCP, sous forme de cinq outils accessibles depuis l'extérieur — dont un outil de recherche de projet sur le PC.

```mermaid
flowchart TB
    CLI[Client MCP<br/>Claude Desktop / Cursor] -->|appelle un outil| SRV[Serveur MCP<br/>mcp_server.py]
    SRV --> O1[read_jira_ticket<br/>lit le contenu d'un ticket]
    SRV --> O2[analyze_jira_ticket<br/>détecte l'intention]
    SRV --> O3[solve_jira_ticket<br/>pipeline complet]
    SRV --> O4[list_jira_tickets<br/>liste les tickets d'un projet]
    SRV --> O5[search_project<br/>cherche un projet sur le PC]
    O3 --> AG[Agent 1 ou Agent 2]
    AG --> RE[Réponse structurée]
```

| Outil MCP | Ce qu'il fait |
|---|---|
| `read_jira_ticket` | Lit un ticket et retourne son titre, description, type et statut |
| `analyze_jira_ticket` | Détecte l'intention du ticket sans appeler un agent IA |
| `solve_jira_ticket` | Pipeline complet : lecture, génération du prompt, réponse de l'agent |
| `list_jira_tickets` | Liste les tickets récents d'un projet Jira |
| `search_project` | Cherche un dossier projet sur le PC par nom ou mot-clé |

### Amélioration 3 — Un client MCP intégré au projet

En plus d'exposer ses fonctions via MCP, le projet intègre aussi un client MCP : une nouvelle route du serveur (`/api/mcp/chat`) permet de poser une question en langage naturel, et c'est l'agent lui-même qui décide quel outil utiliser pour y répondre.

```mermaid
flowchart TB
    U[Utilisateur écrit :<br/>Résous le ticket SCRUM-1] --> FL[Serveur Flask<br/>route /api/mcp/chat]
    FL --> MC[Client MCP<br/>mcp_client.py]
    MC --> LT[Liste des outils<br/>disponibles envoyée au LLM]
    LT --> LLM[Gemini ou Llama<br/>choisit l'outil adapté]
    LLM -->|décide d'utiliser solve_jira_ticket| SRV[Serveur MCP<br/>mcp_server.py]
    SRV --> AG[Agent 1 ou Agent 2]
    AG --> RES[Réponse finale<br/>retournée à l'utilisateur]
```

Concrètement, quand l'utilisateur écrit "Résous le ticket SCRUM-1", le LLM reçoit la liste des outils disponibles, réfléchit à lequel utiliser, demande l'exécution de `solve_jira_ticket`, reçoit le résultat, puis formule une réponse finale. L'utilisateur n'a pas besoin de connaître les outils — il écrit simplement sa demande en langage naturel.

**Ce que ce fonctionnement change concrètement** : le projet peut maintenant être utilisé de deux façons indépendantes — via l'interface graphique comme avant, ou via n'importe quel client MCP compatible, sans modifier une seule ligne du code existant.

```mermaid
flowchart LR
    subgraph Interface["Via l'interface habituelle"]
    UI[Interface HTML] --> FL[Flask<br/>routes existantes]
    end
    subgraph MCP["Via un client MCP"]
    CD[Claude Desktop<br/>ou Cursor] --> MS[mcp_server.py]
    end
    FL --> AG[Agents]
    MS --> AG
```

Les deux modes coexistent dans le même projet, partagent les mêmes agents, et n'interfèrent pas l'un avec l'autre.

---

## Mission 4 — L'agent agit vraiment sur les fichiers du PC

Jusqu'ici, quand un ticket demandait de créer ou corriger du code, l'agent répondait avec une explication et le code à appliquer — mais c'était au développeur de copier-coller lui-même. Cette mission ajoute la capacité à l'agent d'agir directement sur les fichiers du projet concerné.

### Ce qui a changé

L'agent ne se contente plus de répondre avec du texte. Il va maintenant chercher le projet sur le PC, lit les fichiers concernés, crée ou modifie les fichiers nécessaires, et explique ce qu'il a fait — tout ça automatiquement, en une seule commande.

```mermaid
flowchart TB
    T[(Ticket Jira)] --> MC[Client MCP<br/>mcp_client.py]
    MC --> LLM[Gemini ou Llama<br/>reçoit tous les outils disponibles]
    LLM --> D{Quelle action ?}
    D -->|chercher le projet| SP[search_project<br/>parcourt le PC par nom]
    D -->|lire un fichier| RF[fs : read_file<br/>lit le contenu]
    D -->|créer un fichier| CF[fs : write_file<br/>crée le fichier avec le code]
    D -->|modifier un fichier| MF[fs : edit_file<br/>corrige le code existant]
    SP --> LLM
    RF --> LLM
    CF --> RES[Fichier créé sur le PC]
    MF --> RES2[Fichier modifié sur le PC]
    LLM --> EXP[Explication de ce qui a été fait<br/>retournée à l'utilisateur]
```

### Deux serveurs MCP en parallèle

Pour donner à l'agent accès à la fois aux tickets Jira et aux fichiers du PC, le client MCP connecte maintenant deux serveurs en même temps. L'agent reçoit tous les outils des deux serveurs et choisit lui-même lesquels utiliser selon la tâche.

```mermaid
flowchart LR
    MC[Client MCP<br/>mcp_client.py] --> S1[Serveur 1<br/>mcp_server.py<br/>outils Jira + search_project]
    MC --> S2[Serveur 2<br/>MCP Filesystem<br/>read, write, edit fichiers]
    S1 -->|outils jira__| LLM[Gemini ou Llama]
    S2 -->|outils fs__| LLM
    LLM --> PC[Fichiers du PC]
```

Les outils du serveur Jira sont préfixés `jira__` et ceux du serveur filesystem sont préfixés `fs__` — ce qui permet à l'agent de savoir sur quel serveur appeler chaque outil, sans confusion.

### Un exemple concret — ticket SCRUM-3

Le ticket demandait d'ajouter un système de logging au projet CASS TSYP13. Voici exactement ce que l'agent a fait automatiquement, sans aucune intervention manuelle :

```mermaid
flowchart TB
    T[SCRUM-3 : Ajouter un logging<br/>au projet CASS TSYP13] --> ST1[jira__solve_jira_ticket<br/>lit et analyse le ticket]
    ST1 --> ST2[jira__search_project<br/>trouve CASS TSYP13 sur le PC]
    ST2 --> ST3[fs__write_file<br/>crée logger.py avec le code]
    ST3 --> ST4[fs__list_directory<br/>vérifie la structure du projet]
    ST4 --> ST5[fs__read_text_file<br/>lit server.py pour comprendre le code]
    ST5 --> ST6[fs__edit_file<br/>modifie server.py pour intégrer le logger]
    ST6 --> OK[Fichiers créés et modifiés sur le PC]
```

L'agent a non seulement créé le fichier demandé, mais a aussi modifié le fichier existant pour intégrer la nouvelle fonctionnalité — exactement comme un développeur le ferait.

### Un système de confirmation avant action

Pour éviter que l'agent modifie des fichiers sans que le développeur ne le sache, un système de confirmation a été ajouté — inspiré du bouton "Accept" de GitHub Copilot. Avant d'exécuter quoi que ce soit, l'agent affiche son plan d'action complet et attend une réponse.

```mermaid
flowchart TB
    CMD[run_ticket.ps1 -ticket SCRUM-4] --> PLAN[Etape 1 : recuperer le plan<br/>route /api/mcp/plan]
    PLAN --> AFF[Affichage du plan dans le terminal :<br/>ce que l'agent va faire et pourquoi]
    AFF --> CONF{Accepter et executer ? y/n}
    CONF -->|y| EXEC[Etape 2 : execution<br/>route /api/mcp/execute]
    CONF -->|n| ANN[Action annulee — aucun fichier touche]
    EXEC --> PUSH{Pousser sur GitHub ? y/n}
    PUSH -->|y| GIT[git add + commit + push<br/>dans le repo du projet modifie]
    PUSH -->|n| FIN[Termine]
    GIT --> FIN
```

Concrètement, le développeur lance une seule commande dans le terminal, lit le plan affiché, tape `y` pour accepter ou `n` pour refuser, puis confirme ou non le push sur GitHub. Tout le reste est géré automatiquement.

### Le push GitHub automatique

Après chaque exécution acceptée, le script propose de pousser les changements sur GitHub. Si le développeur accepte, le script trouve automatiquement le repo Git du projet modifié, propose un message de commit ou en génère un automatiquement, puis exécute `git add`, `git commit` et `git push` — directement dans le repo du projet modifié, pas dans le repo du projet de stage.

```mermaid
flowchart LR
    EXEC[Fichiers modifies sur le PC] --> FIND[Script trouve le repo Git<br/>du projet modifie]
    FIND --> MSG[Message de commit<br/>automatique ou personnalise]
    MSG --> GIT1[git add .]
    GIT1 --> GIT2[git commit -m message]
    GIT2 --> GIT3[git push]
    GIT3 --> GH[(GitHub<br/>repo du projet)]
```

---

## Limites connues à ce stade

- L'accès aux agents depuis un autre ordinateur du même réseau fonctionne. L'accès depuis un téléphone connecté au même réseau Wi-Fi ne fonctionne pas encore, probablement à cause d'un réglage du routeur qui isole les appareils entre eux pour des raisons de sécurité — un point indépendant du projet lui-même, encore en cours d'investigation.
- Le tarif simulé utilisé pour comparer le coût de l'Agent 2 (gratuit en réalité) à un service payant équivalent est une estimation, pas un tarif officiel vérifié.
- La détection de l'intention d'un ticket Jira (bug ou nouvelle fonctionnalité) repose sur une recherche de mots-clés simples, pas sur un modèle d'intelligence artificielle dédié à cette tâche — un choix volontaire pour rester rapide et facile à expliquer.
- Le serveur tourne actuellement en mode développement, adapté à une démonstration mais pas à un usage en production avec de nombreux utilisateurs.
- La génération du `promptToDevelopAgent` consomme un appel supplémentaire à l'API Gemini avant chaque traitement de ticket — ce qui double le nombre d'appels pour cette fonctionnalité et augmente légèrement le coût et le temps de réponse.
- L'API Gemini gratuite est limitée à 20 requêtes par jour — au-delà de cette limite, le système retourne une erreur 429. Pour un usage intensif, un abonnement payant ou l'utilisation de l'Agent 2 (Llama, gratuit et sans limite) est recommandé.
- La recherche de projet sur le PC (`search_project`) parcourt le disque dur entier, ce qui peut prendre quelques secondes sur les machines avec beaucoup de fichiers. Les dossiers système sont ignorés pour accélérer la recherche.
