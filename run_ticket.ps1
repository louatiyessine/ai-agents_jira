param(
    [string]$ticket = "SCRUM-1",
    [string]$agent = "gemini"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$BASE_URL = "http://localhost:5000"

function Invoke-Api {
    param([string]$Uri, [string]$Body)
    try {
        $response = Invoke-WebRequest -Uri $Uri -Method POST -ContentType "application/json" -Body $Body -UseBasicParsing
        return $response.Content | ConvertFrom-Json
    } catch {
        $errorBody = $_.ErrorDetails.Message
        if ($errorBody) {
            try {
                $parsed = $errorBody | ConvertFrom-Json
                Write-Host "Erreur API : $($parsed.erreur)" -ForegroundColor Red
            } catch {
                Write-Host "Erreur API : $errorBody" -ForegroundColor Red
            }
        } else {
            Write-Host "Flask ne repond pas sur $BASE_URL" -ForegroundColor Red
            Write-Host "Lance d'abord : python app.py" -ForegroundColor Yellow
        }
        return $null
    }
}

Write-Host ""
Write-Host "Verification de Flask..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "$BASE_URL" -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "Flask OK" -ForegroundColor Green
} catch {
    Write-Host "Flask ne repond pas. Lance python app.py" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Analyse du ticket $ticket en cours..." -ForegroundColor Cyan

$planBody = "{`"question`": `"Resous le ticket $ticket`", `"agent`": `"$agent`"}"
$result = Invoke-Api -Uri "$BASE_URL/api/mcp/plan" -Body $planBody

if ($null -eq $result) {
    Write-Host "Impossible de recuperer le plan. Arret." -ForegroundColor Red
    exit 1
}

$quotaPattern = "429"
if ($result.plan -match $quotaPattern) {
    Write-Host "Quota Gemini depasse — bascule sur Llama" -ForegroundColor Yellow
    $agent = "llama"
    $planBody2 = "{`"question`": `"Resous le ticket $ticket`", `"agent`": `"llama`"}"
    $result = Invoke-Api -Uri "$BASE_URL/api/mcp/plan" -Body $planBody2
    if ($null -eq $result) {
        Write-Host "Llama aussi indisponible. Arret." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Plan d action :" -ForegroundColor Yellow
Write-Host "-------------------------------------" -ForegroundColor Gray
Write-Host $result.plan
Write-Host "-------------------------------------" -ForegroundColor Gray
Write-Host ""

$confirmation = Read-Host "Accepter et executer ? [y/n]"

if ($confirmation -ne "y") {
    Write-Host "Action annulee." -ForegroundColor Red
    $cancelBody = "{`"confirmation`": `"n`"}"
    Invoke-Api -Uri "$BASE_URL/api/mcp/execute" -Body $cancelBody | Out-Null
    exit 0
}

Write-Host ""
Write-Host "Execution en cours..." -ForegroundColor Cyan

$execBody = "{`"confirmation`": `"y`"}"
$result2 = Invoke-Api -Uri "$BASE_URL/api/mcp/execute" -Body $execBody

if ($null -eq $result2) {
    Write-Host "Erreur lors de l execution." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Resultat :" -ForegroundColor Green
Write-Host "-------------------------------------" -ForegroundColor Gray
Write-Host $result2.reponse
Write-Host "-------------------------------------" -ForegroundColor Gray

Write-Host ""
$pushConfirm = Read-Host "Pousser les changements sur GitHub ? [y/n]"

if ($pushConfirm -ne "y") {
    Write-Host "Changements non pousses." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Recherche du repo Git..." -ForegroundColor Cyan

$projectPath = $null

if ($result2.reponse -match "([A-Z]:\\[^\n]+)") {
    $foundPath = $matches[1].TrimEnd("\", ".", " ")
    $currentPath = $foundPath
    while ($currentPath -and $currentPath -ne (Split-Path $currentPath -Parent)) {
        if (Test-Path (Join-Path $currentPath ".git")) {
            $projectPath = $currentPath
            break
        }
        $currentPath = Split-Path $currentPath -Parent
    }
}

if (-not $projectPath -or -not (Test-Path (Join-Path $projectPath ".git"))) {
    Write-Host "Repo Git non detecte automatiquement." -ForegroundColor Yellow
    $projectPath = Read-Host "Entre le chemin du projet Git"
    if (-not (Test-Path (Join-Path $projectPath ".git"))) {
        Write-Host "Chemin invalide." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Repo Git : $projectPath" -ForegroundColor Green

$commitMsg = Read-Host "Message du commit (Entree pour message automatique)"
if ($commitMsg -eq "") {
    $commitMsg = "fix: resolution du ticket $ticket via agent IA"
}

Write-Host ""
Write-Host "Push en cours..." -ForegroundColor Cyan

$previousLocation = Get-Location
try {
    Set-Location $projectPath
    git add .
    if ($LASTEXITCODE -ne 0) { throw "git add a echoue" }
    Write-Host "git add : OK" -ForegroundColor Green
    git commit -m $commitMsg
    if ($LASTEXITCODE -ne 0) { throw "git commit a echoue" }
    Write-Host "git commit : OK" -ForegroundColor Green
    git push
    if ($LASTEXITCODE -ne 0) { throw "git push a echoue" }
    Write-Host "git push : OK" -ForegroundColor Green
    Write-Host ""
    Write-Host "Changements pousses sur GitHub !" -ForegroundColor Green
} catch {
    Write-Host "Erreur Git : $_" -ForegroundColor Red
} finally {
    Set-Location $previousLocation
}
