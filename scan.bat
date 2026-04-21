@echo off
setlocal

if not exist "venv\Scripts\python.exe" (
  echo Virtualenv not found at venv\Scripts\python.exe
  exit /b 1
)

venv\Scripts\python.exe -m scripts.full_scan
exit /b %errorlevel%
