from __future__ import annotations

import math
import pygame
from src.core.board import Level
from src.core.constants import Orientation
from src.core.state import BlockPose, SplitPose, State

BACKGROUND = (17, 24, 39)
TEXT = (230, 237, 247)
MUTED = (151, 168, 192)
FLOOR = (166, 181, 199)
FRAGILE = (235, 155, 66)
GOAL = (70, 218, 174)
BLOCK = (169, 116, 65)


def project(row: float, col: float, z: float = 0) -> pygame.Vector2:
    return pygame.Vector2(col - row, (col + row) * 0.5 - z)


def footprint(p):
    return (2 if p.orient == Orientation.VERTICAL else 1,
            2 if p.orient == Orientation.HORIZONTAL else 1)


def block_vertices(p, dz=0.0):
    lr, lc = footprint(p)
    h = 2 if p.orient == Orientation.STANDING else 1
    r, c = p.r, p.c
    return [(r, c, dz), (r, c+lc, dz), (r+lr, c+lc, dz), (r+lr, c, dz),
            (r, c, h+dz), (r, c+lc, h+dz), (r+lr, c+lc, h+dz), (r+lr, c, h+dz)]


def roll_pivot(old_p, new_p):
    """Trả về (trục, toạ độ cạnh xoay, dấu) của cạnh mà khối lăn quanh."""
    olr, olc = footprint(old_p)
    nlr, nlc = footprint(new_p)
    dr = (old_p.r + olr / 2) - (new_p.r + nlr / 2)
    dc = (old_p.c + olc / 2) - (new_p.c + nlc / 2)
    if abs(dr) > abs(dc):
        return 'r', (old_p.r if dr > 0 else old_p.r + olr), (1 if dr > 0 else -1)
    return 'c', (old_p.c if dc > 0 else old_p.c + olc), (1 if dc > 0 else -1)


def rotate(vertices, axis, pivot, sign, angle, dz=0.0):
    cos, sin = math.cos(angle), math.sin(angle)
    out = []
    for r, c, z in vertices:
        lz = z - dz
        if axis == 'r':
            s = r - pivot
            out.append((s*cos + sign*lz*sin + pivot, c, -sign*s*sin + lz*cos + dz))
        else:
            s = c - pivot
            out.append((r, s*cos + sign*lz*sin + pivot, -sign*s*sin + lz*cos + dz))
    return out


