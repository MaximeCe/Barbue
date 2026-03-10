"""
État du jeu et machine à états pour le Barbu
"""
import random
from typing import Optional
from .cards import Card, Suit, Rank, create_deck, deal_cards
from .rounds import (
    RoundType, ReussiteBoard,
    calculate_trick_points, determine_trick_winner,
    ROUND_NAMES, ROUND_DESCRIPTIONS,
)


class GamePhase:
    WAITING = "waiting"           # En attente de joueurs
    ROUND_START = "round_start"   # Début de manche, affichage règles
    PLAYING_TRICK = "trick"       # En cours de pli
    TRICK_RESULT = "trick_result" # Résultat du pli
    REUSSITE = "reussite"         # Phase réussite
    ROUND_END = "round_end"       # Fin de manche, scores
    GAME_END = "game_end"         # Fin de partie


class GameState:
    def __init__(self):
        self.players: list[str] = []          # noms des joueurs
        self.scores: dict[str, int] = {}      # scores totaux
        self.phase: str = GamePhase.WAITING

        self.current_round: int = 0           # 1-7
        self.round_type: Optional[RoundType] = None
        self.hands: dict[str, list[dict]] = {}  # cartes en main (sérialisées)

        # Pli en cours
        self.current_trick: list[dict] = []   # [{player, card}]
        self.lead_suit: Optional[str] = None
        self.current_player_idx: int = 0
        self.trick_number: int = 0
        self.total_tricks: int = 0
        self.round_scores: dict[str, int] = {}  # scores de la manche en cours

        # Réussite
        self.reussite_board: Optional[dict] = None
        self.reussite_turn_idx: int = 0
        self.reussite_finished_order: list[str] = []

        # Résultat du dernier pli (pour affichage)
        self.last_trick_winner: Optional[str] = None
        self.last_trick_points: int = 0

    def to_dict(self) -> dict:
        return {
            "players": self.players,
            "scores": self.scores,
            "phase": self.phase,
            "current_round": self.current_round,
            "round_type": self.round_type.value if self.round_type else None,
            "round_name": ROUND_NAMES.get(self.round_type, "") if self.round_type else "",
            "round_description": ROUND_DESCRIPTIONS.get(self.round_type, "") if self.round_type else "",
            "hands": self.hands,
            "current_trick": self.current_trick,
            "lead_suit": self.lead_suit,
            "current_player_idx": self.current_player_idx,
            "current_player": self.players[self.current_player_idx] if self.players else None,
            "trick_number": self.trick_number,
            "total_tricks": self.total_tricks,
            "round_scores": self.round_scores,
            "reussite_board": self.reussite_board,
            "reussite_turn_idx": self.reussite_turn_idx,
            "reussite_finished_order": self.reussite_finished_order,
            "last_trick_winner": self.last_trick_winner,
            "last_trick_points": self.last_trick_points,
        }

    def get_player_view(self, player_name: str) -> dict:
        """Retourne l'état du jeu du point de vue d'un joueur (cache les mains adverses)."""
        state = self.to_dict()
        # Masquer les mains des autres joueurs
        filtered_hands = {}
        for p, hand in state["hands"].items():
            if p == player_name:
                filtered_hands[p] = hand
            else:
                filtered_hands[p] = [{"hidden": True} for _ in hand]
        state["hands"] = filtered_hands
        state["my_name"] = player_name
        return state


