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
from ...gcode import G
from ...utils import LENGTH_UNIT_SCALE, ZERO_VECTOR, reduce_cancelled_or_finished


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
            bound_boxes = (o.get_bound_box(context) for o in self.operations)
            bound_boxes = [
                (bb_min, bb_max)
                for bb_min, bb_max in bound_boxes
                if bb_max - bb_min != ZERO_VECTOR
            ]
            if sum((bb_max - bb_min).length for bb_min, bb_max in bound_boxes) > 0:
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
            position = self.stock.custom_position.to_3d()
            size = self.stock.custom_size
            result = tuple(
                position + v
                for v in (Vector((0.0, 0.0, -size.z)), Vector((size.x, size.y, 0.0)))
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
            self.operations.add()
            operation = self.operations[-1]
            operation.add_data(context)

    def remove_data(self, context: Context) -> None:
        if self.object is not None:
            bpy.data.meshes.remove(self.object.data)

        if self.data is not None:
            bpy.data.collections.remove(self.data)

    def execute_compute(self, context: Context, report: Callable) -> set[str]:
        result, computed = set(), []
        if not all(
            op.tool_id >= 0 and op.strategy.get_source(context)
            for op in self.operations
        ):
            report({"ERROR"}, "Check all operations have sources and tools.")
            return {"CANCELLED"}

        if self.operations:
            computed.append(self.operations[0].zero)

        partial_computed = []
        for operation in self.operations:
            partial_result, partial_computed = operation.execute_compute(context)
            result.update(partial_result)
            computed.extend(partial_computed)
        (result_item,) = result = reduce_cancelled_or_finished(result)

        if result_item == "CANCELLED":
            report({"ERROR"}, f"CAM Job {self.data.name} couldn't be computed.")
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
            rapid_height = bm.verts.layers.float.new("rapid_height")
            dwell = bm.verts.layers.float.new("dwell")
            feed_rate = bm.verts.layers.float.new("feed_rate")
            plunge_scale = bm.verts.layers.float.new("plunge_scale")
            spindle_direction = bm.verts.layers.int.new("spindle_direction")
            spindle_rpm = bm.verts.layers.int.new("spindle_rpm")
            for c in computed:
                vert = bm.verts.new(c["vector"])
                vert[rapid_height] = c["rapid_height"]
                vert[dwell] = c["dwell"]
                vert[feed_rate] = c["feed_rate"]
                vert[plunge_scale] = c["plunge_scale"]
                vert[spindle_direction] = (
                    0 if c["spindle_direction"] == "CLOCKWISE" else 1
                )
                vert[spindle_rpm] = c["spindle_rpm"]
            bm.verts.index_update()
            for pair in zip(bm.verts[:-1], bm.verts[1:]):
                bm.edges.new(pair)
            bm.edges.index_update()
            bm.to_mesh(self.object.data)
            bm.free()
        return result

    def execute_export(self, context: Context) -> set[str]:
        out_file_path = Path(bpy.path.abspath("//")).joinpath(f"{self.data.name}.nc")
        scale_length = LENGTH_UNIT_SCALE * context.scene.unit_settings.scale_length
        with G(out_file_path) as g:
            vertices = self.object.data.vertices
            dwell = self.object.data.attributes["dwell"].data
            rapid_heights = self.object.data.attributes["rapid_height"].data
            feed_rates = self.object.data.attributes["feed_rate"].data
            plunge_scales = self.object.data.attributes["plunge_scale"].data
            spindle_directions = self.object.data.attributes["spindle_direction"].data
            spindle_rpm = self.object.data.attributes["spindle_rpm"].data

            if feed_rates and spindle_rpm:
                g.feed(feed_rates[0].value * scale_length).spindle(
                    spindle_rpm[0].value, spindle_directions[0].value == 0
                )

            for v, rh, d, fr, ps, sd, sr in zip(
                vertices,
                rapid_heights,
                dwell,
                feed_rates,
                plunge_scales,
                spindle_directions,
                spindle_rpm,
            ):
                position = {k: v * scale_length for k, v in zip("xyz", v.co)}
                feed_rate = fr.value * scale_length
                g.rapid_height = rh.value * scale_length
                if g.is_down_move(position):
                    feed_rate *= ps.value

                g.spindle(sr.value, sd.value == 0)
                if not g.is_rapid(position):
                    g.feed(feed_rate)
                g.abs_move(**position).dwell(d.value)
            g.spindle(0)
        return {"FINISHED"}
