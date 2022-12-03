import math

import bpy

PRECISION = 5


def copy(from_prop: bpy.types.Property, to_prop: bpy.types.Property, depth=0) -> None:
    if type(from_prop) != type(to_prop):
        return

    if isinstance(from_prop, bpy.types.PropertyGroup):
        for propname in props.get_propnames(to_prop, use_exclude_propnames=False):
            from_subprop = getattr(from_prop, propname)
            if isinstance(from_subprop, bpy.types.PropertyGroup) or isinstance(
                from_subprop, bpy.types.bpy_prop_collection
            ):
                copy(from_subprop, getattr(to_prop, propname), depth + 1)
            else:
                setattr(to_prop, propname, from_subprop)
                if propname == "name" and depth == 0:
                    to_prop.name += "_copy"

    elif isinstance(from_prop, bpy.types.bpy_prop_collection):
        to_prop.clear()
        for from_subprop in from_prop.values():
            copy(from_subprop, to_prop.add(), depth + 1)


def get_propnames(pg: bpy.types.PropertyGroup, use_exclude_propnames=True):
    exclude_propnames = ["rna_type"]
    if use_exclude_propnames:
        exclude_propnames += getattr(pg, "exclude_propnames", [])
    return sorted({propname for propname in pg.rna_type.properties.keys() if propname not in exclude_propnames})


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


