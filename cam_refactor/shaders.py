import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

shader = gpu.shader.from_builtin("3D_UNIFORM_COLOR")


def draw_stock() -> None:
    context = bpy.context
    if len(context.scene.cam_jobs) == 0:
        return

    stock_bound_box_min, stock_bound_box_max = context.scene.cam_job.stock_bound_box
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
    indices = [
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

    batch = batch_for_shader(shader, "LINES", {"pos": coords}, indices=indices)
    shader.uniform_float("color", (1, 1, 1, 1))
    batch.draw(shader)
