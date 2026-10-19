"""Draw a top-down board using primitives, without external image assets."""

import pygame

from src.core.board import Level

BACKGROUND = (17, 24, 39)
TEXT = (230, 237, 247)
MUTED = (151, 168, 192)
FLOOR = (100, 124, 155)
FRAGILE = (235, 155, 66)
GOAL = (70, 218, 174)
BLOCK = (113, 170, 255)


class Renderer:
    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen: pygame.Surface, level: Level) -> None:
        screen.fill(BACKGROUND)
        width, height = screen.get_size()
        # Draw on a fixed minimum canvas so resizing never crops individual UI elements.
        canvas = pygame.Surface((max(640, width), max(520, height)))
        canvas.fill(BACKGROUND)
        w, h = canvas.get_size()
        canvas.blit(self.title_font.render("BLOXORZ / AI SOLVER", True, TEXT), (32, 24))
        canvas.blit(self.font.render(level.name, True, MUTED), (32, 66))
        tile = max(1, min(64, (w - 96) // level.cols, (h - 240) // level.rows))
        left = (w - tile * level.cols) // 2
        top = 112 + (h - 240 - tile * level.rows) // 2
        for r, row in enumerate(level.terrain):
            for c, cell in enumerate(row):
                rect = pygame.Rect(left + c * tile, top + r * tile, tile, tile)
                pygame.draw.rect(canvas, (29, 40, 59), rect, 1)
                if cell == ".":
                    continue
                face = rect.inflate(-4, -4)
                pygame.draw.rect(canvas, FRAGILE if cell == "F" else FLOOR, face, border_radius=3)
                if (r, c) == level.goal:
                    hole = face.inflate(-tile // 3, -tile // 3)
                    pygame.draw.rect(canvas, BACKGROUND, hole, border_radius=3)
                    pygame.draw.rect(canvas, GOAL, hole, 3, border_radius=3)
                if cell == "F":
                    canvas.blit(self.font.render("F", True, BACKGROUND), face.move(6, 3))
                if (r, c) == level.start:
                    block = face.inflate(-tile // 3, -tile // 5)
                    pygame.draw.rect(canvas, BLOCK, block, border_radius=4)
                    pygame.draw.rect(canvas, TEXT, block, 2, border_radius=4)
                    label = self.font.render("S", True, BACKGROUND)
                    canvas.blit(label, label.get_rect(center=block.center))
        for i, (color, label) in enumerate(((FLOOR, "Floor"), (GOAL, "Goal"), (FRAGILE, "Fragile"), (BLOCK, "Start / block"))):
            x = 32 + i * 148
            pygame.draw.rect(canvas, color, (x, h - 92, 16, 16), border_radius=3)
            canvas.blit(self.font.render(label, True, TEXT), (x + 24, h - 94))
        canvas.blit(self.font.render("Board preview  |  ESC: quit  |  Movement: next milestone", True, MUTED), (32, h - 48))
        if canvas.get_size() != screen.get_size():
            canvas = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(canvas, (0, 0))
