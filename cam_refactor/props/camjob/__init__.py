# FIXME:
# - update all property descriptions
# - update all post_processor PointerProperty types
# - add missing G-code options
# - add cutters
import importlib
from operator import add, sub

import bmesh
import bpy
from mathutils import Vector

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
        # TODO: cover CURVE type. At the moment it works only with MESH
        objs = []
        for operation in self.operations:
            if isinstance(operation.strategy.source, bpy.types.Object):
                objs.append(operation.strategy.source)
            elif isinstance(operation.strategy.source, bpy.types.Collection):
                objs.extend(operation.strategy.source.objects)

        points = []
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for obj in objs:
            bm = bmesh.new()
            bm.from_object(obj, depsgraph)
            points.extend(obj.matrix_world @ v.co for v in bm.verts)
            bm.free()

        return (
            tuple(
                op(Vector(f(coords) for coords in zip(*points)), self.stock.estimate_offset)
                for f, op in ((min, sub), (max, add))
            )
            if len(objs) > 0
            else (Vector(), Vector())
        )

    def add_data(self, context: bpy.types.Context) -> None:
        self.data = bpy.data.collections.new(self.NAME)
        bpy.context.collection.children.link(self.data)
        operation = self.operations.add()
        operation.add_data(context)

    def remove_data(self) -> None:
        for operation in self.operations:
            operation.remove_data()
        bpy.data.collections.remove(self.data)
