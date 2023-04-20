from functools import reduce
from operator import add, sub
from pathlib import Path
from typing import Callable

import bpy
import bmesh
from bpy.props import (
    CollectionProperty,
    FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
)
from bpy.types import Collection, Context, Object, PropertyGroup
from mathutils import Vector

from . import machine, operation, stock
from .. import utils
from ... import gcode


class CAMJob(PropertyGroup):
    NAME = "CAMJob"

    data: PointerProperty(type=Collection)
    object: PointerProperty(type=Object)
    count: IntVectorProperty(name="Count", default=(1, 1), min=1, subtype="XYZ", size=2)
    gap: FloatVectorProperty(
        name="Gap", default=(0, 0), min=0, subtype="XYZ_LENGTH", size=2
    )
    operations: CollectionProperty(type=operation.Operation)
    operation_active_index: IntProperty(default=0, min=0)
    stock: PointerProperty(type=stock.Stock)
    machine: PointerProperty(type=machine.Machine)

    @property
    def operation(self) -> operation.Operation:
        return self.operations[self.operation_active_index]

    def get_stock_bound_box(self, context: Context) -> tuple[Vector, Vector]:
        result = (Vector(), Vector())
        if self.stock.type == "ESTIMATE":
            bound_boxes = reduce(
                lambda acc, o: acc + [o.get_bound_box(context)], self.operations, []
            )
            if sum((bb_max - bb_min).length for (bb_min, bb_max) in bound_boxes) > 0:
                result = tuple(
                    op(Vector(f(cs) for cs in zip(*vs)), eo)
                    for (f, op, eo), vs in zip(
                        (
                            (min, sub, self.stock.estimate_offset),
                            (max, add, self.stock.estimate_offset),
                        ),
                        zip(*bound_boxes),
                    )
                )
        elif self.stock.type == "CUSTOM":
            result = tuple(
                self.stock.custom_location.to_3d() + v
                for v in (Vector(), self.stock.custom_size)
            )
        return result

    def add_data(self, context: Context) -> None:
        if self.data is None:
            self.data = bpy.data.collections.new(self.NAME)
            context.collection.children.link(self.data)

        if self.object is None:
            self.object = bpy.data.objects.new(
                self.NAME, bpy.data.meshes.new(self.NAME)
            )
            self.object.lock_location = 3 * [True]
            self.object.lock_rotation = 3 * [True]
            self.data.objects.link(self.object)
        elif self.object.name not in context.view_layer.objects:
            self.data.objects.link(self.object)

        if len(self.operations) == 0:
            operation = self.operations.add()
            operation.add_data(context)

    def remove_data(self) -> None:
        if self.object is not None:
            bpy.data.meshes.remove(self.object.data)

        if self.data is not None:
            bpy.data.collections.remove(self.data)

    def execute_compute(self, context: Context, report: Callable) -> set[str]:
        result, vectors = set(), []

        for index, operation in enumerate(self.operations):
            if index == 0:
                vectors.append(Vector((0.0, 0.0, operation.movement.rapid_height)))
            partial_result, msg, partial_vectors = operation.execute_compute(context)
            vectors.extend(partial_vectors)
            msg != "" and report({"ERROR"}, msg)
            result.update(partial_result)
        (result_item,) = result = utils.reduce_cancelled_or_finished(result)

        if result_item == "CANCELLED":
            report({"ERROR"}, f"CAM Job {self.data.name} canceled")
        else:
            self.add_data(context)
            context.view_layer.objects.active = self.object
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            self.object.select_set(True)
            bpy.ops.object.location_clear(clear_delta=True)
            bpy.ops.object.rotation_clear(clear_delta=True)
            bpy.ops.object.scale_clear(clear_delta=True)

            bm = bmesh.new()
            for v in vectors:
                bm.verts.new(v)
            bm.verts.index_update()
            for pair in zip(bm.verts[:-1], bm.verts[1:]):
                bm.edges.new(pair)
            bm.edges.index_update()
            bm.to_mesh(self.object.data)
            bm.free()

        return result

    def execute_export(self) -> set[str]:
        out_file_path = Path(bpy.path.abspath("//")).joinpath(f"{self.data.name}.gcode")
        with gcode.G(out_file_path) as g:
            g.feed(400)
            for vertex in self.object.data.vertices:
                g.abs_move(**{k: v * 1e3 for k, v in zip("xyz", vertex.co)})
        return {"FINISHED"}
