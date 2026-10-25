from __future__ import annotations

import pygame
from src.core.board import Level
from src.core.constants import Orientation
from src.core.state import BlockPose, SplitPose, State, cells

BACKGROUND = (17, 24, 39)
TEXT = (230, 237, 247)
MUTED = (151, 168, 192)
FLOOR = (166, 181, 199)
FRAGILE = (235, 155, 66)
GOAL = (70, 218, 174)
BLOCK = (169, 116, 65)


def project(row: float, col: float, z: float = 0) -> pygame.Vector2:
    return pygame.Vector2(col - row, (col + row) * 0.5 - z)


class Renderer:
    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen: pygame.Surface, level: Level, state: State | None = None,
             block_offset: tuple[float, float] = (0, 0), message: str = "") -> None:
        width, height = screen.get_size()
        canvas = pygame.Surface((max(640, width), max(520, height)))
        canvas.fill(BACKGROUND)
        w, h = canvas.get_size()
        canvas.blit(self.title_font.render(level.name, True, TEXT), (32, 24))
        bounds = [project(r, c, z) for r in (0, level.rows) for c in (0, level.cols) for z in (-0.3, 0)]
        start = level.start
        bounds.extend(project(start[0] + dr, start[1] + dc, 2) for dr, dc in ((0, 0), (0, 1), (1, 1), (1, 0)))
        lo = pygame.Vector2(min(p.x for p in bounds), min(p.y for p in bounds))
        hi = pygame.Vector2(max(p.x for p in bounds), max(p.y for p in bounds))
        area = pygame.Rect(48, 88, w - 96, h - 160)
        scale = min(48, area.width / max(hi.x - lo.x, 1), area.height / max(hi.y - lo.y, 1))
        origin = pygame.Vector2(area.center) - (lo + hi) * (scale / 2)

        def point(row, col, z=0):
            p = origin + project(row, col, z) * scale
            return round(p.x), round(p.y)

        def diamond(row, col, inset=0.025, z=0):
            return [point(row + dr, col + dc, z) for dr, dc in ((inset, inset), (inset, 1-inset), (1-inset, 1-inset), (1-inset, inset))]

        def polygon(color, points, outline=(52, 63, 79)):
            pygame.draw.polygon(canvas, color, points)
            if outline:
                pygame.draw.lines(canvas, outline, True, points, 1)

        tiles = [(r, c) for r, line in enumerate(level.terrain) for c, cell in enumerate(line) if cell != '.']
        for bridge in level.bridges.values():
            tiles.append(bridge.pos)
        tiles = sorted(set(tiles))
        for row, col in tiles:
            polygon((11, 17, 29), [(x+8, y+12) for x, y in diamond(row, col, z=-0.3)], None)
        block_cells = set(cells(state.pose)) if state else {level.start}
        for row, col in sorted(tiles, key=lambda pos: (sum(pos), pos[0])):
            tile = level.terrain[row][col]
            bridge_id = level.bridge_at.get((row, col))
            bridge_closed = bridge_id is not None and not (state and state.bridges & (1 << bridge_id))
            if bridge_closed:
                continue
            top, bottom = diamond(row, col), diamond(row, col, z=-0.3)
            color = FRAGILE if tile == 'F' else FLOOR
            side1 = (157, 91, 37) if tile == 'F' else (87, 105, 128)
            side2 = (189, 113, 43) if tile == 'F' else (112, 131, 152)
            polygon(side1, [top[1], top[2], bottom[2], bottom[1]])
            polygon(side2, [top[2], top[3], bottom[3], bottom[2]])
            polygon(color, top)
            if (row, col) == level.goal:
                opening = diamond(row, col, .18)
                polygon((10, 15, 24), opening, None)
                pygame.draw.lines(canvas, GOAL, True, opening, 2)
            if tile == 'F':
                pygame.draw.lines(canvas, (146, 83, 32), False, [point(row+dr, col+dc, .01) for dr, dc in ((.15,.4),(.42,.52),(.5,.35),(.8,.62))], 2)
            if (row, col) in level.switches:
                pygame.draw.circle(canvas, (40, 90, 112), point(row+.5, col+.5, .04), max(3, round(scale*.12)))
        if state:
            pose = state.pose
            if isinstance(pose, BlockPose):
                r, c = pose.r + block_offset[0], pose.c + block_offset[1]
                if pose.orient == Orientation.STANDING:
                    base = diamond(r, c, 0, .02)
                    cap = diamond(r, c, 0, 2)
                    polygon((125,80,43), [cap[1],cap[2],base[2],base[1]])
                    polygon(BLOCK, [cap[2],cap[3],base[3],base[2]])
                    polygon((221,177,116), cap)
                else:
                    (r2,c2) = (r, c+1) if pose.orient == Orientation.HORIZONTAL else (r+1,c)
                    front, back = diamond(r,c,0,.02), diamond(r2,c2,0,.02)
                    polygon((125,80,43), [front[1],front[2],back[2],back[1]])
                    polygon(BLOCK, [front[2],front[3],back[3],back[2]])
                    polygon((221,177,116), [front[0],front[1],back[1],back[0]])
                    pygame.draw.line(canvas, (103,68,40), front[1], front[2], 1)
            else:
                for r,c in (pose.a, pose.b):
                    base=diamond(r,c,0,.02); cap=diamond(r,c,0,1)
                    polygon(BLOCK,[cap[1],cap[2],base[2],base[1]])
                    polygon((221,177,116),cap)
        canvas.blit(self.font.render('Arrow keys: Move   Esc: Exit', True, MUTED), (32, h-40))
        if message:
            label = self.title_font.render(message, True, GOAL if 'win' in message.lower() else (255,120,120))
            canvas.blit(label, label.get_rect(center=(w//2, 65)))
        if canvas.get_size() != screen.get_size():
            canvas = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(canvas, (0,0))






