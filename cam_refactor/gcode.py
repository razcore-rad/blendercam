from math import isclose
from pathlib import PurePath
from typing import TypeVar

from .utils import PRECISION


LF = "\n"
SPACE = " "

Self = TypeVar("Self", bound="G")


class G:
    def __init__(self, out_file_path: str | PurePath, *, is_si=True) -> Self:
        self.out_file_path = out_file_path
        self.out_file_descriptor = open(self.out_file_path, "w")
        self.rapid_height = 0.0
        self.position = {k: 0.0 for k in "xyz"}
        self.feed_rate = 0.0
        self.spindle_rpm = 0
        self.spindle_is_clockwise = None
        self.mode = ""
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
        self.position = self.updated_position(kwargs)
        cmd = "G0" if self.is_rapid(kwargs) else "G1"
        fmt = self.format(**kwargs)
        self.write(fmt if self.mode == cmd else f"{cmd} {fmt}")
        self.mode = cmd
        return self

    def dwell(self, time: float) -> Self:
        if isclose(time, 0.0):
            return self
        return self.write(f"G4 {self.format(p=time)}")

    def feed(self, feed_rate: float) -> Self:
        if isclose(self.feed_rate, feed_rate):
            return self
        self.feed_rate = max(0.0, feed_rate)
        return self.write(f"G1 {self.format(f=self.feed_rate)}")

    def spindle(self, spindle_rpm=0, is_clockwise=True) -> Self:
        is_same = self.spindle_rpm == spindle_rpm
        if is_same and spindle_rpm > 0:
            return self
        cmd = f"S{spindle_rpm}"

        if spindle_rpm == 0:
            cmd = "M5"
        elif self.spindle_is_clockwise != is_clockwise:
            cmd += " M3" if is_clockwise else " M4"

        self.spindle_rpm = max(0, spindle_rpm)
        self.spindle_is_clockwise = is_clockwise
        return self.write(cmd)

    def end(self) -> Self:
        return self.write("M2")

    def is_rapid(self, position: dict) -> bool:
        z = position.get("z", self.position["z"])
        return (
            isclose(z, self.rapid_height)
            or z > self.rapid_height
            and not self.is_down_move(position)
            or self.is_up_move(position)
        )

    def is_down_move(self, position: dict) -> bool:
        return (
            isclose(self.position["x"], position["x"])
            and isclose(self.position["y"], position["y"])
            and self.position["z"] > position["z"]
        )

    def is_up_move(self, position: dict) -> bool:
        return (
            isclose(self.position["x"], position["x"])
            and isclose(self.position["y"], position["y"])
            and self.position["z"] < position["z"]
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
