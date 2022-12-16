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
    cutter_dict = {
        "BALL": cutter.Mill,
        "BALL_CONE": cutter.ConeMill,
        "BULL": cutter.Mill,
        "BULL_CONE": cutter.ConeMill,
        "CONE": cutter.ConeMill,
        "CYLINDER": cutter.Mill,
        "CYLINDER_CONE": cutter.ConeMill,
        "DRILL": cutter.Drill,
        "V_CARVE": cutter.ConeMill,
        "LASER": cutter.Simple,
        "PLASMA": cutter.Simple,
    }
    previous_cutter = operation.cutter
    Operation.cutter = bpy.props.PointerProperty(type=cutter_dict.get(operation.cutter_type, cutter.Mill))
    utils.copy(context, previous_cutter, operation.cutter)


def update_strategy(operation: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    previous_strategy = operation.strategy
    Operation.strategy = bpy.props.PointerProperty(
        type=getattr(
            strategy, "".join(f"{st[:1].upper()}{st[1:].lower()}" for st in operation.strategy_type.split("_"))
        )
    )
    utils.copy(context, previous_strategy, operation.strategy)
    if operation.cutter_type == "":
        operation.cutter_type = "CYLINDER"


class Operation(bpy.types.PropertyGroup):
    NAME = "CAMOperation"

    data: bpy.props.PointerProperty(type=bpy.types.Object)
    use_modifiers: bpy.props.BoolProperty(default=True)

    cutter_type: bpy.props.EnumProperty(name="Type", items=get_cutter_types, default=5, update=update_cutter)
    cutter: bpy.props.PointerProperty(type=cutter.Mill)

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
        name="Strategy", items=strategy_type_items, default=10, update=update_strategy
    )
    strategy: bpy.props.PointerProperty(type=strategy.Profile)

    feed: bpy.props.PointerProperty(type=feedmovementspindle.Feed)
    movement: bpy.props.PointerProperty(type=feedmovementspindle.Movement)
    spindle: bpy.props.PointerProperty(type=feedmovementspindle.Spindle)
    work_area: bpy.props.PointerProperty(type=workarea.WorkArea)

    def add_data(self, context: bpy.types.Context) -> None:
        self.data = bpy.data.objects.new(self.NAME, bpy.data.meshes.new(self.NAME))
        context.scene.cam_job.data.objects.link(self.data)
        workarea.update_depth_end_type(self.work_area, context)

    def remove_data(self) -> None:
        bpy.data.meshes.remove(self.data.data)
