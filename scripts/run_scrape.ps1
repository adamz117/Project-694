# Wrapper used by the "Project694-Steps" scheduled task: runs the scraper and appends to logs\scrape.log
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force logs | Out-Null
"[$(Get-Date -Format s)] run" | Add-Content logs\scrape.log
py scripts\scrape_profile.py 2>&1 | ForEach-Object { "$_" } | Add-Content logs\scrape.log
