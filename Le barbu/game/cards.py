"""
Cartes et jeu de cartes pour le Barbu
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class Rank(Enum):
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "10")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    ACE = (14, "A")

    def __init__(self, value: int, symbol: str):
        self.numeric_value = value
        self.symbol = symbol


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self):
        return f"{self.rank.symbol}{self.suit.value}"

    def __repr__(self):
        return self.__str__()

    def to_dict(self) -> dict:
        return {"rank": self.rank.name, "suit": self.suit.name}

    @staticmethod
    def from_dict(d: dict) -> "Card":
        return Card(rank=Rank[d["rank"]], suit=Suit[d["suit"]])


def create_deck() -> list[Card]:
    """Crée un jeu de 52 cartes mélangé."""
    import random
    deck = [Card(rank, suit) for suit in Suit for rank in Rank]
    random.shuffle(deck)
    return deck


def deal_cards(deck: list[Card], num_players: int = 4) -> list[list[Card]]:
    """Distribue les cartes également entre les joueurs."""
    hands = [[] for _ in range(num_players)]
    for i, card in enumerate(deck):
        hands[i % num_players].append(card)
    # Trier chaque main par couleur puis valeur
    for hand in hands:
        hand.sort(key=lambda c: (c.suit.name, c.rank.numeric_value))
    return hands
