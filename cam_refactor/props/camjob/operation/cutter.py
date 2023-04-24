import math

from bpy.props import FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from ....utils import PRECISION, get_scaled_prop, set_scaled_prop


class CutterMixin:
    EXCLUDE_PROPNAMES = {"name", "description", "id"}

    id: IntProperty(name="ID", default=1, min=1, max=10)
    description: StringProperty(name="Description")
    diameter: FloatProperty(
        name="Diameter",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("diameter", 3e-3, s),
        set=lambda s, v: set_scaled_prop("diameter", 1 / 10**PRECISION, 1e-1, s, v),
    )


class FlutesMixin:
    flutes: IntProperty(name="Flutes", default=2, min=1, max=10)


class LengthMixin:
    length: FloatProperty(
        name="Length",
        unit="LENGTH",
        get=lambda s: get_scaled_prop("length", 1e-1, s),
        set=lambda s, v: set_scaled_prop("length", 1e-3, 5e-1, s, v),
    )


class Simple(CutterMixin, PropertyGroup):
    pass


class Drill(CutterMixin, LengthMixin, PropertyGroup):
    pass


class Mill(CutterMixin, FlutesMixin, LengthMixin, PropertyGroup):
    pass


class ConeMill(CutterMixin, LengthMixin, PropertyGroup):
    angle: FloatProperty(
        name="Angle", default=math.pi / 4, min=math.pi / 180, max=math.pi / 2
    )
