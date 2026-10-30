"""Edit this grid to design a level by hand; all rows have equal length."""

from src.core.board import Level

DEMO_LEVEL = Level.from_grid(
    "Level 01 - First steps",
    (
        "###.......",
        "#S####....",
        "#########.",
        ".###..####",
        "..##..#G##",
        "..#######.",
        "...##F##..",
    ),
)
