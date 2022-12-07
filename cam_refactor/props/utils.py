import bpy


PRECISION = 5


def get_propnames(pg: bpy.types.PropertyGroup, use_exclude_propnames=True):
    exclude_propnames = ["rna_type"]
    if use_exclude_propnames:
        exclude_propnames += getattr(pg, "EXCLUDE_PROPNAMES", set())
    return sorted({propname for propname in pg.rna_type.properties.keys() if propname not in exclude_propnames})


def copy(from_prop: bpy.types.Property, to_prop: bpy.types.Property, depth=0) -> None:
    if isinstance(from_prop, bpy.types.PropertyGroup):
        for propname in get_propnames(to_prop, use_exclude_propnames=False):
            if not hasattr(from_prop, propname):
                continue

            from_subprop = getattr(from_prop, propname)
            if any(isinstance(from_subprop, p) for p in [bpy.types.PropertyGroup, bpy.types.bpy_prop_collection]):
                copy(from_subprop, getattr(to_prop, propname), depth + 1)
            elif hasattr(to_prop, propname):
                setattr(to_prop, propname, from_subprop)
                if propname == "name" and depth == 0:
                    to_prop.name += "_copy"

    elif isinstance(from_prop, bpy.types.bpy_prop_collection):
        to_prop.clear()
        for from_subprop in from_prop.values():
            copy(from_subprop, to_prop.add(), depth + 1)


def poll_object_source(strategy: bpy.types.Property, obj: bpy.types.Object) -> bool:
    curve = getattr(strategy, "curve", None)
    return obj.users != 0 and obj.type in ["CURVE", "MESH"] and obj is not curve


def poll_curve_object_source(strategy: bpy.types.Property, obj: bpy.types.Object) -> bool:
    return obj.users != 0 and obj.type == "CURVE" and obj is not strategy.source


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
