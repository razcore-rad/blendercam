import math

import bpy

from ... import utils


class CutterMixin:
    EXCLUDE_PROPNAMES = {"name", "description", "id"}

    id: bpy.props.IntProperty(name="ID", default=1, min=1, max=10)
    description: bpy.props.StringProperty(name="Description")
    diameter: bpy.props.FloatProperty(
        name="Diameter",
        default=3e-3,
        min=1 / 10**utils.PRECISION,
        max=1e-1,
        precision=utils.PRECISION,
        unit="LENGTH",
    )

    def get_radius(self, _depth: float) -> float:
        return self.diameter / 2.0


class FlutesMixin:
    flutes: bpy.props.IntProperty(name="Flutes", default=2, min=1, max=10)


class LengthMixin:
    length: bpy.props.FloatProperty(name="Length", default=1e-1, min=5e-2, max=100)


class Simple(CutterMixin, bpy.types.PropertyGroup):
    pass


class Drill(CutterMixin, LengthMixin, bpy.types.PropertyGroup):
    pass


class Mill(CutterMixin, FlutesMixin, LengthMixin, bpy.types.PropertyGroup):
    pass


class ConeMill(CutterMixin, LengthMixin, bpy.types.PropertyGroup):
    angle: bpy.props.FloatProperty(
        name="Angle", default=math.pi / 4, min=math.pi / 180, max=math.pi / 2
    )

