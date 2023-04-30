import bpy
from bl_operators.presets import AddPresetBase
from bpy.props import EnumProperty, IntProperty, StringProperty
from bpy.types import Context, Operator

from .utils import copy, noop


class CAM_OT_AddPresetMachine(AddPresetBase, Operator):
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
        # "machine.feedrate.default",
        # "machine.feedrate.min",
        # "machine.feedrate.max",
        # "machine.spindle.default",
        # "machine.spindle.min",
        # "machine.spindle.max",
        "machine.axes",
    ]


class CAM_OT_AddPresetCutter(AddPresetBase, Operator):
    """Add or remove a CAM Cutter Preset"""

    bl_idname = "cam.preset_add_cutter"
    bl_label = "Add Cutter Preset"
    preset_menu = "CAM_PT_CutterPresets"
    preset_subdir = "cam/cutters"

    preset_defines = ["operation = bpy.context.scene.cam_job.operation"]

    # @property
    # def preset_values(self) -> list[str]:
    #     result = [
    #         "operation.cutter_type",
    #         "operation.cutter.id",
    #         "operation.cutter.description",
    #         "operation.cutter.diameter",
    #     ]

    #     operation = bpy.context.scene.cam_job.operation

    #     if isinstance(operation.cutter, props.cam_job.operation.cutter.Mill):
    #         result.extend(
    #             [
    #                 "operation.cutter.flutes",
    #                 "operation.cutter.length",
    #             ]
    #         )
    #     elif isinstance(operation.cutter, props.cam_job.operation.cutter.Drill):
    #         result.extend(["operation.cutter.length"])
    #     elif isinstance(operation.cutter, props.cam_job.operation.cutter.ConeMill):
    #         result.extend(
    #             [
    #                 "operation.cutter.length",
    #                 "operation.cutter.angle",
    #             ]
    #         )
    #     return result


class CAM_OT_Action(Operator):
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
        ("ADD_TOOL", "Add CAM tool", "Add CAM tool"),
        ("DUPLICATE_TOOL", "Duplicate CAM tool", "Duplicate CAM tool"),
        ("REMOVE_TOOL", "Remove CAM tool", "Remove CAM tool"),
        ("MOVE_TOOL", "Move CAM tool", "Move CAM tool"),
    ]
    type: EnumProperty(items=type_items)
    move_direction: IntProperty()

    def __init__(self):
        super().__init__()
        self.computed = {}
        self.execute_funcs = {
            id: getattr(self, f"execute_{id.split('_')[0].lower()}", self.execute_todo)
            for id, *_ in self.type_items
        }

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.scene is not None

    def execute_todo(
        self, context: Context, dataptr, propname: str, active_propname: str
    ) -> set[str]:
        self.report({"INFO"}, f"{self.bl_idname}:{self.type}:NOT_IMPLTEMENTED_YET")
        return {"FINISHED"}

    def execute_add(
        self, context: Context, dataptr, propname: str, active_propname: str
    ) -> set[str]:
        propscol = getattr(dataptr, propname)
        propscol.add()
        getattr(propscol[-1], "add_data", noop)(context)
        setattr(dataptr, active_propname, len(propscol) - 1)
        getattr(dataptr, "save", noop)()
        return {"FINISHED"}

    def execute_compute(
        self, context: Context, dataptr, propname: str, active_propname: str
    ) -> set[str]:
        return context.scene.cam_job.execute_compute(context, self.report)

    def execute_export(
        self, context: Context, dataptr, propname: str, active_propname: str
    ) -> set[str]:
        return context.scene.cam_job.execute_export(context)

    def execute_duplicate(
        self, context: Context, dataptr, propname: str, active_propname: str
    ) -> set[str]:
        result = {"FINISHED"}
        propscol = getattr(dataptr, propname)
        if not propscol:
            return result
        active_index = getattr(dataptr, active_propname)
        propscol.add()
        prop = propscol[-1]
        copy(context, propscol[active_index], prop)
        setattr(dataptr, active_propname, active_index + 1)
        getattr(prop, "add_data", noop)(context)
        getattr(prop, "save", noop)()
        return result

    def execute_remove(
        self, context: Context, dataptr, propname: str, active_propname: str
    ) -> set[str]:
        try:
            propscol = getattr(dataptr, propname)
            item = propscol[getattr(dataptr, active_propname)]
            getattr(item, "remove_data", noop)()
            propscol.remove(getattr(dataptr, active_propname))
            setattr(dataptr, active_propname, getattr(dataptr, active_propname) - 1)
            getattr(dataptr, "save", noop)()
        except IndexError:
            pass
        return {"FINISHED"}

    def execute_move(
        self, context: Context, dataptr, propname: str, active_propname: str
    ) -> set[str]:
        propscol = getattr(dataptr, propname)
        active_index = getattr(dataptr, active_propname)
        new_active_index = max(
            0, min(active_index + self.move_direction, len(propscol) - 1)
        )
        propscol.move(active_index, new_active_index)
        setattr(dataptr, active_propname, new_active_index)
        return {"FINISHED"}

    def execute(self, context: Context) -> set[str]:
        scene = context.scene
        args = {
            "JOB": (context, scene, "cam_jobs", "cam_job_active_index"),
            "OPERATION": (
                context,
                len(scene.cam_jobs) != 0 and scene.cam_job,
                "operations",
                "operation_active_index",
            ),
            "TOOL": (context, scene.cam_tools_library, "tools", "tool_active_index"),
        }
        _, suffix = self.type.split("_")
        return self.execute_funcs[self.type](*args[suffix])


class CAM_OT_ToolLibrary(Operator):
    bl_idname = "cam.tool_library"
    bl_label = "CAM Tool Library"

    library_name: StringProperty(name="Library Name", default="New Library")
    type: EnumProperty(
        name="Type",
        items=[
            ("ADD", "Add", "Add CAM tool library"),
            ("REMOVE", "Remove", "Remove CAM tool library"),
        ],
    )

    @classmethod
    def poll(self, context: Context) -> bool:
        return context.window_manager is not None

    def execute(self, context: Context) -> set[str]:
        cam_tools_library = context.scene.cam_tools_library
        cam_tools_library.add_library(context, self.library_name)
        return {"FINISHED"}

    def invoke(self, context: Context, event) -> set[str]:
        result = {"FINISHED"}
        if self.type == "REMOVE":
            cam_tools_library = context.scene.cam_tools_library
            cam_tools_library.remove_library()
        else:
            result = context.window_manager.invoke_props_dialog(self)
        return result

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "library_name")


CLASSES = [
    CAM_OT_AddPresetCutter,
    CAM_OT_AddPresetMachine,
    CAM_OT_Action,
    CAM_OT_ToolLibrary,
]


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
