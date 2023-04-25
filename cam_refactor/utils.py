from collections.abc import Sequence
from itertools import chain, count, islice, repeat
from math import ceil, copysign, isclose, sqrt
from typing import Any, Iterator

import bpy
import numpy as np
from bpy.types import (
    bpy_prop_collection,
    Collection,
    Context,
    Object,
    Property,
    PropertyGroup,
)
from mathutils import Vector


PRECISION = 5
EPSILON = 1 / 10**PRECISION
LENGTH_UNIT_SCALE = 1e3
ZERO_VECTOR = Vector()
REDUCE_MAP = {True: {"FINISHED"}, False: {"CANCELLED"}}


def noop(*args, **kwargs) -> None:
    pass


def get_propnames(pg: PropertyGroup, use_exclude_propnames=True) -> list[str]:
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


def get_scaled_prop(propname: str, default, self):
    scale_length = bpy.context.scene.unit_settings.scale_length
    default = (
        [d / scale_length for d in default]
        if isinstance(default, Sequence)
        else default / scale_length
    )
    return self.get(propname, default)


def set_scaled_prop(propname: str, value_min, value_max, self, value):
    scale_length = bpy.context.scene.unit_settings.scale_length
    if value_min is not None:
        value = (
            [max(value_min / scale_length, v) for v in value]
            if isinstance(value, Sequence)
            else max(value_min / scale_length, value)
        )
    if value_max is not None:
        value = (
            [min(value_max / scale_length, v) for v in value]
            if isinstance(value, Sequence)
            else min(value_max / scale_length, value)
        )
    self[propname] = value


def copy(context: Context, from_prop: Property, to_prop: Property, depth=0) -> None:
    if isinstance(from_prop, PropertyGroup):
        for propname in get_propnames(to_prop, use_exclude_propnames=False):
            if not hasattr(from_prop, propname) or propname in ["data", "object"]:
                continue

            from_subprop = getattr(from_prop, propname)
            if any(
                isinstance(from_subprop, t)
                for t in [PropertyGroup, bpy_prop_collection]
            ):
                copy(context, from_subprop, getattr(to_prop, propname), depth + 1)
            elif hasattr(to_prop, propname):
                try:
                    setattr(to_prop, propname, from_subprop)
                except TypeError:
                    pass

    elif isinstance(from_prop, bpy_prop_collection):
        to_prop.clear()
        for from_subprop in from_prop.values():
            copy(context, from_subprop, to_prop.add(), depth + 1)


def poll_object_source(strategy: PropertyGroup, obj: Object) -> bool:
    context = bpy.context
    curve = getattr(strategy, "curve", None)
    obj_is_cam_object = obj in [cj.object for cj in context.scene.cam_jobs]
    return (
        obj.type in ["CURVE", "MESH"]
        and obj.name in context.view_layer.objects
        and obj is not curve
        and not obj_is_cam_object
    )


def poll_collection_source(strategy: PropertyGroup, col: Collection) -> bool:
    return not any(col is cj.data for cj in bpy.context.scene.cam_jobs)


def poll_curve_object_source(strategy: PropertyGroup, obj: Object) -> bool:
    context = bpy.context
    return (
        obj.type == "CURVE"
        and obj.name in context.view_layer.objects
        and obj not in strategy.get_source(context)
    )


def clamp(x: float, bottom: float, top: float) -> float:
    return max(bottom, min(x, top))


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
    xy = transpose(vectors)
    x = np.array(iter_next(xy))
    y = np.array(iter_next(xy))
    c, *_ = np.linalg.lstsq(
        np.array([x, y, np.ones(len(x))]).T, x**2 + y**2, rcond=None
    )
    xc = c[0] / 2
    yc = c[1] / 2
    std_deviation = np.sqrt((x - xc) ** 2 + (y - yc) ** 2).std()
    if std_deviation < tolerance:
        result = Vector((xc, yc)), 2 * sqrt(c[2] + xc**2 + yc**2)
    return result
