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
        "scene = bpy.context.scene",
        "cam_job = scene.cam_jobs[scene.cam_job_active_index]",
    ]

    preset_values = [
        "cam_job.machine.post_processor",
        "cam_job.machine.working_area",
        "cam_job.machine.feedrate.default",
        "cam_job.machine.feedrate.min",
        "cam_job.machine.feedrate.max",
        "cam_job.machine.spindle.default",
        "cam_job.machine.spindle.min",
        "cam_job.machine.spindle.max",
        "cam_job.machine.axes",
    ]


class CAM_OT_AddPresetCutter(bl_operators.presets.AddPresetBase, bpy.types.Operator):
    """Add or remove a CAM Cutter Preset"""

    bl_idname = "cam.preset_add_cutter"
    bl_label = "Add Cutter Preset"
    preset_menu = "CAM_PT_CutterPresets"
    preset_subdir = "cam/cutters"

    preset_defines = [
        "scene = bpy.context.scene",
        "cam_job = scene.cam_jobs[scene.cam_job_active_index]",
    ]

    @property
    def preset_values(self) -> list[str]:
        result = []

        scene = bpy.context.scene
        cam_job = scene.cam_jobs[scene.cam_job_active_index]
        operation = cam_job.operations[cam_job.operation_active_index]

        result.extend(
            [
                "cam_job.operation.cutter_type",
                "cam_job.operation.cutter.id",
                "cam_job.operation.cutter.description",
                "cam_job.operation.cutter.diameter",
            ]
        )

        if isinstance(operation.cutter, props.camjob.operation.cutter.Mill):
            result.extend(
                [
                    "cam_job.operation.cutter.flutes",
                    "cam_job.operation.cutter.length",
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

    def execute_todo(self, dataptr, propname: str, active_propname: str) -> set:
        self.report({"INFO"}, f"{self.bl_idname}:{self.type}:NOT_IMPLTEMENTED_YET")
        return {"FINISHED"}

    def execute_add(self, dataptr, propname: str, active_propname: str) -> set:
        collection = getattr(dataptr, propname)
        collection.add()
        setattr(dataptr, active_propname, len(collection) - 1)
        if propname == "cam_jobs":
            return self.execute_add(
                dataptr.cam_jobs[dataptr.cam_job_active_index],
                "operations",
                "operation_active_index",
            )
        return {"FINISHED"}

    def execute_duplicate(self, dataptr, propname: str, active_propname: str) -> set:
        result = {"FINISHED"}
        collection = getattr(dataptr, propname)
        if len(collection) == 0:
            return result

        props.utils.copy(collection[getattr(dataptr, active_propname)], collection.add())
        setattr(dataptr, active_propname, len(collection) - 1)
        return result

    def execute_remove(self, dataptr, propname: str, active_propname: str) -> set:
        collection = getattr(dataptr, propname)
        collection.remove(getattr(dataptr, active_propname))
        setattr(dataptr, active_propname, getattr(dataptr, active_propname) - 1)
        return {"FINISHED"}

    def execute_move(self, dataptr, propname: str, active_propname: str) -> set:
        collection = getattr(dataptr, propname)
        active_index = getattr(dataptr, active_propname)
        new_active_index = max(0, min(active_index + self.move_direction, len(collection) - 1))
        collection.move(active_index, new_active_index)
        setattr(dataptr, active_propname, new_active_index)
        return {"FINISHED"}

    def execute(self, context: bpy.types.Context) -> set:
        scene = context.scene
        args = {
            "JOB": (scene, "cam_jobs", "cam_job_active_index"),
            "OPERATION": (
                len(scene.cam_jobs) != 0 and scene.cam_jobs[scene.cam_job_active_index],
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
