from pathlib import Path
from typing import TypeVar

from .props.utils import PRECISION


LF = "\n"
SPACE = " "

Self = TypeVar("Self", bound="G")


class G:
    def __init__(self, out_file_path: Path, *, rapid_height=0.0, is_si=True) -> Self:
        self.out_file_path = out_file_path
        self.out_file_descriptor = open(self.out_file_path, "w")
        self.rapid_height = max(0.0, rapid_height)
        self.position = {k: 0.0 for k in "xyz"}
        self.set_abs()
        self.set_millimeters() if is_si else self.set_inches()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False

    def close(self) -> None:
        self.end()
        self.out_file_descriptor.close()

    def abs_move(self, /, **kwargs) -> Self:
        next_position = self.updated_position(kwargs)
        is_rapid = (
            kwargs.get("z", self.position["z"]) > self.rapid_height
            and not self.is_vertical_move(next_position)
        )
        self.position = next_position
        cmd = "G0" if is_rapid else "G1"
        return self.write(f"{cmd} {self.format(**kwargs)}")

    def dwell(self, time: float) -> Self:
        return self.write(f"G4 {self.format(p=time)}")

    def feed(self, rate: float) -> Self:
        return self.write(f"G1 {self.format(f=rate)}")

    def end(self) -> Self:
        return self.write("M2")

    def is_vertical_move(self, position: dict) -> bool:
        return (
            self.position["x"] == position["x"]
            and self.position["y"] == position["y"]
            and self.position["z"] != position["z"]
        )

    def set_abs(self) -> Self:
        return self.write("G90")

    def set_inches(self) -> Self:
        return self.write("G20")

    def set_millimeters(self) -> Self:
        return self.write("G21")

    def format(self, /, **kwargs) -> str:
        return SPACE.join(
            "{0}{1:.{digits}f}".format(k, kwargs[k], digits=PRECISION)
            for k in sorted(kwargs)
        )

    def updated_position(self, position: dict) -> dict:
        return {k: position.get(k, self.position[k]) for k in self.position}

    def write(self, line: str) -> Self:
        self.out_file_descriptor.write(f"{line.upper()}{LF}")
        return self


class GRBL(G):
    def __init__(
        self,
        out_file_path: Path,
        *,
        rapid_height=0.0,
        is_si=True,
        vertical_feed_rate_factor=1.0,
    ) -> Self:
        super().__init__(out_file_path, rapid_height=rapid_height, is_si=is_si)
        self.feed_rate = 0.0
        self.vertical_feed_rate_factor = 1.0

    def drill(self, positions: list) -> Self:
        self.feed(self.feed_rate * self.vertical_feed_rate_factor)
        for position in positions:
            self.abs_move(**position)
        return self

    def feed(self, rate) -> Self:
        self.feed_rate = rate
        return super().feed(rate)
