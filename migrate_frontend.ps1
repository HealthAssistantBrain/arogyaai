$ErrorActionPreference = "Stop"
Write-Host "Migrating Frontend into Apps/Frontend..."

New-Item -ItemType Directory -Force -Path "apps\frontend" | Out-Null

$excludeList = @(
    "apps", "services", "shared", "infra", "docker-compose.yml", 
    "MONOREPO_README.md", "frontend_dockerfile.txt", "ROOT_GITIGNORE", 
    ".git", "scaffold.py", "migrate_frontend.ps1"
)

# Move all root contents (the frontend) into apps/frontend
Get-ChildItem -Path . | Where-Object { $_.Name -notin $excludeList } | ForEach-Object {
    Move-Item -Path $_.FullName -Destination "apps\frontend" -Force
}

# Attach Dockerfile to the frontend
Move-Item -Path "frontend_dockerfile.txt" -Destination "apps\frontend\Dockerfile" -Force

# Rename Monorepo Root Files
Rename-Item -Path "MONOREPO_README.md" -NewName "README.md" -Force
Rename-Item -Path "ROOT_GITIGNORE" -NewName ".gitignore" -Force

Write-Host "Migration Complete! Frontend is safely encapsulated."
Write-Host "You can now run 'docker-compose up --build' to test."
