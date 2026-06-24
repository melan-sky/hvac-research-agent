@echo off
set "APP_DIR=%~dp0"
set "PYTHON_EXE=C:\Users\lyx\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)

powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "$app='%APP_DIR%'; $py='%PYTHON_EXE%';" ^
  "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object { $_.CommandLine -like '*simple_web.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue };" ^
  "Start-Process -FilePath $py -ArgumentList 'simple_web.py' -WorkingDirectory $app -WindowStyle Hidden;" ^
  "Start-Sleep -Seconds 2;" ^
  "$edge=(Get-Command msedge.exe -ErrorAction SilentlyContinue).Source;" ^
  "if($edge){ Start-Process -FilePath $edge -ArgumentList '--app=http://127.0.0.1:8501' } else { Start-Process 'http://127.0.0.1:8501' }"
