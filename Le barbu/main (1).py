#!/usr/bin/env python3
"""
Point d'entrée principal pour le Barbu
Usage:
  python main.py server              # Lancer le serveur
  python main.py client --name Léo   # Lancer un client
"""
import sys
import os

# S'assurer que les imports locaux fonctionnent
sys.path.insert(0, os.path.dirname(__file__))


def run_server():
    from network.server import main
    main()


def run_client():
    from network.client import main
    main()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [server|client] [options]")
        print("  server  --host 0.0.0.0 --port 8765")
        print("  client  --name PSEUDO --host localhost --port 8765")
        sys.exit(1)

    mode = sys.argv[1]
    sys.argv.pop(1)  # Retirer 'server' ou 'client' des args

    if mode == "server":
        run_server()
    elif mode == "client":
        run_client()
    else:
        print(f"Mode inconnu : {mode}")
        sys.exit(1)
