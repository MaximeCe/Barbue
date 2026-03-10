"""
Logique des manches du Barbu
"""
from enum import Enum
from typing import Optional
from .cards import Card, Suit, Rank


class RoundType(Enum):
    PLIS = 1           # Chaque pli = 5 points
    COEURS = 2         # Chaque cœur dans un pli = 5 points
    REINES = 3         # Chaque reine dans un pli = 25 points
    ROI_PIQUE = 4      # Roi de pique = 50 points
    DERNIERS_PLIS = 5  # Avant-dernier pli = 20pts, dernier = 30pts
    SALADE = 6         # Toutes les règles précédentes
    REUSSITE = 7       # Jeu de réussite


ROUND_NAMES = {
    RoundType.PLIS: "1 - Les Plis",
    RoundType.COEURS: "2 - Les Cœurs",
    RoundType.REINES: "3 - Les Reines",
    RoundType.ROI_PIQUE: "4 - Le Roi de Pique",
    RoundType.DERNIERS_PLIS: "5 - Les Derniers Plis",
    RoundType.SALADE: "6 - La Salade",
    RoundType.REUSSITE: "7 - La Réussite",
}

ROUND_DESCRIPTIONS = {
    RoundType.PLIS: "Chaque pli remporté = 5 points",
    RoundType.COEURS: "Chaque cœur dans un pli remporté = 5 points",
    RoundType.REINES: "Chaque reine dans un pli remporté = 25 points",
    RoundType.ROI_PIQUE: "Remporter le roi de pique = 50 points",
    RoundType.DERNIERS_PLIS: "Avant-dernier pli = 20 pts, Dernier pli = 30 pts",
    RoundType.SALADE: "Toutes les règles précédentes simultanément !",
    RoundType.REUSSITE: "Rangez vos cartes autour des 7. Le premier fini = -200 pts",
}

ROI_PIQUE = Card(Rank.KING, Suit.SPADES)


def calculate_trick_points(
    trick: list[Card],
    winner_idx: int,
    round_type: RoundType,
    total_tricks: int,
    current_trick_number: int,
) -> dict[int, int]:
    """
    Calcule les points pour un pli donné selon les règles de la manche.
    Retourne un dict {player_idx: points}.
    """
    points = {winner_idx: 0}

    def add(val):
        points[winner_idx] = points.get(winner_idx, 0) + val

    if round_type in (RoundType.PLIS, RoundType.SALADE):
        add(5)

    if round_type in (RoundType.COEURS, RoundType.SALADE):
        hearts_in_trick = sum(1 for c in trick if c.suit == Suit.HEARTS)
        add(hearts_in_trick * 5)

    if round_type in (RoundType.REINES, RoundType.SALADE):
        queens_in_trick = sum(1 for c in trick if c.rank == Rank.QUEEN)
        add(queens_in_trick * 25)

    if round_type in (RoundType.ROI_PIQUE, RoundType.SALADE):
        if ROI_PIQUE in trick:
            add(50)

    if round_type in (RoundType.DERNIERS_PLIS, RoundType.SALADE):
        if current_trick_number == total_tricks - 1:  # avant-dernier (0-indexed)
            add(20)
        elif current_trick_number == total_tricks:  # dernier
            add(30)

    return points


def determine_trick_winner(
    trick: list[tuple[int, Card]],  # liste de (player_idx, card)
    lead_suit: Suit,
) -> int:
    """
    Détermine le gagnant du pli.
    Seules les cartes de la couleur demandée comptent.
    Retourne l'index du joueur gagnant.
    """
    # Filtrer uniquement les cartes de la couleur demandée
    lead_cards = [(idx, card) for idx, card in trick if card.suit == lead_suit]
    # Le gagnant est celui avec la carte la plus haute de la couleur
    winner_idx, _ = max(lead_cards, key=lambda x: x[1].rank.numeric_value)
    return winner_idx


# --- Réussite ---

class ReussiteBoard:
    """
    Plateau de la Réussite.
    Chaque couleur a une colonne, avec le 7 au centre.
    Les cartes s'ajoutent à gauche (6, 5, 4, 3, 2) ou à droite (8, 9, 10, J, Q, K, A).
    """

    def __init__(self):
        # Pour chaque couleur : {rank_value: card}
        self.placed: dict[Suit, set[int]] = {suit: set() for suit in Suit}
        self.sevens_placed: dict[Suit, bool] = {suit: False for suit in Suit}

    def can_place(self, card: Card) -> bool:
        suit = card.suit
        val = card.rank.numeric_value

        if val == 7:
            return not self.sevens_placed[suit]

        if not self.sevens_placed[suit]:
            return False

        # Peut placer si la carte adjacente est déjà posée
        return (val - 1) in self.placed[suit] or (val + 1) in self.placed[suit]

    def place(self, card: Card) -> bool:
        if not self.can_place(card):
            return False
        suit = card.suit
        val = card.rank.numeric_value
        if val == 7:
            self.sevens_placed[suit] = True
        self.placed[suit].add(val)
        return True

    def get_playable_cards(self, hand: list[Card]) -> list[Card]:
        return [c for c in hand if self.can_place(c)]

    def to_dict(self) -> dict:
        return {
            "placed": {suit.name: list(vals) for suit, vals in self.placed.items()},
            "sevens_placed": {suit.name: placed for suit, placed in self.sevens_placed.items()},
        }

    @staticmethod
    def from_dict(d: dict) -> "ReussiteBoard":
        board = ReussiteBoard()
        board.placed = {Suit[k]: set(v) for k, v in d["placed"].items()}
        board.sevens_placed = {Suit[k]: v for k, v in d["sevens_placed"].items()}
        return board
