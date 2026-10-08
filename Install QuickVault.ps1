$ErrorActionPreference = 'Stop'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\QuickVault'
$source = Join-Path $PSScriptRoot 'dist\QuickVault.exe'
if (-not (Test-Path -LiteralPath $source)) { throw 'Build QuickVault.exe before installing.' }
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -LiteralPath $source -Destination (Join-Path $installDir 'QuickVault.exe') -Force
$shell = New-Object -ComObject WScript.Shell
$shortcutDirs = @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))
foreach ($shortcutDir in $shortcutDirs) {
    $link = $shell.CreateShortcut((Join-Path $shortcutDir 'QuickVault.lnk'))
    $link.TargetPath = Join-Path $installDir 'QuickVault.exe'
    $link.WorkingDirectory = $installDir
    $link.IconLocation = (Join-Path $installDir 'QuickVault.exe') + ',0'
    $link.Description = 'Quick notes and encrypted secrets'
    $link.Save()
}
Write-Host "QuickVault installed in $installDir. Desktop and Start menu shortcuts created."
