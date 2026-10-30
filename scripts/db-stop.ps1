$root = Split-Path $PSScriptRoot -Parent
& "$root\.local\pgsql\bin\pg_ctl.exe" -D "$root\.local\pgdata" stop -m fast
