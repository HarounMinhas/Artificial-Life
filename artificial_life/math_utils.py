import math
from dataclasses import dataclass


@dataclass
class Vec2:
    x: float
    y: float

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vec2":
        length = self.length()
        if length == 0:
            return Vec2(0, 0)
        return Vec2(self.x / length, self.y / length)

    def clamp(self, min_x: float, max_x: float, min_y: float, max_y: float) -> "Vec2":
        return Vec2(
            min(max(self.x, min_x), max_x),
            min(max(self.y, min_y), max_y),
        )


def angle_to_vector(angle_rad: float) -> Vec2:
    return Vec2(math.cos(angle_rad), math.sin(angle_rad))


def vector_to_angle(vec: Vec2) -> float:
    return math.atan2(vec.y, vec.x)


def clamp_angle_rad(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi
