import math

from bpy.props import FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from .... import utils


class CutterMixin:
    EXCLUDE_PROPNAMES = {"name", "description", "id"}

    id: IntProperty(name="ID", default=1, min=1, max=10)
    description: StringProperty(name="Description")
    diameter: FloatProperty(
        name="Diameter",
        default=3e-3,
        min=1 / 10**utils.PRECISION,
        max=1e-1,
        precision=utils.PRECISION,
        unit="LENGTH",
    )


class FlutesMixin:
    flutes: IntProperty(name="Flutes", default=2, min=1, max=10)


class LengthMixin:
    length: FloatProperty(name="Length", default=1e-1, min=5e-2, max=100)


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
