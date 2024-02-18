from math import pi

from bl_math import clamp
from bpy.props import FloatProperty
from bpy.types import PropertyGroup

from .utils import update_cam_tools_library
from ...utils import (
    EPSILON,
    PRECISION,
    get_scaled_prop,
    set_scaled_prop,
)


def set_ball_cutter_corner_radius(self, value: float) -> None:
    self["corner_radius"] = clamp(value, 0.0, self.radius - EPSILON)


def set_ball_cone_cutter_corner_radius(self, value: float) -> None:
    self["corner_radius"] = clamp(value, 0.0, self.lower_radius - EPSILON)


def set_lower_diameter_cutter(self, value: float) -> None:
    self["lower_diameter"] = clamp(value, 0.0, self.upper_diameter - EPSILON)


def set_upper_diameter_cutter(self, value: float) -> None:
    self["upper_diameter"] = max(value, self.lower_diameter + EPSILON)


def set_cone_cone_lower_angle(self, value: float) -> None:
    self["lower_angle"] = clamp(value, self.upper_angle + EPSILON, pi - EPSILON)


def set_cone_cone_upper_angle(self, value: float) -> None:
    self["upper_angle"] = clamp(value, pi / 180, self.lower_angle - EPSILON)


class BaseMixin:
    EXCLUDE_PROPNAMES = ["name"]


class LengthMixin:
    length: FloatProperty(
        name="Length",
        unit="LENGTH",
        get=lambda s: get_scaled_prop("length", 1e-1, s),
        set=lambda s, v: set_scaled_prop("length", 1e-3, None, s, v),
        update=update_cam_tools_library,
    )


class DiameterMixin:
    diameter: FloatProperty(
        name="Diameter",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("diameter", 3e-3, s),
        set=lambda s, v: set_scaled_prop("diameter", 0, None, s, v),
        update=update_cam_tools_library,
    )

    @property
    def radius(self) -> float:
        return self.diameter / 2.0


class Diameter2Mixin:
    lower_diameter: FloatProperty(
        name="Lower Diameter",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("lower_diameter", 3e-3, s),
        set=set_lower_diameter_cutter,
        update=update_cam_tools_library,
    )

    upper_diameter: FloatProperty(
        name="Upper Diameter",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("upper_diameter", 3e-3, s),
        set=set_upper_diameter_cutter,
        update=update_cam_tools_library,
    )

    @property
    def diameter(self) -> float:
        return self.upper_diameter

    @property
    def lower_radius(self) -> float:
        return self.lower_diameter / 2.0

    @property
    def upper_radius(self) -> float:
        return self.upper_diameter / 2.0

    @property
    def radius(self) -> float:
        return self.diameter / 2.0


class AngleMixin:
    angle: FloatProperty(
        name="Angle",
        subtype="ANGLE",
        default=pi / 4,
        min=pi / 180,
        max=pi - EPSILON,
        update=update_cam_tools_library,
    )


class SimpleCutter(BaseMixin, DiameterMixin, PropertyGroup):
    pass


class CylinderCutter(BaseMixin, DiameterMixin, LengthMixin, PropertyGroup):
    pass


class BallCutter(BaseMixin, DiameterMixin, LengthMixin, PropertyGroup):
    pass


class BullCutter(BaseMixin, DiameterMixin, LengthMixin, PropertyGroup):
    corner_radius: FloatProperty(
        name="Corner Radius",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("corner_radius", 1e-3, s),
        set=set_ball_cutter_corner_radius,
        update=update_cam_tools_library,
    )


class ConeCutter(BaseMixin, DiameterMixin, AngleMixin, LengthMixin, PropertyGroup):
    pass


class CylinderConeCutter(BaseMixin, Diameter2Mixin, AngleMixin, LengthMixin, PropertyGroup):
    pass


class BallConeCutter(BaseMixin, Diameter2Mixin, AngleMixin, LengthMixin, PropertyGroup):
    pass


class BullConeCutter(BaseMixin, Diameter2Mixin, AngleMixin, LengthMixin, PropertyGroup):
    corner_radius: FloatProperty(
        name="Corner Radius",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("corner_radius", 1e-3, s),
        set=set_ball_cone_cutter_corner_radius,
        update=update_cam_tools_library,
    )


class ConeConeCutter(BaseMixin, Diameter2Mixin, LengthMixin, PropertyGroup):
    lower_angle: FloatProperty(
        name="Lower Angle",
        subtype="ANGLE",
        get=lambda s: s.get("lower_angle", pi / 2),
        set=set_cone_cone_lower_angle,
        update=update_cam_tools_library,
    )
    upper_angle: FloatProperty(
        name="Upper Angle",
        subtype="ANGLE",
        get=lambda s: s.get("upper_angle", pi / 4),
        set=set_cone_cone_upper_angle,
        update=update_cam_tools_library,
    )
