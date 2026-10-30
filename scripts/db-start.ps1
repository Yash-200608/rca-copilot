$root = Split-Path $PSScriptRoot -Parent
& "$root\.local\pgsql\bin\pg_ctl.exe" -D "$root\.local\pgdata" -l "$root\.local\pg.log" status
if ($LASTEXITCODE -ne 0) { Start-Process "$root\.local\pgsql\bin\pg_ctl.exe" -ArgumentList "-D `"$root\.local\pgdata`" -l `"$root\.local\pg.log`" start" -WindowStyle Hidden; Start-Sleep 4 }
"Postgres on 127.0.0.1:5433"
