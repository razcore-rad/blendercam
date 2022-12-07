import importlib

import bpy

modnames = ["utils"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f"...{modname}", __package__)) for modname in modnames}
)


class CutterMixin:
    EXCLUDE_PROPNAMES = {"name", "id"}

    id: bpy.props.IntProperty(name="ID", default=1, min=1, max=10)
    description: bpy.props.StringProperty(name="Description")
    diameter: bpy.props.FloatProperty(
        name="Diameter", default=3e-3, min=1 / 10**utils.PRECISION, max=1e-1, precision=utils.PRECISION, unit="LENGTH"
    )


class Simple(CutterMixin, bpy.types.PropertyGroup):
    pass


class Mill(CutterMixin, bpy.types.PropertyGroup):
    flutes: bpy.props.IntProperty(name="Flutes", default=2, min=1, max=10)
    length: bpy.props.FloatProperty(name="Length", default=10, min=10, max=100)
