"""
Serveur WebSocket pour le Barbu multijoueur
"""
import asyncio
import json
import logging
from typing import Optional
import websockets
from websockets.server import WebSocketServerProtocol

from game import BarbuGame, GamePhase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SERVER] %(message)s")
logger = logging.getLogger(__name__)


class BarbuServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.game = BarbuGame()
        # player_name -> websocket
        self.connections: dict[str, WebSocketServerProtocol] = {}

    async def handler(self, websocket: WebSocketServerProtocol):
        player_name = None
        try:
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await self._send(websocket, {"type": "error", "message": "JSON invalide."})
                    continue

                action = msg.get("action")
                logger.info(f"Action reçue : {action} | joueur={msg.get('player')}")

                # --- Connexion ---
                if action == "join":
                    name = msg.get("name", "").strip()
                    if not name:
                        await self._send(websocket, {"type": "error", "message": "Nom invalide."})
                        continue
                    ok, info = self.game.add_player(name)
                    if ok:
                        player_name = name
                        self.connections[name] = websocket
                        await self._send(websocket, {"type": "joined", "message": info, "name": name})
                        await self._broadcast_state()
                        # Démarrer automatiquement quand 4 joueurs
                        if self.game.can_start():
                            self.game.start_game()
                            await self._broadcast_state()
                    else:
                        await self._send(websocket, {"type": "error", "message": info})

                # --- Confirmer début de manche ---
                elif action == "ack_round":
                    if player_name:
                        ok, info = self.game.acknowledge_round_start(player_name)
                        if ok:
                            await self._broadcast_state()
                        else:
                            await self._send(websocket, {"type": "error", "message": info})

                # --- Jouer une carte (plis) ---
                elif action == "play_card":
                    if player_name:
                        card = msg.get("card")
                        ok, info = self.game.play_card(player_name, card)
                        if ok:
                            await self._broadcast_state(info)
                        else:
                            await self._send(websocket, {"type": "error", "message": info})

                # --- Confirmer résultat du pli ---
                elif action == "ack_trick":
                    if player_name:
                        ok, info = self.game.acknowledge_trick(player_name)
                        if ok:
                            await self._broadcast_state()
                        else:
                            await self._send(websocket, {"type": "error", "message": info})

                # --- Réussite : poser une carte ---
                elif action == "play_reussite":
                    if player_name:
                        card = msg.get("card")
                        ok, info = self.game.play_reussite(player_name, card)
                        if ok:
                            await self._broadcast_state(info)
                        else:
                            await self._send(websocket, {"type": "error", "message": info})

                # --- Réussite : passer ---
                elif action == "pass_reussite":
                    if player_name:
                        ok, info = self.game.pass_reussite(player_name)
                        if ok:
                            await self._broadcast_state(info)
                        else:
                            await self._send(websocket, {"type": "error", "message": info})

                # --- Passer à la manche suivante ---
                elif action == "next_round":
                    if player_name:
                        ok, info = self.game.next_round()
                        if ok:
                            await self._broadcast_state(info)
                        else:
                            await self._send(websocket, {"type": "error", "message": info})

                else:
                    await self._send(websocket, {"type": "error", "message": f"Action inconnue: {action}"})

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if player_name and player_name in self.connections:
                del self.connections[player_name]
                logger.info(f"{player_name} s'est déconnecté.")

    async def _send(self, ws: WebSocketServerProtocol, data: dict):
        try:
            await ws.send(json.dumps(data))
        except Exception:
            pass

    async def _broadcast_state(self, message: str = ""):
        """Envoie l'état personnalisé à chaque joueur connecté."""
        for player_name, ws in list(self.connections.items()):
            view = self.game.state.get_player_view(player_name)
            payload = {
                "type": "state",
                "state": view,
                "message": message,
            }
            await self._send(ws, payload)

    async def run(self):
        logger.info(f"Serveur Barbu démarré sur ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # run forever


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Serveur Barbu")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = BarbuServer(host=args.host, port=args.port)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
