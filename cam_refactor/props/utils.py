from itertools import chain, count, islice, repeat, tee
from math import ceil, copysign, isclose, sqrt
from typing import Any, Iterator

import bpy
import numpy as np
from mathutils import Vector


PRECISION = 5

REDUCE_MAP = {True: {"FINISHED"}, False: {"CANCELLED"}}


def get_propnames(pg: bpy.types.PropertyGroup, use_exclude_propnames=True) -> list[str]:
    exclude_propnames = ["rna_type"]
    if use_exclude_propnames:
        exclude_propnames += getattr(pg, "EXCLUDE_PROPNAMES", set())
    return sorted(
        {
            propname
            for propname in pg.rna_type.properties.keys()
            if propname not in exclude_propnames
        }
    )


def copy(
    context: bpy.types.Context,
    from_prop: bpy.types.Property,
    to_prop: bpy.types.Property,
    depth=0,
) -> None:
    def noop(*args, **kwargs) -> None:
        pass

    if isinstance(from_prop, bpy.types.PropertyGroup):
        for propname in get_propnames(to_prop, use_exclude_propnames=False):
            if not hasattr(from_prop, propname):
                continue

            from_subprop = getattr(from_prop, propname)
            if any(
                isinstance(from_subprop, t)
                for t in [bpy.types.PropertyGroup, bpy.types.bpy_prop_collection]
            ):
                copy(context, from_subprop, getattr(to_prop, propname), depth + 1)
            elif hasattr(to_prop, propname):
                if propname == "data" and any(
                    isinstance(from_subprop, t)
                    for t in [bpy.types.Collection, bpy.types.Object]
                ):
                    from_subprop = from_subprop.copy()
                    link = noop
                    if isinstance(from_subprop, bpy.types.Collection):
                        link = context.collection.children.link
                        context.scene.cam_job_active_index += 1
                        for obj in from_subprop.objects:
                            from_subprop.objects.unlink(obj)
                    elif isinstance(from_subprop, bpy.types.Object):
                        from_subprop.data = from_subprop.data.copy()
                        link = context.scene.cam_job.data.objects.link
                    link(from_subprop)

                try:
                    setattr(to_prop, propname, from_subprop)
                except TypeError:
                    pass

    elif isinstance(from_prop, bpy.types.bpy_prop_collection):
        to_prop.clear()
        for from_subprop in from_prop.values():
            copy(context, from_subprop, to_prop.add(), depth + 1)


def poll_object_source(strategy: bpy.types.Property, obj: bpy.types.Object) -> bool:
    context = bpy.context
    curve = getattr(strategy, "curve", None)
    obj_is_cam_object = obj in [
        op.data for cj in context.scene.cam_jobs for op in cj.operations
    ]
    operation = context.scene.cam_job.operation
    return (
        obj.type == "CURVE"
        if operation.strategy_type == "DRILL"
        else obj.type in ["CURVE", "MESH"]
        and obj.name in context.view_layer.objects
        and obj is not curve
        and not obj_is_cam_object
    )


def poll_curve_object_source(
    strategy: bpy.types.Property, obj: bpy.types.Object
) -> bool:
    context = bpy.context
    return (
        obj.type == "CURVE"
        and obj.name in context.view_layer.objects
        and obj not in strategy.source
    )


def poll_curve_limit(_work_area: bpy.types.Property, obj: bpy.types.Object) -> bool:
    result = False
    scene = bpy.context.scene
    try:
        cam_job = scene.cam_jobs[scene.cam_job_active_index]
        operation = cam_job.operations[cam_job.operation_active_index]
        strategy = operation.strategy
        curve = getattr(strategy, "curve", None)
        result = poll_curve_object_source(strategy, obj) and obj is not curve
    except IndexError:
        pass
    return result


def get_bound_box(vectors: Iterator[Vector]) -> (Vector, Vector):
    result = (Vector(), Vector())
    if len(vectors) > 0:
        result = tuple(
            Vector(f(cs) for cs in zip(*ps)) for f, ps in zip((min, max), tee(vectors))
        )
    return result


def sign(x: float) -> float:
    if isclose(x, 0):
        x = 0
    return copysign(1, x)


def seq(start: float, end: float, step=1) -> Iterator[float]:
    result = iter(())
    if sign(end - start) == sign(step) and not isclose(step, 0):
        result = islice(count(start, step), ceil(abs((end - start) / step)))
    return result


def intersperse(seq: Iterator[Any], delim: Any) -> Iterator[Any]:
    return islice(chain(*zip(repeat(delim), seq)), 1, None)


def reduce_cancelled_or_finished(results: {str}) -> {str}:
    return REDUCE_MAP[any(r == "FINISHED" for r in results)]


def iter_next(seq) -> Any:
    return next(iter(seq))


def transpose(it: Iterator) -> Iterator:
    return zip(*it, strict=True)


def get_fit_circle_2d(
    vectors: Iterator[Vector], tolerance=1e-5
) -> tuple[Vector, float]:
    result = Vector(), 0.0
    xy = transpose(v.xy for v in vectors)
    x = np.array(iter_next(xy))
    y = np.array(iter_next(xy))
    c, residu, *_ = np.linalg.lstsq(
        np.array([x, y, np.ones(len(x))]).T, x**2 + y**2, rcond=None
    )
    if residu < tolerance:
        xc = c[0] / 2
        yc = c[1] / 2
        d = 2 * sqrt(c[2] + xc**2 + yc**2)
        result = Vector((xc, yc)), d
    return result
