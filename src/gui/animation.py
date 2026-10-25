"""Small time-based translation animation between valid engine states."""
import time

class RollAnimation:
    def __init__(self, duration: float = 0.18):
        self.duration = duration
        self.start = self.end = None
        self.started = 0.0

    def begin(self, old_pose, new_pose):
        self.start = (old_pose.r, old_pose.c) if hasattr(old_pose, 'r') else None
        self.end = (new_pose.r, new_pose.c) if hasattr(new_pose, 'r') else None
        self.started = time.monotonic()

    @property
    def active(self):
        return self.start is not None and time.monotonic() - self.started < self.duration

    def offset(self):
        if not self.active or self.end is None:
            return (0.0, 0.0)
        t = min(1.0, (time.monotonic() - self.started) / self.duration)
        t = t*t*(3-2*t)
        return (self.start[0] + (self.end[0]-self.start[0])*t - self.end[0],
                self.start[1] + (self.end[1]-self.start[1])*t - self.end[1])
