# run_ticket.ps1
param(
    [string]$ticket = "SCRUM-3",
    [string]$agent = "gemini"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "Analyse du ticket $ticket en cours..." -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────
# Etape 1 : recuperer le plan
# ─────────────────────────────────────
$body = "{`"question`": `"Resous le ticket $ticket`", `"agent`": `"$agent`"}"

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/api/mcp/plan" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -UseBasicParsing
    $plan = ($response.Content | ConvertFrom-Json).plan
} catch {
    Write-Host "Erreur lors de la recuperation du plan." -ForegroundColor Red
    exit
}

Write-Host "Plan d'action :" -ForegroundColor Yellow
Write-Host "-------------------------------------" -ForegroundColor Gray
Write-Host $plan
Write-Host "-------------------------------------" -ForegroundColor Gray
Write-Host ""

# ─────────────────────────────────────
# Etape 2 : confirmation execution
# ─────────────────────────────────────
$confirmation = Read-Host "Accepter et executer ? [y/n]"

if ($confirmation -ne "y") {
    Write-Host ""
    Write-Host "Action annulee." -ForegroundColor Red
    $body2 = '{"confirmation": "n"}'
    Invoke-WebRequest -Uri "http://localhost:5000/api/mcp/execute" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body2 `
        -UseBasicParsing | Out-Null
    exit
}

# ─────────────────────────────────────
# Etape 3 : execution
# ─────────────────────────────────────
Write-Host ""
Write-Host "Execution en cours..." -ForegroundColor Cyan

try {
    $body2 = '{"confirmation": "y"}'
    $response2 = Invoke-WebRequest -Uri "http://localhost:5000/api/mcp/execute" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body2 `
        -UseBasicParsing

    $resultat = ($response2.Content | ConvertFrom-Json).reponse
    Write-Host ""
    Write-Host "Resultat :" -ForegroundColor Green
    Write-Host "-------------------------------------" -ForegroundColor Gray
    Write-Host $resultat
    Write-Host "-------------------------------------" -ForegroundColor Gray

} catch {
    Write-Host "Erreur lors de l'execution." -ForegroundColor Red
    exit
}

# ─────────────────────────────────────
# Etape 4 : proposition push GitHub
# On cherche le repo Git du projet modifie
# ─────────────────────────────────────
Write-Host ""
$pushConfirm = Read-Host "Pousser les changements sur GitHub ? [y/n]"

if ($pushConfirm -ne "y") {
    Write-Host ""
    Write-Host "Changements non pousses sur GitHub." -ForegroundColor Yellow
    exit
}

# ─────────────────────────────────────
# Etape 5 : trouver le dossier Git
# On demande a Flask quel projet a ete modifie
# ─────────────────────────────────────
Write-Host ""
Write-Host "Recherche du projet Git modifie..." -ForegroundColor Cyan

# Recuperer le chemin du projet depuis la reponse de l'agent
# On cherche un chemin dans le resultat retourne
$projectPath = $null

if ($resultat -match "C:\\[^\n`"]+") {
    $projectPath = $matches[0].TrimEnd('\', '.', ' ')
    
    # Remonter jusqu'au dossier racine du projet (qui contient .git)
    $currentPath = $projectPath
    while ($currentPath -ne "" -and $currentPath -ne $null) {
        if (Test-Path (Join-Path $currentPath ".git")) {
            $projectPath = $currentPath
            break
        }
        $parent = Split-Path $currentPath -Parent
        if ($parent -eq $currentPath) { break }
        $currentPath = $parent
    }
}

if ($projectPath -eq $null -or -not (Test-Path (Join-Path $projectPath ".git"))) {
    Write-Host ""
    Write-Host "Aucun repo Git trouve automatiquement." -ForegroundColor Yellow
    $projectPath = Read-Host "Entre le chemin du projet Git manuellement"
}

Write-Host "Repo Git trouve : $projectPath" -ForegroundColor Green

# ─────────────────────────────────────
# Etape 6 : git add + commit + push
# ─────────────────────────────────────
Write-Host ""
$commitMsg = Read-Host "Message du commit (Entree pour message automatique)"

if ($commitMsg -eq "") {
    $commitMsg = "fix: resolution du ticket $ticket via agent IA"
}

Write-Host ""
Write-Host "Push en cours..." -ForegroundColor Cyan

try {
    Set-Location $projectPath

    git add .
    Write-Host "git add . : OK" -ForegroundColor Green

    git commit -m $commitMsg
    Write-Host "git commit : OK" -ForegroundColor Green

    git push
    Write-Host "git push : OK" -ForegroundColor Green

    Write-Host ""
    Write-Host "Changements pousses sur GitHub avec succes !" -ForegroundColor Green
    Write-Host "Commit : $commitMsg" -ForegroundColor Gray

} catch {
    Write-Host "Erreur Git : $_" -ForegroundColor Red
}