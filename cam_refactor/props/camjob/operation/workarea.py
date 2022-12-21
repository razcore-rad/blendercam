import importlib

import bpy
from mathutils import Vector

mods = {"...utils"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})


def get_depth_dicts(work_area: bpy.types.PropertyGroup, context: bpy.types.Context) -> tuple[dict]:
    DEPTH_START_DICT = {
        "name": "Depth Start",
        "default": 0,
        "min": -context.scene.cam_job.machine.work_space.z,
        "max": 0,
        "precision": utils.PRECISION,
        "unit": "LENGTH",
        "update": update_depth_start,
    }
    DEPTH_END_DICT = {
        "name": "Depth End",
        "default": DEPTH_START_DICT["min"],
        "min": DEPTH_START_DICT["min"],
        "max": work_area.depth_start,
        "precision": utils.PRECISION,
        "unit": "LENGTH",
    }
    return DEPTH_START_DICT, DEPTH_END_DICT


def update_depth_start(work_area: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    depth_start_dict, depth_end_dict = get_depth_dicts(work_area, context)
    depth_end_dict["min"] = depth_start_dict["min"]
    depth_end_dict["max"] = work_area.depth_start

    depth_end = work_area.depth_end
    WorkArea.depth_end = bpy.props.FloatProperty(**depth_end_dict)
    work_area.depth_end = depth_end


def update_depth_end_type(work_area: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    depth_start_dict, depth_end_dict = get_depth_dicts(work_area, context)
    if work_area.depth_end_type == "SOURCE":
        # TODO: also update on `work_area.depth_end_type == STOCK`
        # FIXME: apply transforms and modifiers before `bound_box`
        source = context.scene.cam_job.operation.strategy.source
        depth_start_dict["min"] = clamp(
            min((obj.matrix_world @ Vector(v)).z for obj in source for v in obj.bound_box),
            depth_start_dict["min"],
            depth_start_dict["max"],
        )
        depth_end_dict["min"] = depth_start_dict["min"]
        depth_end_dict["max"] = work_area.depth_start

    depth_start = work_area.depth_start
    depth_end = work_area.depth_end
    WorkArea.depth_start = bpy.props.FloatProperty(**depth_start_dict)
    WorkArea.depth_end = bpy.props.FloatProperty(**depth_end_dict)
    work_area.depth_start = depth_start
    work_area.depth_end = depth_end


class WorkArea(bpy.types.PropertyGroup):
    ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}
    EXCLUDE_PROPNAMES = {"name", "depth_start", "depth_end_type", "depth_end"}

    depth_start: bpy.props.FloatProperty(name="Depth Start")
    depth_end: bpy.props.FloatProperty(name="Depth End")
    depth_end_type: bpy.props.EnumProperty(
        name="Depth End",
        items=[
            ("CUSTOM", "Custom", ""),
            ("SOURCE", "Source", ""),
            ("STOCK", "Stock", ""),
        ],
        update=update_depth_end_type,
    )
    layer_size: bpy.props.FloatProperty(
        name="Layer Size", default=0, min=0, max=1e-1, precision=utils.PRECISION, unit="LENGTH"
    )
    ambient_type: bpy.props.EnumProperty(
        name="Ambient", items=[("OFF", "Off", ""), ("ALL", "All", ""), ("AROUND", "Around", "")]
    )
    curve_limit: bpy.props.PointerProperty(name="Curve Limit", type=bpy.types.Object, poll=utils.poll_curve_limit)
