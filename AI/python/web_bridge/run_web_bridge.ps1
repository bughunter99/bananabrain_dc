param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

Set-Location $PSScriptRoot

$venvPython = Join-Path $env:USERPROFILE "Envs\v1\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython manage.py runserver "$BindHost`:$Port" --noreload
    exit $LASTEXITCODE
}

$workon = Get-Command workon -ErrorAction SilentlyContinue
if ($null -ne $workon) {
    workon v1
}

python manage.py runserver "$BindHost`:$Port" --noreload