import bpy
import gpu
from itertools import chain, tee
from bpy.types import Context
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from shapely import Point, Polygon, force_3d
from shapely import affinity

from .props.camjob.operation import Operation
from .utils import noop

BUFFER_RESOLUTION = 12
UNIT_CIRCLE_VECTORS = [
    Vector(cs) for cs in force_3d(Point(0, 0).buffer(1, resolution=BUFFER_RESOLUTION).exterior, 0.0).coords
]
SQUARE_INDICES = [(0, 1), (1, 2), (2, 3), (3, 0)]

SHADER = gpu.shader.from_builtin("UNIFORM_COLOR")


def draw_drill_features(context: Context, operation: Operation) -> None:
    features = operation.strategy.get_feature_positions(context, operation)
    if operation.tool_id < 0 or not features:
        return

    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.line_width_set(3)
    SHADER.uniform_float("color", (1, 1, 1, 1))
    cutter_radius = operation.get_cutter(context).radius

    batches = []
    positions = []
    for pos, depth_end in features.items():
        coords = [v * cutter_radius + pos for v in UNIT_CIRCLE_VECTORS]
        batches.append(batch_for_shader(SHADER, "LINE_LOOP", {"pos": coords}))

        positions.append((pos.x, pos.y, depth_end))
    batches.append(batch_for_shader(SHADER, "POINTS", {"pos": positions}))

    for batch in batches:
        batch.draw(SHADER)
    gpu.state.line_width_set(1)


def draw_pocket_features(context: Context, operation: Operation) -> None:
    positions = operation.strategy.get_feature_positions(context, operation)
    if operation.tool_id < 0 or not positions:
        return

    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.line_width_set(3)
    SHADER.uniform_float("color", (1, 1, 1, 1))
    batch = batch_for_shader(SHADER, "LINES", {"pos": [tuple(p) for p in positions]}, indices=SQUARE_INDICES)
    scaled_positions = affinity.scale(Polygon(positions), 0.5, 0.5).exterior.coords
    for batch in [batch, batch_for_shader(SHADER, "LINES", {"pos": scaled_positions}, indices=SQUARE_INDICES)]:
        batch.draw(SHADER)
        gpu.state.line_width_set(1)


def draw_profile_features(context: Context, operation: Operation) -> None:
    positions = operation.strategy.get_feature_positions(context, operation)
    if operation.tool_id < 0 or not positions:
        return

    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.line_width_set(3)
    SHADER.uniform_float("color", (1, 1, 1, 1))
    positions = [tuple(p) for p in positions]
    batch_for_shader(SHADER, "LINES", {"pos": positions}, indices=SQUARE_INDICES).draw(SHADER)
    gpu.state.line_width_set(1)


DRAW_FEAURES_FUNCS = {
    "DRILL": draw_drill_features,
    "PROFILE": draw_profile_features,
    "POCKET": draw_pocket_features,
}


def draw_features() -> None:
    context = bpy.context
    if not (context.mode == "OBJECT" and context.scene.cam_jobs):
        return

    for operation in context.scene.cam_job.operations:
        if operation.is_hidden:
            continue
        DRAW_FEAURES_FUNCS.get(operation.strategy_type, noop)(context, operation)
