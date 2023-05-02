import math

import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty
from bpy.types import Context, PropertyGroup

from ....types import ShortEnumItems
from ....utils import PRECISION, get_scaled_prop, set_scaled_prop


def set_movement_rapid_height(self: PropertyGroup, value: float) -> None:
    self["rapid_height"] = max(self.rapid_height_min, value)


def update_movement_rapid_height_min() -> None:
    context = bpy.context
    if not (context.scene.cam_jobs and context.scene.cam_job.operations):
        return
    operation = context.scene.cam_job.operation
    _, bb_max = operation.get_bound_box(context)
    operation.movement.rapid_height_min = bb_max.z


def movement_type_items(self, context: Context) -> ShortEnumItems:
    result = []
    if not context.scene.cam_jobs and not context.scene.cam_jobs.operations:
        return result

    result = [
        ("CLIMB", "Climb", "Cutter rotates with the direction of the feed"),
        (
            "CONVENTIONAL",
            "Conventional",
            "Cutter rotates against the direction of the feed",
        ),
    ]
    if context.scene.cam_job.operation.strategy_type != "PROFILE":
        result.append(("BOTH", "Both Ways", "Optimize for tool path length"))
    return result


class Feed(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "rate"}

    rate: FloatProperty(
        name="Feed Rate",
        unit="LENGTH",
        get=lambda s: get_scaled_prop("rate", 1e0, s),
        set=lambda s, v: set_scaled_prop("rate", 1e-1, None, s, v),
    )
    plunge_scale: FloatProperty(name="Plunge Scale", default=5e-1, min=5e-2, max=1)
    plunge_angle: FloatProperty(
        name="Plunge Angle",
        default=math.pi / 6,
        min=0,
        max=math.pi / 2,
        subtype="ANGLE",
        unit="ROTATION",
    )


class Movement(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "rapid_height_min"}

    rapid_height_min: FloatProperty(default=0.0)
    rapid_height: FloatProperty(
        name="Rapid Height",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("rapid_height", 5e-3, s),
        set=set_movement_rapid_height,
    )
    type: EnumProperty(name="Movement Type", items=movement_type_items)


class Spindle(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    direction_type: EnumProperty(
        name="Spindle Direction",
        items=[
            ("CW", "Clockwise", "", "LOOP_FORWARDS", 0),
            ("CCW", "Counter-Clockwise", "", "LOOP_BACK", 1),
        ],
    )

    rpm: IntProperty(name="Spindle RPM", default=12000)
