@echo off
REM Start PostgreSQL portable (run this each time before using the project)
SET PGHOME=D:\Tools\PostgreSQL\pgsql
SET PATH=%PGHOME%\bin;%PGHOME%\lib;%PATH%

echo Starting PostgreSQL...
start "" /B "%PGHOME%\postgres.exe" -D "D:\Tools\PostgreSQL\data"
timeout /t 5 /nobreak >nul
"%PGHOME%\pg_isready.exe" -h 127.0.0.1 -p 5432
if %errorlevel%==0 (
    echo PostgreSQL is running on localhost:5432
) else (
    echo PostgreSQL failed to start. Check D:\Tools\PostgreSQL\pg.log
)
