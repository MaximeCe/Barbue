"""
ui/app.py — Point d'entrée du client Barbu (Docker).

Architecture :
  - Thread principal  : tkinter (lobby → game window)
  - Thread asyncio    : WebSocket client (+ serveur si hôte)
  - Communication     : deux queue.Queue thread-safe
"""
import sys
import os
import tkinter as tk
import threading
import asyncio
import queue
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
logger = logging.getLogger("barbu.app")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


# ────────────────────────────────────────────────────────────────────────────
#  Thread réseau
# ────────────────────────────────────────────────────────────────────────────

class NetworkThread(threading.Thread):
    """Thread asyncio dédié : serveur optionnel + client WebSocket."""

    def __init__(self, host: str, port: int, player_name: str,
                 is_host: bool, game_name: str,
                 in_q: queue.Queue, out_q: queue.Queue):
        super().__init__(daemon=True, name="BarbuNetwork")
        self.host = host
        self.port = port
        self.player_name = player_name
        self.is_host = is_host
        self.game_name = game_name
        self.in_q  = in_q    # serveur → UI
        self.out_q = out_q   # UI → serveur

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._main())
        except Exception as e:
            logger.error(f"NetworkThread : {e}", exc_info=True)
            self.in_q.put({"type": "disconnected"})
        finally:
            loop.close()

    async def _main(self):
        if self.is_host:
            asyncio.create_task(self._run_server())
            await asyncio.sleep(0.6)     # attendre que le serveur démarre

        connect_to = "127.0.0.1" if self.is_host else self.host
        await self._run_client(connect_to, self.port)

    async def _run_server(self):
        from network.server import BarbuServer
        from network.discovery import ServerBeacon
        beacon = ServerBeacon(ws_port=self.port, server_name=self.game_name)
        beacon.start()
        server = BarbuServer(host="0.0.0.0", port=self.port)
        logger.info(f"Serveur démarré port {self.port} – beacon UDP actif")
        await server.run(game_name=self.game_name, beacon=False)   # beacon déjà lancé

    async def _run_client(self, host: str, port: int):
        import websockets
        uri = f"ws://{host}:{port}"
        for attempt in range(12):
            try:
                async with websockets.connect(uri, open_timeout=3) as ws:
                    logger.info(f"Connecté à {uri}")
                    await ws.send(json.dumps({
                        "action": "join",
                        "name": self.player_name,
                    }))
                    recv = asyncio.create_task(self._recv(ws))
                    send = asyncio.create_task(self._send(ws))
                    done, pending = await asyncio.wait(
                        [recv, send], return_when=asyncio.FIRST_COMPLETED)
                    for t in pending:
                        t.cancel()
                    return
            except (OSError, Exception) as e:
                logger.warning(f"Connexion échouée ({attempt+1}/12) : {e}")
                await asyncio.sleep(0.6)

        logger.error("Impossible de se connecter au serveur")
        self.in_q.put({"type": "disconnected"})

    async def _recv(self, ws):
        import websockets
        try:
            async for raw in ws:
                try:
                    self.in_q.put(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            self.in_q.put({"type": "disconnected"})

    async def _send(self, ws):
        import websockets
        while True:
            try:
                msg = self.out_q.get_nowait()
                await ws.send(json.dumps(msg))
            except queue.Empty:
                await asyncio.sleep(0.04)
            except websockets.exceptions.ConnectionClosed:
                break


# ────────────────────────────────────────────────────────────────────────────
#  Application Tkinter
# ────────────────────────────────────────────────────────────────────────────

class BarbuApp:
    def __init__(self):
        self.root = tk.Tk()
        self._show_lobby()

    def _show_lobby(self):
        from ui.lobby import LobbyWindow
        for w in self.root.winfo_children():
            w.destroy()
        self.root.withdraw()
        LobbyWindow(self.root, on_ready=self._on_ready)
        self.root.deiconify()
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.mainloop()

    def _on_ready(self, host: str, port: int, player_name: str,
                   is_host: bool, game_name: str = "Partie de Barbu"):
        for w in self.root.winfo_children():
            w.destroy()

        in_q:  queue.Queue = queue.Queue()
        out_q: queue.Queue = queue.Queue()

        NetworkThread(
            host=host, port=port,
            player_name=player_name,
            is_host=is_host,
            game_name=game_name,
            in_q=in_q, out_q=out_q,
        ).start()

        from ui.game_window import GameWindow
        GameWindow(
            root=self.root,
            player_name=player_name,
            in_queue=in_q,
            send=out_q.put,
        )
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)


def main():
    BarbuApp()


if __name__ == "__main__":
    main()
