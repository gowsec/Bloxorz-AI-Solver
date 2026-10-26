"""Time-based block translation for manual moves and solver replay."""
import time

from src.core.state import BlockPose, SplitPose


class RollAnimation:
    def __init__(self, duration: float = 0.18):
        self.duration = duration
        self.started = 0.0
        self.moving_cube: int | None = None
        self.old_pose = None
        self.fall_pose = None
        self.start = None
        self.end = None
        self.start_cubes = None
        self.end_cubes = None
        self.is_falling = False

    def reset(self):
        self.started = 0.0
        self.moving_cube = None
        self.start = self.end = None
        self.start_cubes = self.end_cubes = None
        self.old_pose = None
        self.fall_pose = None
        self.is_falling = False
        self.duration = 0.18

    def begin(self, old_pose, new_pose, cube: int | None = None):
        self.is_falling = False
        self.started = time.monotonic()
        self.moving_cube = cube
        self.old_pose = old_pose
        self.start = self.end = None
        self.start_cubes = self.end_cubes = None
        if isinstance(old_pose, BlockPose) and isinstance(new_pose, BlockPose):
            self.start = (old_pose.r, old_pose.c)
            self.end = (new_pose.r, new_pose.c)
        elif isinstance(old_pose, SplitPose) and isinstance(new_pose, SplitPose) and cube in (0, 1):
            self.start_cubes = old_pose.a, old_pose.b
            self.end_cubes = new_pose.a, new_pose.b

    @property
    def active(self) -> bool:
        # return (self.start is not None or self.start_cubes is not None) and time.monotonic() - self.started < self.duration
        has_started = self.start is not None or self.start_cubes is not None or getattr(self, 'is_falling', False)
        return has_started and (time.monotonic() - self.started < self.duration)
    def _progress(self) -> float:
        t = min(1.0, (time.monotonic() - self.started) / self.duration)
        return t * t * (3 - 2 * t)

    def offset(self) -> tuple[float, float]:
        if not self.active or self.start is None or self.end is None:
            return 0.0, 0.0
        t = self._progress()
        return (self.start[0] + (self.end[0] - self.start[0]) * t - self.end[0],
                self.start[1] + (self.end[1] - self.start[1]) * t - self.end[1])

    def cube_offsets(self) -> tuple[tuple[float, float], tuple[float, float]]:
        offsets = [(0.0, 0.0), (0.0, 0.0)]
        if not self.active or self.start_cubes is None or self.end_cubes is None:
            return offsets[0], offsets[1]
        t = self._progress()
        for index in (0, 1):
            if index != self.moving_cube:
                continue
            start, end = self.start_cubes[index], self.end_cubes[index]
            offsets[index] = (start[0] + (end[0] - start[0]) * t - end[0],
                              start[1] + (end[1] - start[1]) * t - end[1])
        return offsets[0], offsets[1]
    @property                   # <--- THÊM HÀM NÀY XUỐNG CUỐI
    def progress(self) -> float:
        if not self.active:
            return 1.0
        return self._progress()
    def begin_fall(self, old_pose, fall_pose, kind: str = "edge"):
        """kind: 'edge' = nghiêng qua viền map rồi rơi; 'straight' = lăn xong rồi rơi thẳng."""
        self.started = time.monotonic()
        self.old_pose = old_pose
        self.fall_pose = fall_pose
        self.fall_kind = kind
        self.is_falling = True
        self.duration = 1.0 if kind == "goal" else 0.8

    @property
    def fall_t(self) -> float:
        """Tiến trình tuyến tính 0..1 (không easing) để rơi nhanh dần."""
        return min(1.0, (time.monotonic() - self.started) / self.duration)