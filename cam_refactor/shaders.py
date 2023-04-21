import bpy
import bmesh
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector


def gen_unit_circle_vectors() -> list[Vector]:
    bm = bmesh.new()
    result = [
        v.co.copy()
        for v in bmesh.ops.create_circle(bm, segments=12, radius=0.5)["verts"]
    ]
    bm.free()
    return result


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


UNIT_CIRCLE_VECTORS = gen_unit_circle_vectors()


def draw_stock() -> None:
    context = bpy.context
    if len(context.scene.cam_jobs) == 0 or len(context.scene.cam_job.operations) == 0:
        return

    (
        stock_bound_box_min,
        stock_bound_box_max,
    ) = context.scene.cam_job.get_stock_bound_box(context)
    coords = [
        # bottom
        Vector((stock_bound_box_min.x, stock_bound_box_min.y, stock_bound_box_min.z)),
        Vector((stock_bound_box_max.x, stock_bound_box_min.y, stock_bound_box_min.z)),
        Vector((stock_bound_box_max.x, stock_bound_box_max.y, stock_bound_box_min.z)),
        Vector((stock_bound_box_min.x, stock_bound_box_max.y, stock_bound_box_min.z)),
        # top
        Vector((stock_bound_box_min.x, stock_bound_box_min.y, stock_bound_box_max.z)),
        Vector((stock_bound_box_max.x, stock_bound_box_min.y, stock_bound_box_max.z)),
        Vector((stock_bound_box_max.x, stock_bound_box_max.y, stock_bound_box_max.z)),
        Vector((stock_bound_box_min.x, stock_bound_box_max.y, stock_bound_box_max.z)),
    ]

    gpu.state.line_width_set(2)
    gpu.state.depth_test_set("LESS_EQUAL")
    gpu.state.depth_mask_set(True)
    SHADER.uniform_float("color", (1, 1, 1, 1))
    batch = batch_for_shader(SHADER, "LINES", {"pos": coords}, indices=STOCK_INDICES)
    batch.draw(SHADER)
    gpu.state.depth_mask_set(False)
    gpu.state.line_width_set(1)


def draw_valid_drill() -> None:
    context = bpy.context
    if len(context.scene.cam_jobs) == 0 or len(context.scene.cam_job.operations) == 0:
        return

    # Temporary select drill operation
    operation = context.scene.cam_job.operation
    strategy = operation.strategy

    gpu.state.line_width_set(2)
    SHADER.uniform_float("color", (1, 1, 1, 1))
    svf = strategy.get_source_valid_features(context, operation)
    for center, (bb_min, bb_max) in zip(svf["center"], svf["bound_box"]):
        scale = 0.1 * (bb_max - bb_min)
        coords = [v * scale + center for v in UNIT_CIRCLE_VECTORS]
        batch = batch_for_shader(SHADER, "LINE_LOOP", {"pos": coords})
        batch.draw(SHADER)
    gpu.state.line_width_set(1)
