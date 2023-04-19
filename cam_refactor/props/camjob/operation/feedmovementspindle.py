import math

import bpy

from ... import utils


class Feed(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "rate"}

    rate: bpy.props.FloatProperty(name="Feed Rate", default=1, min=1e-1, unit="LENGTH")
    plunge_speed: bpy.props.FloatProperty(
        name="Plunge Speed", default=5e-1, min=5e-2, max=1, subtype="PERCENTAGE"
    )
    plunge_angle: bpy.props.FloatProperty(
        name="Plunge Angle",
        default=math.pi / 6,
        min=0,
        max=math.pi / 2,
        subtype="ANGLE",
        unit="ROTATION",
    )


class Movement(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    rapid_height: bpy.props.FloatProperty(
        name="Rapid Height",
        min=1e-5,
        default=5e-3,
        precision=utils.PRECISION,
        unit="LENGTH",
    )
    type: bpy.props.EnumProperty(
        name="Movement Type",
        items=[
            ("CLIMB", "Climb", "Cutter rotates with the direction of the feed"),
            (
                "CONVENTIONAL",
                "Conventional",
                "Cutter rotates against the direction of the feed",
            ),
            (
                "MEANDER",
                "Meander",
                "Cutting is done both with and against the rotation of the spindle",
            ),
        ],
    )
    # vertical_angle: bpy.props.FloatProperty(
    #     name="Vertical Angle",
    #     description="Convert path above this angle to a vertical path for cutter protection",
    #     default=math.pi / 45,
    #     min=0,
    #     max=math.pi / 2,
    #     precision=0,
    #     subtype="ANGLE",
    #     unit="ROTATION",
    # )


class Spindle(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    direction_type: bpy.props.EnumProperty(
        name="Spindle Direction",
        items=[
            ("CLOCKWISE", "Clockwise", "", "LOOP_FORWARDS", 0),
            ("COUNTER_CLOCKWISE", "Counter-Clockwise", "", "LOOP_BACK", 1),
        ],
    )

    rpm: bpy.props.IntProperty(name="Spindle RPM", default=12000)
