# FIXME:
# - update all property descriptions
# - update all post_processor PointerProperty types
# - add missing G-code options
# - add cutters
import importlib

import bpy

mods = {".machine", ".operation", ".stock"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})


class CAMJob(bpy.types.PropertyGroup):
    NAME = "CAMJob"

    data: bpy.props.PointerProperty(type=bpy.types.Collection)
    count: bpy.props.IntVectorProperty(name="Count", default=(1, 1), min=1, subtype="XYZ", size=2)
    gap: bpy.props.FloatVectorProperty(name="Gap", default=(0, 0), min=0, subtype="XYZ_LENGTH", size=2)
    operations: bpy.props.CollectionProperty(type=operation.Operation)
    operation_active_index: bpy.props.IntProperty(default=0, min=0)
    stock: bpy.props.PointerProperty(type=stock.Stock)
    machine: bpy.props.PointerProperty(type=machine.Machine)

    @property
    def operation(self) -> operation.Operation:
        return self.operations[self.operation_active_index]

    def add_data(self, context: bpy.types.Context) -> None:
        self.data = bpy.data.collections.new(self.NAME)
        bpy.context.collection.children.link(self.data)
        operation = self.operations.add()
        operation.add_data(context)

    def remove_data(self) -> None:
        for operation in self.operations:
            operation.remove_data()
        bpy.data.collections.remove(self.data)
