import importlib

import bpy

modnames = ["cutter", "feedmovementspindle", "strategy", "workarea"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f".{modname}", __package__)) for modname in modnames}
)


class Operation(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="Operation")
    is_hidden: bpy.props.BoolProperty(default=False)
    use_modifiers: bpy.props.BoolProperty(default=True)

    cutter_type: bpy.props.EnumProperty(
        items=[
            ("END", "End", "End Mill"),
            ("BALL_CONE", "Ball Cone", "Ball Cone Mill for Parallel"),
            ("BALL_NOSE", "Ball Nose", "Ball Nose Mill"),
            ("BULL_NOSE", "Bull Nose", "Bull Nose Mill"),
            ("CYLINDER_CONE", "Cylinder Cone", "Cylinder Cone Mill for Parallel"),
            ("LASER", "Laser", "Laser Cutter"),
            ("PLASMA", "Plasma", "Plasma Cutter"),
            ("V_CARVE", "V-Carve", "V-Carve Mill"),
        ],
        name="Type",
    )
    end_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    ball_cone_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    ball_nose_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    bull_nose_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    cylinder_cone_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    laser_cutter: bpy.props.PointerProperty(type=cutter.Simple)
    plasma_cutter: bpy.props.PointerProperty(type=cutter.Simple)
    v_carve_cutter: bpy.props.PointerProperty(type=cutter.Mill)

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
    strategy_type: bpy.props.EnumProperty(items=strategy_type_items, name="Strategy")

    block_strategy: bpy.props.PointerProperty(type=strategy.BlockStrategy)
    carve_project_strategy: bpy.props.PointerProperty(type=strategy.CarveProjectStrategy)
    circles_strategy: bpy.props.PointerProperty(type=strategy.CirclesStrategy)
    cross_strategy: bpy.props.PointerProperty(type=strategy.CrossStrategy)
    curve_to_path_strategy: bpy.props.PointerProperty(type=strategy.CurveToPathStrategy)
    drill_strategy: bpy.props.PointerProperty(type=strategy.DrillStrategy)
    medial_axis_strategy: bpy.props.PointerProperty(type=strategy.MedialAxisStrategy)
    outline_fill_strategy: bpy.props.PointerProperty(type=strategy.OutlineFillStrategy)
    parallel_strategy: bpy.props.PointerProperty(type=strategy.ParallelStrategy)
    pocket_strategy: bpy.props.PointerProperty(type=strategy.PocketStrategy)
    profile_strategy: bpy.props.PointerProperty(type=strategy.ProfileStrategy)
    spiral_strategy: bpy.props.PointerProperty(type=strategy.SpiralStrategy)
    waterline_roughing_strategy: bpy.props.PointerProperty(type=strategy.WaterlineRoughingStrategy)

    feed: bpy.props.PointerProperty(type=feedmovementspindle.Feed)
    movement: bpy.props.PointerProperty(type=feedmovementspindle.Movement)
    spindle: bpy.props.PointerProperty(type=feedmovementspindle.Spindle)
    work_area: bpy.props.PointerProperty(type=workarea.WorkArea)

    @property
    def cutter_propname(self) -> str:
        return f"{self.cutter_type.lower()}_cutter"

    @property
    def cutter(self) -> bpy.types.PropertyGroup:
        return getattr(self, self.cutter_propname, None)

    @property
    def strategy_propname(self) -> str:
        return f"{self.strategy_type.lower()}_strategy"

    @property
    def strategy(self) -> bpy.types.PropertyGroup:
        return getattr(self, self.strategy_propname, None)

    @property
    def is_strategy_valid(self) -> bool:
        return self.strategy is not None