class CAMJob(bpy.types.PropertyGroup):
    class Operation(bpy.types.PropertyGroup):
        class Movement(bpy.types.PropertyGroup):
            exclude_propnames = {"name"}

            free_height: bpy.props.FloatProperty(
                name="Free Movement Height", min=1e-5, default=5e-3, precision=PRECISION, unit="LENGTH"
            )
            type: bpy.props.EnumProperty(
                name="Movement Type",
                items=[
                    ("CLIMB", "Climb", "Cutter rotates with the direction of the feed"),
                    ("CONVENTIONAL", "Conventional", "Cutter rotates against the direction of the feed"),
                    ("MEANDER", "Meander", "Cutting is done both with and against the rotation of the spindle"),
                ],
            )

            spindle_direction_type: bpy.props.EnumProperty(
                name="Spindle Direction",
                items=[
                    ("CLOCKWISE", "Clockwise", "", "LOOP_FORWARDS", 0),
                    ("COUNTER_CLOCKWISE", "Counter-Clockwise", "", "LOOP_BACK", 1),
                ],
            )

            vertical_angle: bpy.props.FloatProperty(
                name="Vertical Angle",
                description="Convert path above this angle to a vertical path for cutter protection",
                default=math.radians(4),
                min=0,
                max=math.pi / 2,
                precision=0,
                subtype="ANGLE",
                unit="ROTATION",
            )

        class WorkArea(bpy.types.PropertyGroup):
            ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}

            exclude_propnames = {"name", "depth_start", "depth_end_type", "depth_end"}

            depth_start: bpy.props.FloatProperty(
                name="Depth Start", default=0, min=0, max=1, precision=PRECISION, unit="LENGTH"
            )
            depth_end_type: bpy.props.EnumProperty(
                name="Depth End",
                items=[
                    ("CUSTOM", "Custom", ""),
                    ("OBJECT", "Object", ""),
                    ("STOCK", "Stock", ""),
                ],
            )
            depth_end: bpy.props.FloatProperty(
                name="Depth End", default=1e-1, min=1e-5, max=1, precision=PRECISION, unit="LENGTH"
            )
            layer_size: bpy.props.FloatProperty(
                name="Layer Size", default=0, min=1e-4, max=1e-1, precision=PRECISION, unit="LENGTH"
            )
            ambient_type: bpy.props.EnumProperty(
                name="Ambient", items=[("OFF", "Off", ""), ("ALL", "All", ""), ("AROUND", "Around", "")]
            )
            curve_limit: bpy.props.PointerProperty(name="Curve Limit", type=bpy.types.Object, poll=poll_curve_limit)

        class DistanceAlongPathsMixin(bpy.types.PropertyGroup):
            distance_along_paths: bpy.props.FloatProperty(
                name="Distance Along Paths",
                default=2e-4,
                min=1e-5,
                max=32,
                precision=PRECISION,
                unit="LENGTH",
            )

        class DistanceBetweenPathsMixin(bpy.types.PropertyGroup):
            distance_between_paths: bpy.props.FloatProperty(
                name="Distance Between Paths",
                default=1e-3,
                min=1e-5,
                max=32,
                precision=PRECISION,
                unit="LENGTH",
            )

        class PathsAngleMixin(bpy.types.PropertyGroup):
            paths_angle: bpy.props.FloatProperty(
                name="Paths Angle",
                default=0,
                min=-math.tau,
                max=math.tau,
                precision=0,
                subtype="ANGLE",
                unit="ROTATION",
            )

        class SourceMixin(bpy.types.PropertyGroup):
            exclude_propnames = [
                "name",
                "source_type",
                "object_source",
                "collection_source",
            ]

            source_type_items = [
                ("OBJECT", "Object", "Object data source.", "OBJECT_DATA", 0),
                ("COLLECTION", "Collection", "Collection data source", "OUTLINER_COLLECTION", 1),
            ]
            source_type: bpy.props.EnumProperty(items=source_type_items, name="Source Type")
            object_source: bpy.props.PointerProperty(type=bpy.types.Object, name="Source", poll=poll_object_source)
            collection_source: bpy.props.PointerProperty(type=bpy.types.Collection, name="Source")

            @property
            def source(self) -> bpy.types.PropertyGroup:
                return getattr(self, f"{self.source_type.lower()}_source", None)

            @property
            def is_source_valid(self) -> bool:
                return self.source is not None

        class BlockStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin):
            pass

        class CarveProjectStrategy(DistanceAlongPathsMixin, SourceMixin):
            ICON_MAP = {"curve": "OUTLINER_OB_CURVE"}

            curve: bpy.props.PointerProperty(name="Curve", type=bpy.types.Object, poll=poll_curve_object_source)
            depth: bpy.props.FloatProperty(name="Depth", default=1e-3, unit="LENGTH", precision=PRECISION)

            @property
            def is_source_valid(self) -> bool:
                return super().is_source_valid and self.curve is not None

        class CirclesStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin):
            pass

        class CrossStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, PathsAngleMixin, SourceMixin):
            pass

        class CurveToPathStrategy(SourceMixin):
            exclude_propnames = [
                "name",
                "source_type",
                "curve_object_source",
                "object_source",
                "collection_source",
            ]

            source_type_items = [
                ("CURVE_OBJECT", "Object (Curve)", "Curve object data source", "OUTLINER_OB_CURVE", 0),
                ("COLLECTION", "Collection", "Collection data source", "OUTLINER_COLLECTION", 1),
            ]
            source_type: bpy.props.EnumProperty(items=source_type_items, name="Source Type")
            curve_object_source: bpy.props.PointerProperty(
                type=bpy.types.Object, name="Source", poll=poll_curve_object_source
            )

        class DrillStrategy(SourceMixin):
            method_type: bpy.props.EnumProperty(
                name="Method",
                items=[
                    ("POINTS", "Points", "Drill at every point", "SNAP_VERTEX", 0),
                    (
                        "CENTER",
                        "Center",
                        "Position is at the center of disjoint mesh or curve islands",
                        "SNAP_FACE_CENTER",
                        1,
                    ),
                ],
            )

        class MedialAxisStrategy(SourceMixin):
            threshold: bpy.props.FloatProperty(name="Threshold", default=1e-3, unit="LENGTH", precision=PRECISION)
            subdivision: bpy.props.FloatProperty(name="Subdivision", default=2e-4, unit="LENGTH", precision=PRECISION)
            do_clean_finish: bpy.props.BoolProperty(name="Clean Finish", default=True)
            do_generate_mesh: bpy.props.BoolProperty(name="Generate Mesh", default=True)

        class OutlineFillStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin):
            pass

        class PocketStrategy(DistanceBetweenPathsMixin, SourceMixin):
            pass

        class ProfileStrategy(SourceMixin):
            cut_type: bpy.props.EnumProperty(
                name="Cut",
                items=[
                    ("ON_LINE", "On Line", "On line"),
                    ("INSIDE", "Inside", "Inside"),
                    ("OUTSIDE", "Outside", "Outside"),
                ],
            )
            do_merge: bpy.props.BoolProperty(name="Merge Outlines", default=True)
            outlines_count: bpy.props.IntProperty(name="Outlines Count", default=0)
            offset: bpy.props.IntProperty(name="Offset", default=0)
            style: bpy.props.EnumProperty(
                name="Style",
                items=[
                    ("CONVENTIONAL", "Conventional", "Conventional rounded"),
                    ("OVERSHOOT", "Overshoot", "Overshoot style"),
                ],
            )

        class ParallelStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, PathsAngleMixin, SourceMixin):
            pass

        class SpiralStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin):
            pass

        class WaterlineRoughingStrategy(DistanceBetweenPathsMixin, SourceMixin):
            distance_between_slices: bpy.props.FloatProperty(
                name="Distance Between Slices",
                default=1e-3,
                min=1e-5,
                max=32,
                precision=PRECISION,
                unit="LENGTH",
            )
            fill_between_slices: bpy.props.BoolProperty(name="Fill Between Slices", default=True)

        name: bpy.props.StringProperty(default="Operation")
        is_hidden: bpy.props.BoolProperty(default=False)
        use_modifiers: bpy.props.BoolProperty(default=True)

        strategy_type_items = [
            ("BLOCK", "Block", "Block path"),
            (
                "CARVE_PROJECT",
                "Carve Project",
                "Project a curve object on a 3D surface",
            ),
            ("CIRCLES", "Circles", "Circles path"),
            ("CROSS", "Cross", "Cross paths"),
            ("CURVE_TO_PATH", "Curve to Path", "Convert a curve object to G-code path"),
            ("DRILL", "Drill", "Drill"),
            (
                "MEDIAL_AXIS",
                "Medial axis",
                (
                    "Medial axis, must be used with V or ball cutter, for engraving various width"
                    " shapes with a single stroke"
                ),
            ),
            (
                "OUTLINE_FILL",
                "Outline Fill",
                "Detect outline and fill it with paths as pocket then sample these paths on the 3D surface",
            ),
            ("POCKET", "Pocket", "Pocket"),
            ("PROFILE", "Profile", "Profile cutout"),
            ("PARALLEL", "Parallel", "Parallel lines at any angle"),
            ("SPIRAL", "Spiral", "Spiral path"),
            (
                "WATERLINE_ROUGHING",
                "Waterline Roughing",
                "Roughing below ZERO. Z is always below ZERO",
            ),
        ]
        strategy_type: bpy.props.EnumProperty(items=strategy_type_items, name="Strategy")

        block_strategy: bpy.props.PointerProperty(type=BlockStrategy)
        carve_project_strategy: bpy.props.PointerProperty(type=CarveProjectStrategy)
        circles_strategy: bpy.props.PointerProperty(type=CirclesStrategy)
        cross_strategy: bpy.props.PointerProperty(type=CrossStrategy)
        curve_to_path_strategy: bpy.props.PointerProperty(type=CurveToPathStrategy)
        drill_strategy: bpy.props.PointerProperty(type=DrillStrategy)
        medial_axis_strategy: bpy.props.PointerProperty(type=MedialAxisStrategy)
        outline_fill_strategy: bpy.props.PointerProperty(type=OutlineFillStrategy)
        pocket_strategy: bpy.props.PointerProperty(type=PocketStrategy)
        profile_strategy: bpy.props.PointerProperty(type=ProfileStrategy)
        parallel_strategy: bpy.props.PointerProperty(type=ParallelStrategy)
        spiral_strategy: bpy.props.PointerProperty(type=SpiralStrategy)
        waterline_roughing_strategy: bpy.props.PointerProperty(type=WaterlineRoughingStrategy)

        movement: bpy.props.PointerProperty(type=Movement)
        work_area: bpy.props.PointerProperty(type=WorkArea)

        @property
        def strategy(self) -> bpy.types.PropertyGroup:
            return getattr(self, f"{self.strategy_type.lower()}_strategy", None)

    class Stock(bpy.types.PropertyGroup):
        exclude_propnames = {"name"}

        type: bpy.props.EnumProperty(
            name="Type", items=[("ESTIMATE", "Estimate from Job", ""), ("CUSTOM", "Custom", "")]
        )
        estimate_offset: bpy.props.FloatVectorProperty(
            name="Estimate Offset", min=0, default=(1e-3, 1e-3, 1e-3), subtype="XYZ_LENGTH"
        )
        custom_location: bpy.props.FloatVectorProperty(name="Location", min=0, default=(0, 0, 0), subtype="XYZ_LENGTH")
        custom_size: bpy.props.FloatVectorProperty(
            name="Size", min=1e-3, default=(5e-1, 5e-1, 1e-1), subtype="XYZ_LENGTH"
        )

    class Machine(bpy.types.PropertyGroup):
        exclude_propnames = {"name", "post_processor"}

        class Feedrate(bpy.types.PropertyGroup):
            exclude_propnames = {"name"}

            default: bpy.props.FloatProperty(name="Default", default=1.5)
            min: bpy.props.FloatProperty(name="Min", default=1e-3)
            max: bpy.props.FloatProperty(name="Max", default=2)

        class Spindle(bpy.types.PropertyGroup):
            exclude_propnames = {"name"}

            default: bpy.props.FloatProperty(name="Default", default=5e3)
            min: bpy.props.FloatProperty(name="Min", default=2.5e3)
            max: bpy.props.FloatProperty(name="Max", default=2e4)

        work_area: bpy.props.FloatVectorProperty(
            name="Work Area", default=(8e-1, 5.6e-1, 9e-2), min=0, subtype="XYZ_LENGTH"
        )
        feedrate: bpy.props.PointerProperty(type=Feedrate)
        spindle: bpy.props.PointerProperty(type=Spindle)
        axes: bpy.props.IntProperty(name="Axes", default=3, min=3, max=5)
        collet_size: bpy.props.FloatProperty(name="Collet Size", default=0.0, min=0, max=1)
        post_processor: bpy.props.EnumProperty(
            name="Post Processor",
            default="GRBL",
            items=[
                ("ANILAM", "Anilam Crusader M", "Post processor for Anilam Crusader M"),
                ("CENTROID", "Centroid M40", "Post processor for Centroid M40"),
                ("EMC", "LinuxCNC", "Post processor for Linux based CNC control software"),
                ("FADAL", "Fadal", "Post processor for Fadal VMC"),
                ("GRAVOS", "Gravos", "Post processor for Gravos"),
                ("GRBL", "grbl", "Post processor for grbl firmware on Arduino with CNC shield"),
                ("ISO", "Iso", "Standardized G-code ISO 6983 (RS-274)"),
                ("HAFCO_HM_50", "Hafco HM-50", "Post processor for Hafco HM-50"),
                ("HEIDENHAIN", "Heidenhain", "Post processor for Heidenhain"),
                ("HEIDENHAIN_530", "Heidenhain 530", "Post processor for Heidenhain 530"),
                ("HEIDENHAIN_TNC151", "Heidenhain TNC151", "Post processor for Heidenhain TNC151"),
                ("LYNX_OTTER_O", "Lynx Otter O", "Post processor for Lynx Otter O"),
                ("MACH3", "Mach3", "Post processor for Mach3"),
                ("SHOPBOT_MTC", "ShopBot MTC", "Post processor for ShopBot MTC"),
                ("SIEGKX1", "Sieg KX1", "Post processor for Sieg KX1"),
                ("WIN_PC", "WinPC-NC", "Post processor for CNC by Burkhard Lewetz"),
            ],
        )

    name: bpy.props.StringProperty(name="Name", default="Job")
    is_hidden: bpy.props.BoolProperty(default=False)
    count: bpy.props.IntVectorProperty(name="Count", default=(1, 1), min=1, subtype="XYZ", size=2)
    gap: bpy.props.FloatVectorProperty(name="Gap", default=(0, 0), min=0, subtype="XYZ_LENGTH", size=2)
    operations: bpy.props.CollectionProperty(type=Operation)
    operation_active_index: bpy.props.IntProperty(default=0, min=0)
    stock: bpy.props.PointerProperty(type=Stock)
    machine: bpy.props.PointerProperty(type=Machine)


