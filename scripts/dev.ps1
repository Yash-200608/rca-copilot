# Starts PostgreSQL (if needed), the FastAPI backend and the Vite frontend, each in its own window.
$root = Split-Path $PSScriptRoot -Parent
& "$PSScriptRoot\db-start.ps1"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\frontend'; npm run dev -- --host 127.0.0.1"
"Backend  http://127.0.0.1:8000/docs   Frontend http://127.0.0.1:5173"
