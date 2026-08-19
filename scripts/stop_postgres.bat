@echo off
REM Stop PostgreSQL
SET PGHOME=D:\Tools\PostgreSQL\pgsql
SET PATH=%PGHOME%\bin;%PGHOME%\lib;%PATH%
"%PGHOME%\pg_ctl.exe" -D "D:\Tools\PostgreSQL\data" -m fast stop
