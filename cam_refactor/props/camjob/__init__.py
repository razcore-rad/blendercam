import importlib
from functools import reduce
from math import isclose
from operator import add, sub

import bpy
from mathutils import Vector

from .. import utils

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

    @property
    def stock_bound_box(self) -> tuple[Vector]:
        result = (Vector(), Vector())
        z_compare = 0
        if self.stock.type == "ESTIMATE":
            objs = reduce(lambda acc, o: acc + o.strategy.source, self.operations, [])
            if len(objs) > 0:
                bound_boxes = (utils.get_bound_box(o) for o in objs)
                result = tuple(
                    op(Vector(f(cs) for cs in zip(*vs)), eo)
                    for (f, op, eo), vs in zip(
                        ((min, sub, self.stock.estimate_offset.xy.resized(3)), (max, add, self.stock.estimate_offset)),
                        zip(*bound_boxes),
                    )
                )
                z_compare = self.stock.estimate_offset.z
        elif self.stock.type == "CUSTOM":
            result = tuple(self.stock.custom_location.to_3d() + v for v in (Vector(), self.stock.custom_size))
        return (Vector(), Vector()) if isclose(z_compare, result[1].z) else result

    def add_data(self, context: bpy.types.Context) -> None:
        if self.data is None:
            self.data = bpy.data.collections.new(self.NAME)
            context.collection.children.link(self.data)
        op = self.operations.add()
        op.add_data(context)

    def remove_data(self) -> None:
        for operation in self.operations:
            operation.remove_data()
        if self.data is not None:
            bpy.data.collections.remove(self.data)
