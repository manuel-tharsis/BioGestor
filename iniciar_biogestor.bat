@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -c "import PySide6, biogestor" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias...
    ".venv\Scripts\python.exe" -m pip install -e ".[dev]"
    if errorlevel 1 goto :error
)

echo Abriendo BioGestor...
".venv\Scripts\python.exe" -m biogestor.main
goto :eof

:error
echo.
echo No se pudo iniciar BioGestor.
pause
exit /b 1
