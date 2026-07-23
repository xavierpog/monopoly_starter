import sys, os

# Garantit que le répertoire du projet est le CWD au moment de l'import de app.py
# (requis pour que StaticFiles trouve le dossier 'static/')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
