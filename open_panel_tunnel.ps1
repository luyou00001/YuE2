# Open the panel tunnel without logging into the server.
# The window stays on this PC. Open http://127.0.0.1:8765
# Stop the tunnel later with: Stop-Process -Id <pid printed below>

$ErrorActionPreference = "Stop"
$SshKey = "C:/Users/c00871154/.ssh/Saxphone.pem"
$SshPort = "34456"
$SshUserHost = "ma-user@10.155.175.163"

$existing = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "127.0.0.1:8765 is already open. Use http://127.0.0.1:8765"
    exit 0
}

$proc = Start-Process -FilePath ssh -WindowStyle Hidden -PassThru -ArgumentList @(
    "-i", $SshKey,
    "-p", $SshPort,
    "-N",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "StrictHostKeyChecking=no",
    "-L", "8765:127.0.0.1:8765",
    $SshUserHost
)
Start-Sleep -Seconds 1
if ($proc.HasExited) {
    throw "SSH tunnel exited immediately. If a previous window is sitting on the server, type exit there first."
}
Write-Host "Tunnel is running in the background, pid $($proc.Id)."
Write-Host "This window is still your PC. Open http://127.0.0.1:8765"
Write-Host "Stop it with: Stop-Process -Id $($proc.Id)"
