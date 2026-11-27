# Sync YuE2 -> Linux server via git-over-SSH (incremental).
#
# Usage:
#   .\sync_to_linux.ps1                  pull from GitHub + push to Linux (default: skip commit, NO prompts)
#   .\sync_to_linux.ps1 -Commit          also auto add-all + commit local uncommitted changes first (NO prompts)
#   .\sync_to_linux.ps1 -Commit -Confirm ask y/N before committing and before pushing
#   .\sync_to_linux.ps1 -Force           force push (overwrite server-side divergence)
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
$SshKey      = "C:/Users/c00871154/.ssh/Saxphone.pem"
$SshPort     = "34456"
$SshUserHost = "ma-user@10.155.175.163"
$RemoteDir   = "/home/ma-user/work/YuE2"
$RemoteUrl   = "ssh://ma-user@10.155.175.163:34456/home/ma-user/work/YuE2"
$RemoteName  = "rl-node"

$env:GIT_SSH_COMMAND = "ssh -i `"$SshKey`" -o StrictHostKeyChecking=no"

function Invoke-Ssh([string]$Command) {
    ssh -i $SshKey -p $SshPort -o StrictHostKeyChecking=no $SshUserHost $Command
    if ($LASTEXITCODE -ne 0) { throw "SSH command failed: $Command" }
}

function Get-RemoteHead {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = ssh -i $SshKey -p $SshPort -o StrictHostKeyChecking=no $SshUserHost "git -C '$RemoteDir' rev-parse --verify HEAD"
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) { return "" }
    return ("$output").Trim()
}

function Show-UpdatedFiles([string]$Before, [string]$After) {
    $emptyTree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    $fromLabel = $(if ($Before) { $Before.Substring(0, [Math]::Min(7, $Before.Length)) } else { "none" })
    $toLabel = $After.Substring(0, [Math]::Min(7, $After.Length))
    Write-Host "-> 此次伺服器更新：$fromLabel -> $toLabel" -ForegroundColor Cyan
    if ($Before -eq $After) {
        Write-Host "   此次沒有更新任何文件" -ForegroundColor Yellow
        return
    }
    $base = $(if ($Before) { $Before } else { $emptyTree })
    $changed = @(git --no-pager diff --name-status --find-renames $base $After)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   無法和伺服器舊版本比較，改列最新一次提交的文件：" -ForegroundColor Yellow
        $changed = @(git --no-pager show --name-status --pretty=format: -1 $After)
    }
    $changed = @($changed | Where-Object { $_ -and $_.ToString().Trim() })
    if ($changed.Count -eq 0) {
        Write-Host "   此次沒有更新任何文件" -ForegroundColor Yellow
        return
    }
    Write-Host "   此次更新的文件 ($($changed.Count))：" -ForegroundColor Green
    $changed | ForEach-Object { Write-Host "   $_" }
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

$RemoteBefore = Get-RemoteHead

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
    Write-Host "   .\sync_to_linux.ps1 -Force" -ForegroundColor Red
    throw "git push failed"
}

Write-Host "-> Verifying server side..." -ForegroundColor Cyan
Invoke-Ssh "cd '$RemoteDir' && git status --short --branch && echo '---' && ls -1"
$LocalHead = (git rev-parse HEAD).Trim()
Show-UpdatedFiles $RemoteBefore $LocalHead
Write-Host "Done." -ForegroundColor Green
