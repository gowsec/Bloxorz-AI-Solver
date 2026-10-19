"""Basic level data for the first rendering milestone."""

from dataclasses import dataclass

Pos = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Level:
    name: str
    terrain: tuple[str, ...]
    start: Pos
    goal: Pos

    @property
    def rows(self) -> int:
        return len(self.terrain)

    @property
    def cols(self) -> int:
        return len(self.terrain[0])

    @classmethod
    def from_grid(cls, name: str, grid: tuple[str, ...]) -> "Level":
        """Parse a rectangular grid; coordinates are (row, column)."""
        grid = tuple(grid)
        if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
            raise ValueError("Level grid must be non-empty and rectangular")
        if any(cell not in ".#SGF" for row in grid for cell in row):
            raise ValueError("Allowed tiles: . # S G F")
        starts = [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == "S"]
        goals = [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == "G"]
        if len(starts) != 1 or len(goals) != 1:
            raise ValueError("Level needs exactly one S and one G")
        terrain = tuple(row.replace("S", "#").replace("G", "#") for row in grid)
        return cls(name, terrain, starts[0], goals[0])
