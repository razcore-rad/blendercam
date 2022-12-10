import importlib

import bl_operators
import bpy

modnames = ["props"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f".{modname}", __package__)) for modname in modnames}
)


class CAM_OT_AddPresetMachine(bl_operators.presets.AddPresetBase, bpy.types.Operator):
    """Add or remove a CAM Machine Preset"""

    bl_idname = "cam.preset_add_machine"
    bl_label = "Add Machine Preset"
    preset_menu = "CAM_PT_MachinePresets"
    preset_subdir = "cam/machines"

    preset_defines = [
        "machine = bpy.context.scene.cam_job.machine",
    ]

    preset_values = [
        "machine.post_processor",
        "machine.working_area",
        "machine.feedrate.default",
        "machine.feedrate.min",
        "machine.feedrate.max",
        "machine.spindle.default",
        "machine.spindle.min",
        "machine.spindle.max",
        "machine.axes",
    ]


class CAM_OT_AddPresetCutter(bl_operators.presets.AddPresetBase, bpy.types.Operator):
    """Add or remove a CAM Cutter Preset"""

    bl_idname = "cam.preset_add_cutter"
    bl_label = "Add Cutter Preset"
    preset_menu = "CAM_PT_CutterPresets"
    preset_subdir = "cam/cutters"

    preset_defines = [
        "operation = bpy.context.scene.cam_job.operation"
    ]

    @property
    def preset_values(self) -> list[str]:
        result = [
            "operation.cutter_type",
            "operation.cutter.id",
            "operation.cutter.description",
            "operation.cutter.diameter",
        ]

        operation = bpy.context.scene.cam_job.operation

        if isinstance(operation.cutter, props.camjob.operation.cutter.Mill):
            result.extend(
                [
                    "operation.cutter.flutes",
                    "operation.cutter.length",
                ]
            )
        elif isinstance(operation.cutter, props.camjob.operation.cutter.Drill):
            result.extend(["operation.cutter.length"])
        elif isinstance(operation.cutter, props.camjob.operation.cutter.ConeMill):
            result.extend(
                [
                    "operation.cutter.length",
                    "operation.cutter.angle",
                ]
            )
        return result


class CAM_OT_Action(bpy.types.Operator):
    bl_idname = "cam.action"
    bl_label = "CAM Action"
    bl_options = {"UNDO"}

    type_items = [
        ("ADD_JOB", "Add CAM job", "Add CAM job"),
        ("DUPLICATE_JOB", "Duplicate CAM job", "Duplicate CAM job"),
        ("REMOVE_JOB", "Remove CAM job", "Remove CAM job"),
        ("MOVE_JOB", "Move CAM job", "Move CAM job"),
        ("COMPUTE_JOB", "Compute CAM job", "Compute CAM job"),
        ("EXPORT_JOB", "Export CAM job", "Export CAM job"),
        ("ADD_OPERATION", "Add CAM operation", "Add CAM operation"),
        ("DUPLICATE_OPERATION", "Duplicate CAM operation", "Duplicate CAM operation"),
        ("REMOVE_OPERATION", "Remove CAM operation", "Remove CAM operation"),
        ("MOVE_OPERATION", "Move CAM operation", "Move CAM operation"),
    ]
    type: bpy.props.EnumProperty(items=type_items)
    move_direction: bpy.props.IntProperty()

    def __init__(self):
        super().__init__()
        self.execute_funcs = {
            id: getattr(self, f"execute_{id.split('_')[0].lower()}", self.execute_todo) for id, *_ in self.type_items
        }

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.scene is not None

    def execute_todo(self, context: bpy.types.Context, dataptr, propname: str, active_propname: str) -> set[str]:
        self.report({"INFO"}, f"{self.bl_idname}:{self.type}:NOT_IMPLTEMENTED_YET")
        return {"FINISHED"}

    def execute_add(self, context: bpy.types.Context, dataptr, propname: str, active_propname: str) -> set[str]:
        propscol = getattr(dataptr, propname)
        item = propscol.add()
        item.add_data()
        setattr(dataptr, active_propname, len(propscol) - 1)
        return {"FINISHED"}

    def execute_duplicate(self, context: bpy.types.Context, dataptr, propname: str, active_propname: str) -> set[str]:
        result = {"FINISHED"}
        propscol = getattr(dataptr, propname)
        if len(propscol) == 0:
            return result

        props.utils.copy(propscol[getattr(dataptr, active_propname)], propscol.add())
        return result

    def execute_remove(self, context: bpy.types.Context, dataptr, propname: str, active_propname: str) -> set[str]:
        try:
            propscol = getattr(dataptr, propname)
            item = propscol[getattr(dataptr, active_propname)]
            item.remove_data()
            propscol.remove(getattr(dataptr, active_propname))
            setattr(dataptr, active_propname, getattr(dataptr, active_propname) - 1)
        except IndexError:
            pass
        return {"FINISHED"}

    # def execute_move(self, context: bpy.types.Context, dataptr, propname: str, active_propname: str) -> set[str]:
    #     propscol = getattr(dataptr, propname)
    #     active_index = getattr(dataptr, active_propname)
    #     new_active_index = max(0, min(active_index + self.move_direction, len(propscol) - 1))
    #     propscol.move(active_index, new_active_index)
    #     setattr(dataptr, active_propname, new_active_index)
    #     return {"FINISHED"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        scene = context.scene
        args = {
            "JOB": (context, scene, "cam_jobs", "cam_job_active_index"),
            "OPERATION": (
                context,
                len(scene.cam_jobs) != 0 and scene.cam_job,
                "operations",
                "operation_active_index",
            ),
        }
        _, suffix = self.type.split("_")
        return self.execute_funcs[self.type](*args[suffix])


CLASSES = [CAM_OT_AddPresetCutter, CAM_OT_AddPresetMachine, CAM_OT_Action]


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
