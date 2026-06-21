from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    minor: int

    def __post_init__(self):
        if not isinstance(self.minor, int):
            raise TypeError("Money.minor must be int")
        if self.minor < 0:
            raise ValueError("Money must be non-negative")
