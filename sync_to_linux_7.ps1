# Sync YuE2 -> the earlier 7.216.161.45 server. Does not change sync_to_linux.ps1.
#
# Usage:
#   .\sync_to_linux_7.ps1
#   .\sync_to_linux_7.ps1 -Force
#
# Notes:
#   - Requires: git + OpenSSH (both already installed on this Windows box).
#   - The server folder /home/ma-user/work/YuE2 is created on
#     first run and becomes a git repo checked out on branch `main`, so pushed
#     code lands directly at that path (receive.denyCurrentBranch=updateInstead).
#   - Files ignored by .gitignore (audio, outputs, checkpoints, venv...) are NOT
#     pushed; only committed source/config/data text files are synced.
#   - Uncommitted local changes are never synced unless -Commit is given; the
#     script no longer prompts for confirmation.

param(
    [switch]$Force,
    [switch]$Commit,
    [switch]$Confirm
)

$ErrorActionPreference = "Stop"

$RepoDir     = $PSScriptRoot
$SshKey      = "C:/Users/c00871154/.ssh/hk-develop-sh.pem"
$SshPort     = "32138"
$SshUserHost = "ma-user@7.216.161.45"
$RemoteDir   = "/home/ma-user/work/YuE2"
$RemoteUrl   = "ssh://ma-user@7.216.161.45:32138/home/ma-user/work/YuE2"
$RemoteName  = "v100-7"

$env:GIT_SSH_COMMAND = "ssh -i `"$SshKey`" -o StrictHostKeyChecking=no"

function Invoke-Ssh([string]$Command) {
    ssh -i $SshKey -p $SshPort -o StrictHostKeyChecking=no $SshUserHost $Command
    if ($LASTEXITCODE -ne 0) { throw "SSH command failed: $Command" }
}

Set-Location $RepoDir

Write-Host "-> (1/5) Testing SSH connectivity..." -ForegroundColor Cyan
Invoke-Ssh "echo ok > /dev/null"
Write-Host "   SSH OK" -ForegroundColor Green

Write-Host "-> (2/5) Pulling latest from origin (GitHub)..." -ForegroundColor Cyan
git pull
if ($LASTEXITCODE -ne 0) {
    Write-Host "   git pull failed; aborting to avoid pushing stale/conflicting code." -ForegroundColor Red
    throw "git pull failed"
}
Write-Host "   pull OK" -ForegroundColor Green

Write-Host "-> (3/5) Checking uncommitted local changes..." -ForegroundColor Cyan
$Dirty = @(git status --porcelain)
if ($Dirty.Count -gt 0) {
    Write-Host "   Uncommitted changes (will NOT be synced unless -Commit):" -ForegroundColor Yellow
    $Dirty | ForEach-Object { Write-Host "     $_" }
    if ($Commit) {
        if ($Confirm) {
            $ans = Read-Host "   Commit all changes above? [y/N]"
            if ($ans -notmatch '^[yY]') {
                Write-Host "   Skipped commit." -ForegroundColor Yellow
                $Commit = $false
            }
        }
        if ($Commit) {
            git add -A
            if ($LASTEXITCODE -ne 0) { throw "git add failed" }
            git commit -m "sync to linux node $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
            if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
            Write-Host "   Committed." -ForegroundColor Green
        }
    }
} else {
    Write-Host "   Working tree clean." -ForegroundColor Green
}

Write-Host "-> (4/5) Ensuring server repo exists at $RemoteDir ..." -ForegroundColor Cyan
Invoke-Ssh "if [ ! -d '$RemoteDir/.git' ]; then mkdir -p '$RemoteDir' && git -C '$RemoteDir' init -q && git -C '$RemoteDir' symbolic-ref HEAD refs/heads/main && git -C '$RemoteDir' config receive.denyCurrentBranch updateInstead && echo created; else echo exists; fi"

Write-Host "-> (5/5) Setting git remote '$RemoteName' ..." -ForegroundColor Cyan
if (-not (git remote | Select-String "^$RemoteName$")) {
    git remote add $RemoteName $RemoteUrl
} else {
    git remote set-url $RemoteName $RemoteUrl
}

Write-Host "-> Pushing to server (branch: main) ..." -ForegroundColor Cyan
if ($Confirm) {
    $ans = Read-Host "   Push to server? [y/N]"
    if ($ans -notmatch '^[yY]') {
        Write-Host "Aborted by user." -ForegroundColor Yellow
        exit 0
    }
}
if ($Force) {
    git push $RemoteName HEAD:main --force
} else {
    git push $RemoteName HEAD:main
}
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push failed. If the server has local commits that diverge, re-run with:" -ForegroundColor Red
    Write-Host "   .\sync_to_linux_7.ps1 -Force" -ForegroundColor Red
    throw "git push failed"
}

Write-Host "-> Verifying server side..." -ForegroundColor Cyan
Invoke-Ssh "cd '$RemoteDir' && git status --short --branch && echo '---' && ls -1"
Write-Host "Done." -ForegroundColor Green
