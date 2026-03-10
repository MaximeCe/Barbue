# 🃏 Le Barbu — Jeu de cartes multijoueur en ligne

Jeu de cartes **Le Barbu** en Python, jouable à 4 joueurs en réseau local ou sur Internet via WebSockets.

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Lancer une partie

### 1. Le serveur (une seule personne le lance)

```bash
python main.py server
# ou avec options :
python main.py server --host 0.0.0.0 --port 8765
```

Le serveur tourne sur le port **8765** par défaut.  
Les autres joueurs ont besoin de l'**IP** de la machine qui héberge le serveur.

### 2. Chaque joueur lance son client

```bash
python main.py client --name Léo
# ou en se connectant à un serveur distant :
python main.py client --name Léo --host 192.168.1.42 --port 8765
```

La partie démarre **automatiquement** quand les 4 joueurs sont connectés.

---

## Règles du Barbu

### Principe général (manches 1 à 6)
- 52 cartes distribuées équitablement (13 par joueur)
- Le premier joueur (aléatoire) joue une carte d'une couleur
- Les autres **doivent jouer la même couleur** s'ils en ont, sinon ils se défaussent
- Le joueur avec **la carte la plus haute de la couleur demandée** remporte le pli
- Le gagnant du pli joue en premier au suivant
- **Tous les points sont négatifs** — on cherche à en avoir le moins possible

### Manches

| # | Nom | Règle |
|---|-----|-------|
| 1 | Les Plis | Chaque pli remporté = **5 pts** |
| 2 | Les Cœurs | Chaque carte ♥ dans un pli remporté = **5 pts** |
| 3 | Les Reines | Chaque reine dans un pli remporté = **25 pts** |
| 4 | Le Roi de Pique | Remporter le K♠ = **50 pts** |
| 5 | Les Derniers Plis | Avant-dernier pli = **20 pts**, Dernier pli = **30 pts** |
| 6 | La Salade | Toutes les règles précédentes en même temps ! |
| 7 | La Réussite | Voir ci-dessous |

### La Réussite (manche 7)
- Chaque joueur joue à tour de rôle
- On pose une carte uniquement si elle est **adjacente à une carte déjà posée de la même couleur**
- Les **7** sont posés en premier pour chaque couleur
- On peut placer un **6** ou un **8** à côté d'un 7, un 5 à côté d'un 6, etc.
- Si on joue un **Roi**, on peut **rejouer**
- Si on ne peut pas jouer, on **passe son tour**
- Ordre de fin : 1er = **-200 pts**, 2e = **-100 pts**, 3e = **-50 pts**, 4e = **0 pts**

---

## Structure du projet

```
barbu/
├── main.py               # Point d'entrée
├── requirements.txt
├── game/
│   ├── cards.py          # Cartes, couleurs, valeurs
│   ├── rounds.py         # Règles des manches, Réussite
│   └── engine.py         # Machine à états du jeu
└── network/
    ├── server.py         # Serveur WebSocket
    └── client.py         # Client terminal
```
