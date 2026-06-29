@echo off
echo Installation des dependances...
pip install fastapi uvicorn --quiet

echo.
echo Lancement du serveur Monopoly Online...
echo Ouvrez votre navigateur sur : http://localhost:8000
echo Appuyez sur Ctrl+C pour arreter le serveur.
echo.

cd /d "%~dp0"
uvicorn app:app --host 127.0.0.1 --port 8000
pause
