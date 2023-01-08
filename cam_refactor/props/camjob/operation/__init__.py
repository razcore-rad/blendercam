import importlib

import bpy

mods = {".cutter", ".feedmovementspindle", ".strategy", ".workarea", "...utils"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})


def get_cutter_types(operation: bpy.types.PropertyGroup, _context: bpy.types.Context) -> list[tuple[str, str, str]]:
    result = []
    try:
        result.extend(
            [
                ("BALL", "Ball", "Ball nose end mill"),
                ("BALL_CONE", "Ball Cone", "Ball cone nose end mill"),
                ("BULL", "Bull", "Bull nose end mill"),
                ("BULL_CONE", "Bull Cone", "Bull cone nose end mill"),
                ("CONE", "Cone", "Cone end mill"),
                ("CYLINDER", "Cylinder", "Cylinder end mill"),
                ("CYLINDER_CONE", "Cylinder Cone", "Cylinder cone end mill"),
            ]
        )

        if operation.strategy_type in {"MEDIAL_AXIS", "PROFILE"}:
            result.extend(
                [
                    None,
                    ("V_CARVE", "V-Carve", "V-Carve end mill"),
                    None,
                    ("LASER", "Laser", "Laser cutter"),
                    ("PLASMA", "Plasma", "Plasma cutter"),
                ]
            )
        elif operation.strategy_type in {"DRILL"}:
            result.extend([None, ("DRILL", "Drill", "Drill mill")])
    except IndexError:
        pass
    return result


def update_cutter(operation: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    utils.copy(context, operation.previous_cutter, operation.cutter)
    operation.previous_cutter_type = operation.cutter_type


def update_strategy(operation: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    utils.copy(context, operation.previous_strategy, operation.strategy)
    if operation.cutter_type == "":
        operation.cutter_type = "CYLINDER"
    operation.previous_strategy_type = operation.strategy_type


class Operation(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"previous_strategy_type"}
    NAME = "CAMOperation"

    data: bpy.props.PointerProperty(type=bpy.types.Object)
    use_modifiers: bpy.props.BoolProperty(default=True)

    previous_cutter_type: bpy.props.StringProperty(default="CYLINDER")
    cutter_type: bpy.props.EnumProperty(name="Type", items=get_cutter_types, default=5, update=update_cutter)
    ball_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    ball_cone_cutter: bpy.props.PointerProperty(type=cutter.ConeMill)
    bull_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    bull_cone_cutter: bpy.props.PointerProperty(type=cutter.ConeMill)
    cone_cutter: bpy.props.PointerProperty(type=cutter.ConeMill)
    cylinder_cutter: bpy.props.PointerProperty(type=cutter.Mill)
    cylinder_cone_cutter: bpy.props.PointerProperty(type=cutter.ConeMill)
    drill_cutter: bpy.props.PointerProperty(type=cutter.Drill)
    v_carve_cutter: bpy.props.PointerProperty(type=cutter.ConeMill)
    laser_cutter: bpy.props.PointerProperty(type=cutter.Simple)
    plasma_cutter: bpy.props.PointerProperty(type=cutter.Simple)

    previous_strategy_type: bpy.props.StringProperty(default="PROFILE")
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
    strategy_type: bpy.props.EnumProperty(
        name="Strategy", items=strategy_type_items, default="PROFILE", update=update_strategy
    )
    block_strategy: bpy.props.PointerProperty(type=strategy.Block)
    circles_strategy: bpy.props.PointerProperty(type=strategy.Circles)
    cross_strategy: bpy.props.PointerProperty(type=strategy.Cross)
    curve_to_path_strategy: bpy.props.PointerProperty(type=strategy.CurveToPath)
    drill_strategy: bpy.props.PointerProperty(type=strategy.Drill)
    medial_axis_strategy: bpy.props.PointerProperty(type=strategy.MedialAxis)
    outline_fill_strategy: bpy.props.PointerProperty(type=strategy.OutlineFill)
    parallel_strategy: bpy.props.PointerProperty(type=strategy.Parallel)
    pocket_strategy: bpy.props.PointerProperty(type=strategy.Pocket)
    profile_strategy: bpy.props.PointerProperty(type=strategy.Profile)
    spiral_strategy: bpy.props.PointerProperty(type=strategy.Spiral)
    waterline_roughing_strategy: bpy.props.PointerProperty(type=strategy.WaterlineRoughing)

    feed: bpy.props.PointerProperty(type=feedmovementspindle.Feed)
    movement: bpy.props.PointerProperty(type=feedmovementspindle.Movement)
    spindle: bpy.props.PointerProperty(type=feedmovementspindle.Spindle)
    work_area: bpy.props.PointerProperty(type=workarea.WorkArea)

    @property
    def previous_cutter(self) -> bpy.types.PropertyGroup:
        return getattr(self, f"{self.previous_cutter_type.lower()}_cutter")

    @property
    def cutter_propname(self) -> str:
        return f"{self.cutter_type.lower()}_cutter"

    @property
    def cutter(self) -> str:
        return getattr(self, self.cutter_propname)

    @property
    def strategy_propname(self) -> str:
        return f"{self.strategy_type.lower()}_strategy"

    @property
    def previous_strategy(self) -> bpy.types.PropertyGroup:
        return getattr(self, f"{self.previous_strategy_type.lower()}_strategy")

    @property
    def strategy(self) -> bpy.types.PropertyGroup:
        return getattr(self, self.strategy_propname)

    def add_data(self, context: bpy.types.Context) -> None:
        self.data = bpy.data.objects.new(self.NAME, bpy.data.meshes.new(self.NAME))
        context.scene.cam_job.data.objects.link(self.data)

    def remove_data(self) -> None:
        bpy.data.meshes.remove(self.data.data)
