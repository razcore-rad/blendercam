from bpy.props import (
    BoolProperty,
    EnumProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Context, Object, PropertyGroup
from mathutils import Vector

from . import feedmovementspindle, strategy, workarea
from .cutter import (
    BallCutter,
    BullCutter,
    BallConeCutter,
    BullConeCutter,
    ConeCutter,
    ConeConeCutter,
    CylinderCutter,
    CylinderConeCutter,
    SimpleCutter,
)
from .... import utils
from ....types import ComputeResult


def update_cutter(operation: PropertyGroup, context: Context) -> None:
    utils.copy(context, operation.previous_cutter, operation.cutter)
    operation.previous_cutter_type = operation.cutter_type


def update_strategy(operation: PropertyGroup, context: Context) -> None:
    utils.copy(context, operation.previous_strategy, operation.strategy)
    if operation.cutter_type == "":
        operation.cutter_type = "CYLINDER"
    operation.previous_strategy_type = operation.strategy_type


class Operation(PropertyGroup):
    EXCLUDE_PROPNAMES = {
        "previous_strategy_type",
        "previous_cutter_type",
    }
    NAME = "CAMOperation"

    is_hidden: BoolProperty(default=False)
    previous_cutter_type: StringProperty(default="CYLINDER")
    cutter_type: EnumProperty(
        name="Type",
        items=[
            ("CYLINDER", "Cylinder", ""),
            ("BALL", "Ball", ""),
            ("BULL", "Bull", ""),
            ("CONE", "Cone", ""),
            ("CYLINDER_CONE", "Cylinder Cone", ""),
            ("BALL_CONE", "Ball Cone", ""),
            ("BULL_CONE", "Bull Cone", ""),
            ("CONE_CONE", "Cone Cone", ""),
        ],
        default=5,
        update=update_cutter,
    )
    cylinder_cutter: PointerProperty(type=CylinderCutter)
    ball_cutter: PointerProperty(type=BallCutter)
    bull_cutter: PointerProperty(type=BullCutter)
    cone_cutter: PointerProperty(type=ConeCutter)
    cylinder_cone_cutter: PointerProperty(type=CylinderConeCutter)
    ball_cone_cutter: PointerProperty(type=BallConeCutter)
    bull_cone_cutter: PointerProperty(type=BullConeCutter)
    cone_cone_cutter: PointerProperty(type=ConeConeCutter)
    laser_cutter: PointerProperty(type=SimpleCutter)
    plasma_cutter: PointerProperty(type=SimpleCutter)

    previous_strategy_type: StringProperty(default="PROFILE")
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
                "Medial axis, must be used with V or ball cutter, for engraving"
                " various width shapes with a single stroke"
            ),
        ),
        (
            "OUTLINE_FILL",
            "Outline Fill",
            (
                "Detect outline and fill it with paths as pocket then sample"
                " these paths on the 3D surface"
            ),
        ),
        ("PARALLEL", "Parallel", "Parallel lines at any angle"),
        ("POCKET", "Pocket", "Pocket"),
        ("PROFILE", "Profile", "Profile cutout"),
        ("SPIRAL", "Spiral", "Spiral path"),
        (
            "WATERLINE_ROUGHING",
            "Waterline Roughing",
            "Roughing below ZERO. Z is always below ZERO",
        ),
    ]
    strategy_type: EnumProperty(
        name="Strategy",
        items=strategy_type_items,
        default="PROFILE",
        update=update_strategy,
    )
    block_strategy: PointerProperty(type=strategy.Block)
    circles_strategy: PointerProperty(type=strategy.Circles)
    cross_strategy: PointerProperty(type=strategy.Cross)
    carve_project_strategy: PointerProperty(type=strategy.CarveProject)
    curve_to_path_strategy: PointerProperty(type=strategy.CurveToPath)
    drill_strategy: PointerProperty(type=strategy.Drill)
    medial_axis_strategy: PointerProperty(type=strategy.MedialAxis)
    outline_fill_strategy: PointerProperty(type=strategy.OutlineFill)
    parallel_strategy: PointerProperty(type=strategy.Parallel)
    pocket_strategy: PointerProperty(type=strategy.Pocket)
    profile_strategy: PointerProperty(type=strategy.Profile)
    spiral_strategy: PointerProperty(type=strategy.Spiral)
    waterline_roughing_strategy: PointerProperty(type=strategy.WaterlineRoughing)

    feed: PointerProperty(type=feedmovementspindle.Feed)
    movement: PointerProperty(type=feedmovementspindle.Movement)
    spindle: PointerProperty(type=feedmovementspindle.Spindle)
    work_area: PointerProperty(type=workarea.WorkArea)

    @property
    def previous_cutter(self) -> PropertyGroup:
        return getattr(self, f"{self.previous_cutter_type.lower()}_cutter")

    @property
    def cutter_propname(self) -> str:
        return f"{self.cutter_type.lower()}_cutter"

    @property
    def cutter(self) -> PropertyGroup:
        return getattr(self, self.cutter_propname)

    @property
    def strategy_propname(self) -> str:
        return f"{self.strategy_type.lower()}_strategy"

    @property
    def previous_strategy(self) -> PropertyGroup:
        return getattr(self, f"{self.previous_strategy_type.lower()}_strategy")

    @property
    def strategy(self) -> PropertyGroup:
        return getattr(self, self.strategy_propname)

    def get_bound_box(self, context: Context) -> (Vector, Vector):
        def get_vectors(source: list[Object]) -> [Vector]:
            result = []
            for obj in source:
                if obj.name not in context.view_layer.objects:
                    continue

                for v in obj.to_mesh().vertices:
                    result.append(obj.matrix_world @ v.co)
                obj.to_mesh_clear()
            return result

        result = (Vector(), Vector())
        source = self.strategy.get_evaluated_source(context)
        if source:
            result = utils.get_bound_box(get_vectors(source))
        return result

    def get_depth_end(self, context: Context) -> float:
        result = 0
        if self.work_area.depth_end_type == "CUSTOM":
            result = self.work_area.depth_end
        if self.work_area.depth_end_type == "SOURCE":
            bound_box_min, _ = self.get_bound_box(context)
            result = bound_box_min.z
        elif self.work_area.depth_end_type == "STOCK":
            stock_bound_box_min, _ = context.scene.cam_job.get_stock_bound_box(context)
            result = stock_bound_box_min.z
        return result

    def execute_compute(self, context: Context) -> ComputeResult:
        return self.strategy.execute_compute(context, self)

    def add_data(self, context: Context) -> None:
        self.name = self.NAME
