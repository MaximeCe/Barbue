# Le Barbu — Docker

Jeu de cartes multijoueur (4 joueurs), réseau local WiFi.

## Prérequis
- Docker + Docker Compose
- Linux avec serveur X11 (ou XQuartz sur Mac)

---

## Test local (1 machine, 4 fenêtres)

```bash
# Build
docker compose build

# Lancer le serveur
docker compose up server

# Dans 4 terminaux séparés (un par joueur)
PLAYER_NAME=Alice   docker compose --profile local run --rm client1
PLAYER_NAME=Bob     docker compose --profile local run --rm client2
PLAYER_NAME=Claire  docker compose --profile local run --rm client3
PLAYER_NAME=David   docker compose --profile local run --rm client4
```

---

## Vrai réseau LAN (joueurs sur machines séparées)

**Sur la machine hôte :**
```bash
docker compose build
docker compose up server
```

**Sur chaque machine cliente :**
```bash
# Build l'image client
docker compose build

# Lancer (le pseudo peut aussi être saisi dans le lobby)
./run_client.sh MonPseudo
```

> **Note :** `--network host` est requis pour que le scan UDP broadcast fonctionne.  
> Si ton système refuse (ex: Docker Desktop sur Mac), utilise la saisie IP manuelle dans le lobby.

---

## Ports utilisés

| Port | Protocole | Usage |
|------|-----------|-------|
| 8765 | TCP (WS)  | Jeu WebSocket |
| 8766 | UDP       | Découverte automatique LAN |

---

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `PLAYER_NAME` | *(vide)* | Pseudo prérempli dans le lobby |
| `GAME_NAME` | `Partie de Barbu` | Nom affiché dans la découverte réseau |
| `PORT` | `8765` | Port WebSocket (serveur) |
