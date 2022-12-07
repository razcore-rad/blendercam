# FIXME:
# - update all property descriptions
# - update all post_processor PointerProperty types
# - add missing G-code options
# - add cutters
import importlib

import bpy

modnames = ["machine", "operation", "stock"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f".{modname}", __package__)) for modname in modnames}
)


class CAMJob(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Job")
    is_hidden: bpy.props.BoolProperty(default=False)
    count: bpy.props.IntVectorProperty(name="Count", default=(1, 1), min=1, subtype="XYZ", size=2)
    gap: bpy.props.FloatVectorProperty(name="Gap", default=(0, 0), min=0, subtype="XYZ_LENGTH", size=2)
    operations: bpy.props.CollectionProperty(type=operation.Operation)
    operation_active_index: bpy.props.IntProperty(default=0, min=0)
    stock: bpy.props.PointerProperty(type=stock.Stock)
    machine: bpy.props.PointerProperty(type=machine.Machine)

    @property
    def operation(self) -> operation.Operation:
        return self.operations[self.operation_active_index]
