# Watch the current branch and run sync_to_linux.ps1 when it moves.
#
# Usage (leave this window open):
#   .\watch_sync_to_linux.ps1
#
# Every 10 seconds it fetches the upstream of the branch checked out in this
# clone. A new local commit or a new upstream commit runs .\sync_to_linux.ps1
# once. While nothing has moved, the status stays on one line and the clock
# updates in place. Ctrl+C stops the loop. sync_to_linux.ps1 is not modified.
# Uncommitted files are not treated as a change, because sync_to_linux.ps1
# only pushes commits unless you pass -Commit yourself.

param(
    [int]$IntervalSeconds = 10
)

$ErrorActionPreference = "Continue"
$env:GIT_TERMINAL_PROMPT = "0"

$RepoDir = $PSScriptRoot
$SyncScript = Join-Path $RepoDir "sync_to_linux.ps1"
$StateFile = Join-Path $RepoDir ".git/watch_sync_to_linux_sha"
$LockFile = Join-Path $RepoDir ".git/watch_sync_to_linux.lock"

$script:QuietLine = $false

function End-QuietLine {
    if ($script:QuietLine) {
        Write-Host ""
        $script:QuietLine = $false
    }
}

function Write-Stamp([string]$Message, [string]$Color = "Gray") {
    End-QuietLine
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$stamp] $Message" -ForegroundColor $Color
}

function Write-Quiet([string]$Message) {
    $stamp = Get-Date -Format "HH:mm:ss"
    $text = "[$stamp] $Message"
    if ($text.Length -lt 72) { $text = $text.PadRight(72) }
    Write-Host "`r$text" -NoNewline -ForegroundColor DarkGray
    $script:QuietLine = $true
}

function Short-Sha([string]$Sha) {
    if (-not $Sha) { return "-" }
    if ($Sha.Length -le 7) { return $Sha }
    return $Sha.Substring(0, 7)
}

function Read-State {
    if (-not (Test-Path $StateFile)) { return "" }
    return (Get-Content -Path $StateFile -TotalCount 1).Trim()
}

function Write-State([string]$Sha) {
    Set-Content -Path $StateFile -Value $Sha -Encoding ascii -NoNewline
}

if (-not (Test-Path $SyncScript)) {
    throw "missing $SyncScript"
}

Set-Location $RepoDir

if (Test-Path $LockFile) {
    $oldPidText = (Get-Content -Path $LockFile -TotalCount 1).Trim()
    $oldPid = 0
    if ([int]::TryParse($oldPidText, [ref]$oldPid)) {
        $alive = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($alive) {
            Write-Stamp "already running (pid $oldPid). Leave that window open." "Yellow"
            exit 1
        }
    }
}
Set-Content -Path $LockFile -Value $PID -Encoding ascii

try {
    $branchName = (git rev-parse --abbrev-ref HEAD).Trim()
    $warnedNoUpstream = $false
    Write-Stamp "watching $branchName every ${IntervalSeconds}s. Ctrl+C to stop." "Cyan"

    while ($true) {
        try {
            $upstream = ""
            git rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                $upstream = (git rev-parse --abbrev-ref --symbolic-full-name "@{upstream}").Trim()
            }

            $remoteSha = ""
            if ($upstream -match "^([^/]+)/(.+)$") {
                $remoteName = $Matches[1]
                $remoteBranch = $Matches[2]
                git fetch $remoteName $remoteBranch --quiet
                if ($LASTEXITCODE -ne 0) {
                    Write-Stamp "fetch $upstream failed; will retry" "Yellow"
                    Start-Sleep -Seconds $IntervalSeconds
                    continue
                }
                $remoteSha = (git rev-parse $upstream).Trim()
            } elseif (-not $warnedNoUpstream) {
                $warnedNoUpstream = $true
                Write-Stamp "this branch has no upstream; watching local HEAD only" "Yellow"
            }

            $head = (git rev-parse HEAD).Trim()
            if ($LASTEXITCODE -ne 0 -or -not $head) {
                Write-Stamp "cannot read HEAD; will retry" "Yellow"
                Start-Sleep -Seconds $IntervalSeconds
                continue
            }

            $last = Read-State
            # Upstream behind this clone is not a new change. Pull would add nothing,
            # and treating it as dirty would run the sync script every interval.
            $remoteMoved = $false
            if ($remoteSha -and $remoteSha -ne $head) {
                git merge-base --is-ancestor $remoteSha $head 1>$null 2>$null
                if ($LASTEXITCODE -ne 0) { $remoteMoved = $true }
            }
            $changed = ($head -ne $last) -or $remoteMoved
            if (-not $changed) {
                Write-Quiet "no change ($(Short-Sha $head))"
                Start-Sleep -Seconds $IntervalSeconds
                continue
            }

            Write-Stamp "change detected local=$(Short-Sha $head) upstream=$(Short-Sha $remoteSha); running sync_to_linux.ps1" "Cyan"
            & $SyncScript
            if ($LASTEXITCODE -ne 0) {
                throw "sync_to_linux.ps1 exited $LASTEXITCODE"
            }
            $synced = (git rev-parse HEAD).Trim()
            Write-State $synced
            Write-Stamp "synced $(Short-Sha $synced). Server has this commit on main." "Green"
        } catch {
            Write-Stamp "sync failed: $($_.Exception.Message); will retry" "Red"
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    End-QuietLine
    if (Test-Path $LockFile) {
        $owner = (Get-Content -Path $LockFile -TotalCount 1).Trim()
        if ($owner -eq "$PID") {
            Remove-Item -Path $LockFile -ErrorAction SilentlyContinue
        }
    }
}
