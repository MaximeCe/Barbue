"""
Client terminal pour le Barbu - interface joueur
"""
import asyncio
import json
import sys
import os
import threading
from typing import Optional
import websockets

# ---- Couleurs ANSI ----
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SUIT_COLORS = {
    "HEARTS": RED,
    "DIAMONDS": RED,
    "CLUBS": WHITE,
    "SPADES": WHITE,
}


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def color_card(card_dict: dict) -> str:
    if card_dict.get("hidden"):
        return f"{DIM}[??]{RESET}"
    suit = card_dict.get("suit", "")
    rank = card_dict.get("rank", "")
    from game.cards import Rank, Suit
    rank_obj = Rank[rank]
    suit_obj = Suit[suit]
    col = SUIT_COLORS.get(suit, WHITE)
    return f"{col}{BOLD}{rank_obj.symbol}{suit_obj.value}{RESET}"


def render_hand(hand: list[dict], playable: list[dict] = None) -> str:
    parts = []
    for i, c in enumerate(hand):
        card_str = color_card(c)
        if playable is not None:
            if c in playable:
                parts.append(f"[{CYAN}{BOLD}{i+1}{RESET}]{card_str}")
            else:
                parts.append(f"[{DIM}{i+1}{RESET}]{DIM}{color_card(c)}{RESET}")
        else:
            parts.append(f"[{i+1}]{card_str}")
    return "  ".join(parts)


def render_scores(scores: dict, players: list) -> str:
    lines = [f"{BOLD}{CYAN}━━━ Scores ━━━{RESET}"]
    sorted_players = sorted(players, key=lambda p: scores.get(p, 0))
    for p in sorted_players:
        pts = scores.get(p, 0)
        col = GREEN if pts == min(scores.values()) else WHITE
        lines.append(f"  {col}{p:15s} {pts:>6} pts{RESET}")
    return "\n".join(lines)


def render_reussite_board(board: dict) -> str:
    from game.cards import Suit, Rank
    lines = [f"{BOLD}{CYAN}━━━ Plateau Réussite ━━━{RESET}"]
    suits = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
    ranks_order = [r for r in Rank]

    for suit in suits:
        placed = set(board["placed"].get(suit.name, []))
        seven_placed = board["sevens_placed"].get(suit.name, False)
        col = SUIT_COLORS[suit.name]
        row = f"  {col}{suit.value}{RESET} "
        for rank in ranks_order:
            v = rank.numeric_value
            if v in placed:
                row += f"{col}{BOLD}{rank.symbol}{RESET} "
            else:
                row += f"{DIM}·{RESET} "
        lines.append(row)
    return "\n".join(lines)


def render_trick(trick: list[dict]) -> str:
    if not trick:
        return f"  {DIM}(aucune carte jouée){RESET}"
    parts = []
    for entry in trick:
        card_str = color_card(entry["card"])
        parts.append(f"{entry['player']}: {card_str}")
    return "  " + "  |  ".join(parts)