CLASSES = [
    CAMJob.Operation.Movement,
    CAMJob.Operation.WorkArea,
    CAMJob.Operation.BlockStrategy,
    CAMJob.Operation.CarveProjectStrategy,
    CAMJob.Operation.CirclesStrategy,
    CAMJob.Operation.CrossStrategy,
    CAMJob.Operation.CurveToPathStrategy,
    CAMJob.Operation.DrillStrategy,
    CAMJob.Operation.MedialAxisStrategy,
    CAMJob.Operation.OutlineFillStrategy,
    CAMJob.Operation.PocketStrategy,
    CAMJob.Operation.ProfileStrategy,
    CAMJob.Operation.ParallelStrategy,
    CAMJob.Operation.SpiralStrategy,
    CAMJob.Operation.WaterlineRoughingStrategy,
    CAMJob.Operation,
    CAMJob.Stock,
    CAMJob.Machine.Feedrate,
    CAMJob.Machine.Spindle,
    CAMJob.Machine,
    CAMJob,
]


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cam_jobs = bpy.props.CollectionProperty(type=CAMJob)
    bpy.types.Scene.cam_job_active_index = bpy.props.IntProperty(default=0, min=0)


def unregister() -> None:
    del bpy.types.Scene.cam_jobs
    del bpy.types.Scene.cam_job_active_index
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
