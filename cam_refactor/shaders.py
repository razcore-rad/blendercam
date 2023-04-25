import bpy
import bmesh
import gpu
from bpy.types import Context
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from .props.camjob.operation import Operation
from .utils import noop


def gen_unit_circle_vectors() -> list[Vector]:
    bm = bmesh.new()
    result = [
        v.co.copy() for v in bmesh.ops.create_circle(bm, segments=12, radius=1)["verts"]
    ]
    bm.free()
    return result


UNIT_CIRCLE_VECTORS = gen_unit_circle_vectors()

STOCK_INDICES = [
    # bottom
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 0),
    # top
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 4),
    # vertical lines
    (0, 4),
    (1, 5),
    (2, 6),
    (3, 7),
]

SHADER = gpu.shader.from_builtin("3D_UNIFORM_COLOR")


def draw_stock() -> None:
    context = bpy.context
    if not (
        context.mode == "OBJECT"
        and context.scene.cam_jobs
        and context.scene.cam_job.operations
    ):
        return

    cam_job = context.scene.cam_job
    bb_min, bb_max = cam_job.get_stock_bound_box(context)
    coords = [
        # bottom
        Vector((bb_min.x, bb_min.y, bb_min.z)),
        Vector((bb_max.x, bb_min.y, bb_min.z)),
        Vector((bb_max.x, bb_max.y, bb_min.z)),
        Vector((bb_min.x, bb_max.y, bb_min.z)),
        # top
        Vector((bb_min.x, bb_min.y, bb_max.z)),
        Vector((bb_max.x, bb_min.y, bb_max.z)),
        Vector((bb_max.x, bb_max.y, bb_max.z)),
        Vector((bb_min.x, bb_max.y, bb_max.z)),
    ]

    gpu.state.depth_test_set("LESS_EQUAL")
    SHADER.uniform_float("color", (1, 1, 1, 1))
    batch = batch_for_shader(SHADER, "LINES", {"pos": coords}, indices=STOCK_INDICES)
    batch.draw(SHADER)


def draw_drill_features(context: Context, operation: Operation) -> None:
    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.line_width_set(3)
    SHADER.uniform_float("color", (1, 1, 1, 1))
    cutter_radius = operation.cutter.radius
    positions = operation.strategy.get_feature_positions(context, operation)
    for position in positions:
        coords = [v * cutter_radius + position for v in UNIT_CIRCLE_VECTORS]
        batch_for_shader(SHADER, "LINE_LOOP", {"pos": coords}).draw(SHADER)

    positions = [(p.x, p.y, operation.get_depth_end(context)) for p in positions]
    batch = batch_for_shader(SHADER, "POINTS", {"pos": positions})
    batch.draw(SHADER)
    gpu.state.line_width_set(1)


DRAW_FEAURES_FUNCS = {"DRILL": draw_drill_features}


def draw_features() -> None:
    context = bpy.context
    if not (context.mode == "OBJECT" and context.scene.cam_jobs):
        return

    for operation in context.scene.cam_job.operations:
        if operation.is_hidden:
            continue
        DRAW_FEAURES_FUNCS.get(operation.strategy_type, noop)(context, operation)
