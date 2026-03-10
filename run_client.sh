#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# run_client.sh  –  Lance le client Barbu sur ta machine (réseau LAN réel)
#
# Usage :
#   ./run_client.sh                        # pseudo saisi dans le lobby
#   ./run_client.sh MonPseudo              # pseudo prédéfini
# ─────────────────────────────────────────────────────────────────────────────

PSEUDO="${1:-}"

# Autoriser les connexions X11 locales
xhost +local:docker 2>/dev/null

docker run --rm -it \
  --network host \
  -e DISPLAY="$DISPLAY" \
  -e PLAYER_NAME="$PSEUDO" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  barbu-docker-client1   # nom de l'image buildée par docker-compose
