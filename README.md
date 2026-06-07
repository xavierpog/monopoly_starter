# Monopoly Online — Démarrage rapide

## Prérequis
- Python 3.10+
- pip

## Installation

```bash
# 1. Placer les 3 fichiers dans un même dossier :
#    app.py  |  index.html  |  requirements.txt

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer le serveur
uvicorn app:app --reload
```

## Jouer en local

1. Ouvrir **http://localhost:8000** dans votre navigateur
2. Entrez votre nom et un code de salle (ex: `partie1`)
3. Ouvrez un **deuxième onglet** (ou un autre navigateur) et rejoignez la même salle
4. Une fois 2 joueurs connectés, cliquez **Démarrer la partie**

## Commandes en jeu

| Bouton | Action |
|---|---|
| Démarrer | Lance la partie (2 joueurs minimum) |
| Lancer les dés | Déplace votre pion (votre tour uniquement) |
| Acheter | Achète la propriété sur laquelle vous êtes |

## Structure du projet

```
monopoly_starter/
├── app.py          ← Serveur FastAPI + logique de jeu + WebSockets
├── index.html      ← Interface web (plateau, joueurs, chat)
└── requirements.txt

# Prochaines étapes suggérées :
# ├── models/         ← Classes Python (Player, Board, Property, Card...)
# ├── game/           ← Logique séparée du serveur (moteur de jeu pur)
# ├── static/         ← CSS/JS séparés quand le front grossit
# └── tests/          ← Tests unitaires (pytest)
```

## Hébergement gratuit (pas fait encore)

| Service | Usage | Limite gratuite |
|---|---|---|
| **Render** | Backend FastAPI | 750h/mois, mise en veille après 15min d'inactivité |
| **Railway** | Backend + DB | 500h/mois |
| **Fly.io** | Backend toujours actif | 3 VMs partagées |
| **Netlify** | Frontend statique | Illimité |
| **Supabase** | PostgreSQL | 500 MB |