class BarbuGame:
    """Contrôleur principal du jeu."""

    def __init__(self):
        self.state = GameState()

    # ------------------------------------------------------------------ #
    #  Gestion des joueurs                                                 #
    # ------------------------------------------------------------------ #

    def add_player(self, name: str) -> tuple[bool, str]:
        if len(self.state.players) >= 4:
            return False, "La partie est déjà complète (4 joueurs max)."
        if name in self.state.players:
            return False, f"Le nom '{name}' est déjà pris."
        if self.state.phase != GamePhase.WAITING:
            return False, "La partie a déjà commencé."
        self.state.players.append(name)
        self.state.scores[name] = 0
        return True, f"{name} a rejoint la partie."

    def can_start(self) -> bool:
        return len(self.state.players) == 4 and self.state.phase == GamePhase.WAITING

    # ------------------------------------------------------------------ #
    #  Démarrage                                                           #
    # ------------------------------------------------------------------ #

    def start_game(self) -> tuple[bool, str]:
        if not self.can_start():
            return False, "Il faut exactement 4 joueurs pour démarrer."
        self._start_round(1)
        return True, "La partie commence !"

    def _start_round(self, round_num: int):
        self.state.current_round = round_num
        self.state.round_type = RoundType(round_num)
        self.state.round_scores = {p: 0 for p in self.state.players}
        self.state.trick_number = 0
        self.state.total_tricks = 13  # 52 cartes / 4 joueurs
        self.state.last_trick_winner = None
        self.state.last_trick_points = 0

        if self.state.round_type == RoundType.REUSSITE:
            self._setup_reussite()
        else:
            self._deal_and_start_tricks()

        self.state.phase = GamePhase.ROUND_START

    def _deal_and_start_tricks(self):
        deck = create_deck()
        hands_list = deal_cards(deck)
        for i, player in enumerate(self.state.players):
            self.state.hands[player] = [c.to_dict() for c in hands_list[i]]
        # Premier joueur aléatoire
        self.state.current_player_idx = random.randint(0, 3)
        self.state.current_trick = []
        self.state.lead_suit = None

    def _setup_reussite(self):
        deck = create_deck()
        hands_list = deal_cards(deck)
        for i, player in enumerate(self.state.players):
            self.state.hands[player] = [c.to_dict() for c in hands_list[i]]
        self.state.reussite_board = ReussiteBoard().to_dict()
        self.state.reussite_turn_idx = random.randint(0, 3)
        self.state.reussite_finished_order = []

    # ------------------------------------------------------------------ #
    #  Confirmer début de manche (après affichage règles)                  #
    # ------------------------------------------------------------------ #

    def acknowledge_round_start(self, player: str) -> tuple[bool, str]:
        if self.state.phase != GamePhase.ROUND_START:
            return False, "Ce n'est pas le bon moment."
        self.state.phase = (
            GamePhase.REUSSITE
            if self.state.round_type == RoundType.REUSSITE
            else GamePhase.PLAYING_TRICK
        )
        return True, "C'est parti !"

    # ------------------------------------------------------------------ #
    #  Jouer une carte (manches à plis)                                    #
    # ------------------------------------------------------------------ #

    def play_card(self, player: str, card_dict: dict) -> tuple[bool, str]:
        if self.state.phase != GamePhase.PLAYING_TRICK:
            return False, "Ce n'est pas le moment de jouer une carte."

        current_player = self.state.players[self.state.current_player_idx]
        if player != current_player:
            return False, f"Ce n'est pas ton tour. C'est à {current_player} de jouer."

        card = Card.from_dict(card_dict)
        hand = [Card.from_dict(c) for c in self.state.hands[player]]

        if card not in hand:
            return False, "Tu ne possèdes pas cette carte."

        # Vérifier la règle de couleur
        if self.state.lead_suit:
            lead_suit = Suit[self.state.lead_suit]
            hand_suits = {c.suit for c in hand}
            if card.suit != lead_suit and lead_suit in hand_suits:
                return False, f"Tu dois jouer une carte de couleur {lead_suit.value} si tu en as."

        # Jouer la carte
        hand.remove(card)
        self.state.hands[player] = [c.to_dict() for c in hand]
        self.state.current_trick.append({"player": player, "card": card_dict})

        if not self.state.lead_suit:
            self.state.lead_suit = card.suit.name

        # Vérifier si le pli est complet
        if len(self.state.current_trick) == 4:
            return self._resolve_trick()
        else:
            self.state.current_player_idx = (self.state.current_player_idx + 1) % 4
            return True, f"{player} a joué {card}."

    def _resolve_trick(self) -> tuple[bool, str]:
        trick_cards = [(entry["player"], Card.from_dict(entry["card"])) for entry in self.state.current_trick]
        lead_suit = Suit[self.state.lead_suit]

        # Convertir pour determine_trick_winner
        indexed_trick = [
            (self.state.players.index(p), c) for p, c in trick_cards
        ]
        winner_idx = determine_trick_winner(indexed_trick, lead_suit)
        winner_name = self.state.players[winner_idx]

        self.state.trick_number += 1

        # Calculer les points
        cards_only = [c for _, c in trick_cards]
        pts_dict = calculate_trick_points(
            cards_only,
            winner_idx,
            self.state.round_type,
            self.state.total_tricks,
            self.state.trick_number,
        )
        pts = pts_dict.get(winner_idx, 0)

        self.state.round_scores[winner_name] = self.state.round_scores.get(winner_name, 0) + pts
        self.state.last_trick_winner = winner_name
        self.state.last_trick_points = pts

        # Préparer le prochain pli
        self.state.current_player_idx = winner_idx
        self.state.current_trick = []
        self.state.lead_suit = None

        # Fin de manche ?
        if self.state.trick_number >= self.state.total_tricks:
            self._end_round()
            return True, f"{winner_name} remporte le dernier pli ({pts} pts). Fin de la manche !"

        self.state.phase = GamePhase.TRICK_RESULT
        return True, f"{winner_name} remporte le pli ({pts} pts) !"

    def acknowledge_trick(self, player: str) -> tuple[bool, str]:
        """Le joueur courant confirme qu'il a vu le résultat du pli."""
        if self.state.phase != GamePhase.TRICK_RESULT:
            return False, "Pas de résultat de pli à confirmer."
        self.state.phase = GamePhase.PLAYING_TRICK
        return True, "Prochain pli !"

    # ------------------------------------------------------------------ #
    #  Réussite                                                            #
    # ------------------------------------------------------------------ #

    def play_reussite(self, player: str, card_dict: dict) -> tuple[bool, str]:
        if self.state.phase != GamePhase.REUSSITE:
            return False, "Ce n'est pas la phase Réussite."

        current_player = self.state.players[self.state.reussite_turn_idx]
        if player != current_player:
            return False, f"Ce n'est pas ton tour. C'est à {current_player}."

        card = Card.from_dict(card_dict)
        hand = [Card.from_dict(c) for c in self.state.hands[player]]

        if card not in hand:
            return False, "Tu ne possèdes pas cette carte."

        board = ReussiteBoard.from_dict(self.state.reussite_board)

        if not board.can_place(card):
            return False, f"Tu ne peux pas poser {card} pour l'instant."

        board.place(card)
        hand.remove(card)
        self.state.hands[player] = [c.to_dict() for c in hand]
        self.state.reussite_board = board.to_dict()

        # Si le joueur a fini ses cartes
        if not hand and player not in self.state.reussite_finished_order:
            self.state.reussite_finished_order.append(player)

        # Si tous ont fini → fin de manche
        if len(self.state.reussite_finished_order) == 4:
            self._end_reussite()
            return True, "Réussite terminée !"

        # Le roi permet de rejouer, sinon tour suivant
        is_king = card.rank == Rank.KING
        if not is_king or not hand:
            self._next_reussite_turn()

        return True, f"{player} pose {card}." + (" Rejoue (Roi) !" if is_king and hand else "")

    def pass_reussite(self, player: str) -> tuple[bool, str]:
        """Passer son tour à la réussite si aucune carte jouable."""
        if self.state.phase != GamePhase.REUSSITE:
            return False, "Ce n'est pas la phase Réussite."

        current_player = self.state.players[self.state.reussite_turn_idx]
        if player != current_player:
            return False, "Ce n'est pas ton tour."

        board = ReussiteBoard.from_dict(self.state.reussite_board)
        hand = [Card.from_dict(c) for c in self.state.hands[player]]
        playable = board.get_playable_cards(hand)

        if playable:
            return False, "Tu peux encore jouer des cartes !"

        self._next_reussite_turn()
        return True, f"{player} passe son tour."

    def _next_reussite_turn(self):
        self.state.reussite_turn_idx = (self.state.reussite_turn_idx + 1) % 4

    def _end_reussite(self):
        bonus = [-200, -100, -50, 0]
        for i, player in enumerate(self.state.reussite_finished_order):
            self.state.round_scores[player] = bonus[i]
        # Les autres (si jamais) prennent 0
        self._end_round()

    # ------------------------------------------------------------------ #
    #  Fin de manche / partie                                              #
    # ------------------------------------------------------------------ #

    def _end_round(self):
        for player, pts in self.state.round_scores.items():
            self.state.scores[player] = self.state.scores.get(player, 0) + pts

        if self.state.current_round < 7:
            self.state.phase = GamePhase.ROUND_END
        else:
            self.state.phase = GamePhase.GAME_END

    def next_round(self) -> tuple[bool, str]:
        if self.state.phase != GamePhase.ROUND_END:
            return False, "La manche n'est pas encore terminée."
        next_round = self.state.current_round + 1
        self._start_round(next_round)
        return True, f"Manche {next_round} commence !"

    def get_winner(self) -> Optional[str]:
        if self.state.phase != GamePhase.GAME_END:
            return None
        # Gagnant = moins de points (tous les points sont négatifs)
        return min(self.state.scores, key=lambda p: self.state.scores[p])
