import bpy

PRECISION = 5


def poll_object_source(strategy: bpy.types.Property, obj: bpy.types.Object) -> bool:
    curve = getattr(strategy, "curve", None)
    return obj.users != 0 and obj.type in ["CURVE", "MESH"] and obj is not curve


def poll_curve_object_source(strategy: bpy.types.Property, obj: bpy.types.Object) -> bool:
    return obj.users != 0 and obj.type == "CURVE" and obj is not strategy.source


def poll_curve_limit(work_area: bpy.types.Property, obj: bpy.types.Object) -> bool:
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
        class WorkArea(bpy.types.PropertyGroup):
            exclude_propnames = {"name"}

            depth_start: bpy.props.FloatProperty(
                name="Depth Start", default=0, min=0, max=1, precision=PRECISION, unit="LENGTH"
            )
            depth_end_type: bpy.props.EnumProperty(
                name="Depth End Type",
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
            ambient: bpy.props.EnumProperty(
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
                min=-360,
                max=360,
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
            method: bpy.props.EnumProperty(
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

    class PostProcessor(bpy.types.PropertyGroup):
        exclude_propnames = {"name"}

        movement_type: bpy.props.EnumProperty(
            name="Movement Type",
            items=[
                ("CLIMB", "Climb", ""),
                ("CONVENTIONAL", "Conventional", ""),
                ("MEANDER", "Meander", ""),
            ],
        )
        spinle_direction: bpy.props.EnumProperty(
            name="Spindle Direction",
            items=[
                ("CLOCKWISE", "Clockwise", ""),
                ("COUNTER_CLOCKWISE", "Couner Clocwie", ""),
            ],
        )
        free_movement_height: bpy.props.FloatProperty(
            name="Free Movement Height", min=1e-5, default=5e-3, precision=PRECISION, unit="LENGTH"
        )

    name: bpy.props.StringProperty(name="Name", default="Job")
    is_hidden: bpy.props.BoolProperty(default=False)
    count: bpy.props.IntVectorProperty(name="Count", default=(1, 1), min=1, subtype="XYZ", size=2)
    gap: bpy.props.FloatVectorProperty(name="Gap", default=(0, 0), min=0, subtype="XYZ_LENGTH", size=2)
    operations: bpy.props.CollectionProperty(type=Operation)
    operation_active_index: bpy.props.IntProperty(default=0, min=0)
    stock: bpy.props.PointerProperty(type=Stock)
    post_processor: bpy.props.PointerProperty(type=PostProcessor)