class Renderer:
    def __init__(self) -> None:
        self.title_font = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen: pygame.Surface, level: Level, state: State | None = None,
             animation=None, message: str = "",
             selected_cube: int = 0, cube_offsets=((0.0, 0.0), (0.0, 0.0))) -> None:
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

        def polygon(color, points, outline=(52, 63, 79), surf=None):
            target = canvas if surf is None else surf
            pygame.draw.polygon(target, color, points)
            if outline:
                pygame.draw.lines(target, outline, True, points, 1)

        def solid(r, c):
            if not (0 <= r < level.rows and 0 <= c < level.cols):
                return False
            bid = level.bridge_at.get((r, c))
            if bid is not None:
                return bool(state and state.bridges & (1 << bid))
            return level.terrain[r][c] != '.'

        # ---------- Tiles ----------
        tiles = [(r, c) for r, line in enumerate(level.terrain) for c, cell in enumerate(line) if cell != '.']
        for bridge in level.bridges.values():
            tiles.append(bridge.pos)
        tiles = sorted(set(tiles))

        # Ô gạch yếu bị vỡ: rơi cùng khối
        broken, broken_dz, broken_done = None, 0.0, False
        if (animation is not None and getattr(animation, 'is_falling', False)
                and getattr(animation, 'fall_kind', None) == "straight"
                and isinstance(getattr(animation, 'fall_pose', None), BlockPose)):
            broken = (animation.fall_pose.r, animation.fall_pose.c)
            broken_dz = -15 * max(0.0, (animation.fall_t - 0.35) / 0.65) ** 2
            broken_done = animation.fall_t >= 1.0

        for row, col in tiles:
            if (row, col) == broken:
                continue
            polygon((11, 17, 29), [(x+8, y+12) for x, y in diamond(row, col, z=-0.3)], None)

        for row, col in sorted(tiles, key=lambda pos: (sum(pos), pos[0])):
            tile = level.terrain[row][col]
            bridge_id = level.bridge_at.get((row, col))
            bridge_closed = bridge_id is not None and not (state and state.bridges & (1 << bridge_id))
            if bridge_closed:
                continue
            if (row, col) == broken and broken_done:
                continue
            dz = broken_dz if (row, col) == broken else 0.0
            top, bottom = diamond(row, col, z=dz), diamond(row, col, z=-0.3 + dz)
            color = FRAGILE if tile == 'F' else FLOOR
            side1 = (157, 91, 37) if tile == 'F' else (87, 105, 128)
            side2 = (189, 113, 43) if tile == 'F' else (112, 131, 152)
            polygon(side1, [top[1], top[2], bottom[2], bottom[1]])
            polygon(side2, [top[2], top[3], bottom[3], bottom[2]])
            polygon(color, top)
            if (row, col) == level.goal:
                opening = diamond(row, col)
                polygon((10, 15, 24), opening, None)
                pygame.draw.lines(canvas, GOAL, True, opening, 2)
            if tile == 'F':
                pygame.draw.lines(canvas, (146, 83, 32), False,
                                  [point(row+dr, col+dc, .01 + dz) for dr, dc in ((.15, .4), (.42, .52), (.5, .35), (.8, .62))], 2)
            if (row, col) in level.switches:
                pygame.draw.circle(canvas, (40, 90, 112), point(row+.5, col+.5, .04), max(3, round(scale*.12)))

        # ---------- Block ----------
        if state:
            falling = animation is not None and getattr(animation, 'is_falling', False)
            vertices = None
            sink_clip = None

            if falling:
                if animation.active:   # rơi xong thì không vẽ nữa -> biến mất
                    t = animation.fall_t
                    old_p, new_p = animation.old_pose, animation.fall_pose
                    if isinstance(old_p, BlockPose) and isinstance(new_p, BlockPose):
                        axis, pivot, sign = roll_pivot(old_p, new_p)
                        if animation.fall_kind == "edge":
                            lever = None   # (axis, pivot, sign) của đòn bẩy
                            if new_p.orient != Orientation.STANDING:
                                if new_p.orient == Orientation.HORIZONTAL:
                                    a_ok = solid(new_p.r, new_p.c)
                                    b_ok = solid(new_p.r, new_p.c + 1)
                                    l_axis, l_pivot = 'c', new_p.c + 1
                                else:
                                    a_ok = solid(new_p.r, new_p.c)
                                    b_ok = solid(new_p.r + 1, new_p.c)
                                    l_axis, l_pivot = 'r', new_p.r + 1
                                if a_ok != b_ok:   # đúng 1 ô có gạch -> có đòn bẩy
                                    lever = (l_axis, l_pivot, 1 if a_ok else -1)

                            if lever:
                                # Pha 1: lăn bình thường sang tư thế mới
                                s = min(1.0, t / 0.35)
                                vertices = block_vertices(new_p)
                                vertices = rotate(vertices, axis, pivot, sign, (1 - s) * math.pi / 2)
                                if t > 0.35:
                                    # Pha 2: xoay quanh đường biên (qua trung điểm khối) rồi rơi
                                    phi = (math.pi / 2) * min(1.0, (t - 0.35) / 0.4)
                                    z_drop = -15 * max(0.0, (t - 0.55) / 0.45) ** 2
                                    la, lp, ls = lever
                                    vertices = rotate(block_vertices(new_p, z_drop),
                                                      la, lp, ls, phi, z_drop)
                            else:
                                # Không có đòn bẩy: nghiêng quanh cạnh viền
                                phi = (math.pi / 2) * min(1.0, t * 1.6)
                                z_drop = -15 * max(0.0, (t - 0.45) / 0.55) ** 2
                                vertices = rotate(block_vertices(old_p, z_drop),
                                                  axis, pivot, sign, -phi, z_drop)
                        elif animation.fall_kind == "goal":
                            # Lăn vào ô đích, sau đó chìm thẳng xuống lỗ
                            s = min(1.0, t / 0.25)
                            z_drop = -3 * max(0.0, (t - 0.25) / 0.75) ** 2
                            vertices = rotate(block_vertices(new_p, z_drop),
                                              axis, pivot, sign, (1 - s) * math.pi / 2, z_drop)
                            if t > 0.25:
                                sink_clip = (new_p.r, new_p.c)
                        else:
                            # FRAGILE_BROKE: lăn bình thường rồi rơi thẳng
                            s = min(1.0, t / 0.35)
                            z_drop = -15 * max(0.0, (t - 0.35) / 0.65) ** 2
                            vertices = rotate(block_vertices(new_p, z_drop),
                                              axis, pivot, sign, (1 - s) * math.pi / 2, z_drop)
            else:
                pose = state.pose
                if isinstance(pose, BlockPose):
                    vertices = block_vertices(pose)
                    t = animation.progress if (animation and animation.active) else 1.0
                    old_p = getattr(animation, 'old_pose', None)
                    if t < 1.0 and isinstance(old_p, BlockPose):
                        axis, pivot, sign = roll_pivot(old_p, pose)
                        vertices = rotate(vertices, axis, pivot, sign, (1 - t) * math.pi / 2)

            if vertices:
                pts = [point(v[0], v[1], v[2]) for v in vertices]
                faces = [
                    ((125, 80, 43), [0, 1, 5, 4]),
                    ((125, 80, 43), [0, 3, 7, 4]),
                    (BLOCK, [1, 2, 6, 5]),
                    (BLOCK, [3, 2, 6, 7]),
                    ((221, 177, 116), [4, 5, 6, 7]),
                    ((100, 80, 60), [0, 1, 2, 3]),
                ]
                faces.sort(key=lambda f: sum(sum(vertices[i]) for i in f[1]))

                target = pygame.Surface(canvas.get_size(), pygame.SRCALPHA) if sink_clip else canvas
                for color, indices in faces:
                    polygon(color, [pts[i] for i in indices], surf=target)

                if sink_clip:
                    gr, gc = sink_clip
                    left, right = point(gr + 1, gc), point(gr, gc + 1)
                    bottom = point(gr + 1, gc + 1)
                    region = [left, bottom, right, (right[0], -2000), (left[0], -2000)]
                    mask = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
                    pygame.draw.polygon(mask, (255, 255, 255, 255), region)
                    target.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    canvas.blit(target, (0, 0))

        if message:
            label = self.title_font.render(message, True, GOAL if 'win' in message.lower() else (255, 120, 120))
            canvas.blit(label, label.get_rect(center=(w//2, 65)))
        if canvas.get_size() != screen.get_size():
            canvas = pygame.transform.smoothscale(canvas, screen.get_size())
        screen.blit(canvas, (0, 0))