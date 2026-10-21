"""Draw a shaded isometric board using pygame-ce polygons."""

import pygame
from src.core.board import Level

BACKGROUND = (17, 24, 39)
TEXT = (230, 237, 247)
MUTED = (151, 168, 192)
FLOOR = (166, 181, 199)
FRAGILE = (235, 155, 66)
GOAL = (70, 218, 174)
BLOCK = (169, 116, 65)


def project(row: float, col: float, z: float = 0) -> pygame.Vector2:
    """Board units to isometric coordinates; z is height above the floor."""
    return pygame.Vector2(col - row, (col + row) * 0.5 - z)


class Renderer:
    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen: pygame.Surface, level: Level) -> None:
        width, height = screen.get_size()
        canvas = pygame.Surface((max(640, width), max(520, height)))
        canvas.fill(BACKGROUND)
        w, h = canvas.get_size()
        canvas.blit(self.title_font.render(level.name, True, TEXT), (32, 24))
        bounds = [project(r, c, z) for r in (0, level.rows)
                  for c in (0, level.cols) for z in (-0.3, 0)]
        r, c = level.start
        bounds.extend(project(r + dr, c + dc, 2) for dr, dc in
                      ((0, 0), (0, 1), (1, 1), (1, 0)))
        lo = pygame.Vector2(min(p.x for p in bounds), min(p.y for p in bounds))
        hi = pygame.Vector2(max(p.x for p in bounds), max(p.y for p in bounds))
        area = pygame.Rect(48, 88, w - 96, h - 160)
        scale = min(48, area.width / (hi.x - lo.x), area.height / (hi.y - lo.y))
        origin = pygame.Vector2(area.center) - (lo + hi) * (scale / 2)

        def point(row, col, z=0):
            p = origin + project(row, col, z) * scale
            return round(p.x), round(p.y)

        def diamond(row, col, inset=0.025, z=0):
            return [point(row + dr, col + dc, z) for dr, dc in
                    ((inset, inset), (inset, 1-inset),
                     (1-inset, 1-inset), (1-inset, inset))]

        def polygon(color, points, outline=(52, 63, 79)):
            pygame.draw.polygon(canvas, color, points)
            if outline:
                pygame.draw.lines(canvas, outline, True, points, 1)

        cells = [(r, c) for r, line in enumerate(level.terrain)
                 for c, cell in enumerate(line) if cell != '.']
        for row, col in cells:
            shadow = [(x + 8, y + 12) for x, y in diamond(row, col, z=-0.3)]
            polygon((11, 17, 29), shadow, None)

        # Painter's order: draw distant tiles and their contents first.
        for row, col in sorted(cells, key=lambda pos: (sum(pos), pos[0])):
            fragile = level.terrain[row][col] == 'F'
            top = diamond(row, col)
            bottom = diamond(row, col, z=-0.3)
            polygon((157, 91, 37) if fragile else (87, 105, 128),
                    [top[1], top[2], bottom[2], bottom[1]])
            polygon((189, 113, 43) if fragile else (112, 131, 152),
                    [top[2], top[3], bottom[3], bottom[2]])
            polygon(FRAGILE if fragile else FLOOR, top)
            if (row, col) == level.goal:
                opening = diamond(row, col, 0.18)
                polygon((10, 15, 24), opening, None)
                # Inner walls remain inside the opening's diamond.
                center = point(row + 0.5, col + 0.5, -0.12)
                polygon((46, 62, 77), [opening[0], opening[1], center], None)
                polygon((32, 45, 59), [opening[3], opening[0], center], None)
                pygame.draw.lines(canvas, GOAL, True, opening, 2)
            if fragile:
                crack = [point(row + dr, col + dc, 0.01) for dr, dc in
                         ((0.15, 0.4), (0.42, 0.52), (0.5, 0.35), (0.8, 0.62))]
                pygame.draw.lines(canvas, (146, 83, 32), False, crack, 2)
            if (row, col) == level.start:
                base = diamond(row, col, 0.12, 0.02)
                cap = diamond(row, col, 0.12, 2)
                polygon((125, 80, 43), [cap[1], cap[2], base[2], base[1]])
                polygon(BLOCK, [cap[2], cap[3], base[3], base[2]])
                polygon((221, 177, 116), cap)
                mid = diamond(row, col, 0.12, 1)
                pygame.draw.lines(canvas, (103, 68, 40), False, [mid[1], mid[2], mid[3]], 1)

        canvas.blit(self.font.render('Esc: Exit', True, MUTED), (32, h - 40))
        if canvas.get_size() != screen.get_size():
            canvas = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(canvas, (0, 0))