class BarbuClient:
    def __init__(self, host: str, port: int, player_name: str):
        self.uri = f"ws://{host}:{port}"
        self.player_name = player_name
        self.state: Optional[dict] = None
        self.last_message: str = ""
        self.last_error: str = ""
        self.websocket = None
        self.running = True

    async def connect(self):
        async with websockets.connect(self.uri) as ws:
            self.websocket = ws
            # Rejoindre
            await ws.send(json.dumps({"action": "join", "name": self.player_name}))
            # Boucle de réception
            async for raw in ws:
                msg = json.loads(raw)
                await self._handle_message(msg)
                if not self.running:
                    break

    async def _handle_message(self, msg: dict):
        mtype = msg.get("type")
        if mtype == "error":
            self.last_error = msg.get("message", "")
            self._render()
        elif mtype in ("state", "joined"):
            self.state = msg.get("state")
            self.last_message = msg.get("message", "")
            self.last_error = ""
            self._render()
            # Déclencher l'input utilisateur
            await self._handle_input()

    def _render(self):
        clear()
        if not self.state:
            print(f"{CYAN}{BOLD}=== LE BARBU ==={RESET}")
            print(f"En attente de connexion...")
            return

        s = self.state
        phase = s.get("phase", "")
        players = s.get("players", [])
        scores = s.get("scores", {})

        print(f"{CYAN}{BOLD}╔══════════════════════════════════════════╗")
        print(f"║              LE BARBU 🃏                  ║")
        print(f"╚══════════════════════════════════════════╝{RESET}")
        print()

        if self.last_error:
            print(f"{RED}⚠ {self.last_error}{RESET}\n")
        if self.last_message:
            print(f"{YELLOW}ℹ {self.last_message}{RESET}\n")

        print(f"Joueurs connectés : {', '.join(players) or '(aucun)'}\n")

        if phase == "waiting":
            print(f"{YELLOW}En attente de 4 joueurs... ({len(players)}/4){RESET}")
            return

        if phase in ("round_start", "trick", "trick_result", "reussite", "round_end", "game_end"):
            round_num = s.get("current_round", "?")
            round_name = s.get("round_name", "")
            round_desc = s.get("round_description", "")
            print(f"{BOLD}{MAGENTA}═══ Manche {round_num} : {round_name} ═══{RESET}")
            print(f"  {DIM}{round_desc}{RESET}\n")

        if phase == "round_start":
            print(f"{YELLOW}La manche va commencer. Appuie sur Entrée pour confirmer...{RESET}")
            return

        # Plateau réussite
        if phase == "reussite" and s.get("reussite_board"):
            print(render_reussite_board(s["reussite_board"]))
            print()

        # Pli en cours
        if phase in ("trick", "trick_result"):
            print(f"{BOLD}Pli {s.get('trick_number', 0) + 1}/{s.get('total_tricks', 13)}{RESET}")
            trick = s.get("current_trick", [])
            print("Cartes jouées :")
            print(render_trick(trick))
            print()
            if s.get("last_trick_winner") and phase == "trick_result":
                print(f"{GREEN}{BOLD}→ {s['last_trick_winner']} remporte le pli ! (+{s['last_trick_points']} pts){RESET}")
                print()

        # Ma main
        my_hand = s.get("hands", {}).get(self.player_name, [])
        if my_hand and not any(c.get("hidden") for c in my_hand):
            print(f"{BOLD}Tes cartes :{RESET}")
            print(render_hand(my_hand))
            print()

        # Scores
        print(render_scores(scores, players))

        if phase == "round_end":
            round_scores = s.get("round_scores", {})
            print(f"\n{BOLD}{CYAN}Scores de cette manche :{RESET}")
            for p, pts in sorted(round_scores.items(), key=lambda x: x[1]):
                print(f"  {p:15s} {pts:>6} pts")

        if phase == "game_end":
            winner = min(scores, key=lambda p: scores[p]) if scores else "?"
            print(f"\n{GREEN}{BOLD}🏆 FIN DE PARTIE ! Gagnant : {winner} 🏆{RESET}")

    async def _handle_input(self):
        if not self.state:
            return

        s = self.state
        phase = s.get("phase", "")
        my_name = self.player_name
        current_player = s.get("current_player")

        # Début de manche → tous confirment
        if phase == "round_start":
            input(f"\n{YELLOW}Appuie sur Entrée pour commencer...{RESET}")
            await self.websocket.send(json.dumps({"action": "ack_round", "player": my_name}))
            return

        # Résultat du pli → confirmer (seul le joueur courant)
        if phase == "trick_result" and current_player == my_name:
            input(f"\n{YELLOW}Appuie sur Entrée pour continuer...{RESET}")
            await self.websocket.send(json.dumps({"action": "ack_trick", "player": my_name}))
            return

        # Jouer une carte
        if phase == "trick" and current_player == my_name:
            my_hand = s.get("hands", {}).get(my_name, [])
            await self._input_play_card(my_hand)
            return

        # Réussite
        if phase == "reussite":
            reussite_player = s.get("players", [])[s.get("reussite_turn_idx", 0)]
            if reussite_player == my_name:
                my_hand = s.get("hands", {}).get(my_name, [])
                await self._input_reussite(my_hand, s.get("reussite_board"))
            return

        # Fin de manche
        if phase == "round_end" and current_player == my_name or phase == "round_end":
            # Premier joueur décide
            if s.get("players", [None])[0] == my_name:
                input(f"\n{YELLOW}Appuie sur Entrée pour la manche suivante...{RESET}")
                await self.websocket.send(json.dumps({"action": "next_round", "player": my_name}))
            else:
                print(f"\n{DIM}En attente que {s['players'][0]} lance la prochaine manche...{RESET}")
            return

    async def _input_play_card(self, hand: list[dict]):
        print(f"\n{BOLD}{GREEN}C'est ton tour ! Choisis une carte :{RESET}")
        print(render_hand(hand))
        while True:
            try:
                raw = input(f"\nNuméro de carte (1-{len(hand)}) : ").strip()
                idx = int(raw) - 1
                if 0 <= idx < len(hand):
                    await self.websocket.send(json.dumps({
                        "action": "play_card",
                        "player": self.player_name,
                        "card": hand[idx],
                    }))
                    return
                print(f"{RED}Numéro invalide.{RESET}")
            except (ValueError, KeyboardInterrupt):
                print(f"{RED}Entrée invalide.{RESET}")

    async def _input_reussite(self, hand: list[dict], board: dict):
        from game.cards import Card
        from game.rounds import ReussiteBoard
        board_obj = ReussiteBoard.from_dict(board)
        hand_cards = [Card.from_dict(c) for c in hand]
        playable = board_obj.get_playable_cards(hand_cards)
        playable_dicts = [c.to_dict() for c in playable]

        if not playable:
            print(f"\n{YELLOW}Aucune carte jouable. Appuie sur Entrée pour passer...{RESET}")
            input()
            await self.websocket.send(json.dumps({"action": "pass_reussite", "player": self.player_name}))
            return

        print(f"\n{BOLD}{GREEN}C'est ton tour (Réussite) ! Cartes jouables en {CYAN}bleu{RESET}{BOLD} :{RESET}")
        print(render_hand(hand, playable_dicts))
        while True:
            try:
                raw = input(f"\nNuméro de carte (1-{len(hand)}) : ").strip()
                idx = int(raw) - 1
                if 0 <= idx < len(hand):
                    card = hand[idx]
                    if card in playable_dicts:
                        await self.websocket.send(json.dumps({
                            "action": "play_reussite",
                            "player": self.player_name,
                            "card": card,
                        }))
                        return
                    print(f"{RED}Cette carte n'est pas jouable.{RESET}")
                else:
                    print(f"{RED}Numéro invalide.{RESET}")
            except (ValueError, KeyboardInterrupt):
                print(f"{RED}Entrée invalide.{RESET}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Client Barbu")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--name", required=True, help="Ton prénom/pseudo")
    args = parser.parse_args()

    client = BarbuClient(host=args.host, port=args.port, player_name=args.name)
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Déconnexion.{RESET}")


if __name__ == "__main__":
    main()
