from functools import reduce

import bpy
from bpy.types import Context, Menu, Panel, PropertyGroup, UIList, UILayout

from .props.camjob.operation import Operation
from . import ops, utils


UNITS = {"MIN": "/ min"}


def get_enum_item_icon(items: [(str, str, str, str, int)], item_type: str) -> str:
    return reduce(
        lambda acc, item: item[-2] if item_type == item[0] and len(item) == 5 else acc,
        items,
        "NONE",
    )


class CAM_UL_List(UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            if hasattr(item, "data") and item.data is not None:
                layout.row().prop(
                    item.data, "name", text="", emboss=False, icon_value=icon
                )
                layout.row(align=True).prop(
                    item.data, "hide_viewport", text="", emboss=False
                )
            else:
                layout.row().prop(item, "name", text="", emboss=False, icon_value=icon)
                if isinstance(item, Operation):
                    icon = "HIDE_ON" if item.is_hidden else "HIDE_OFF"
                    layout.row(align=True).prop(
                        item, "is_hidden", text="", emboss=False, icon=icon
                    )
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class PresetPanel:
    bl_label = "Presets"
    bl_category = "CAM"
    path_menu = Menu.path_menu

    @classmethod
    def draw_panel_header(cls, layout: UILayout) -> None:
        layout.emboss = "NONE"
        layout.popover(panel=cls.__name__, icon="PRESET", text="")

    @classmethod
    def draw_menu(cls, layout, text=None) -> None:
        text = text or cls.bl_label
        layout.popover(panel=cls.__name__, icon="PRESET", text=text)

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.emboss = "PULLDOWN_MENU"
        layout.operator_context = "EXEC_DEFAULT"
        Menu.draw_preset(self, context)


class CAM_PT_PanelBase(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CAM"

    def __init__(self):
        super().__init__()
        self.layout.use_property_decorate = False

    def draw_property_group(
        self,
        pg: PropertyGroup,
        *,
        layout: UILayout = None,
        label_text=None,
    ) -> None:
        if layout is None:
            layout = self.layout.box().column(align=True)
            layout.use_property_split = True

        for propname in utils.get_propnames(pg):
            if isinstance(getattr(pg, propname), PropertyGroup):
                continue

            row = layout.row(align=True)
            if label_text is not None:
                split = layout.split(factor=0.85, align=True)
                row = split.row(align=True)
            row.prop(pg, propname, expand=propname.endswith("type"))
            if label_text is not None:
                row = split.row(align=True)
                row.alignment = "RIGHT"
                row.label(text=label_text)


class CAM_PT_PanelJobsOperationSubPanel(CAM_PT_PanelBase):
    @classmethod
    def poll(cls, context: Context) -> bool:
        result = False
        try:
            strategy = context.scene.cam_job.operation.strategy
            result = strategy.get_source(context) is not [] and getattr(
                strategy, "curve", True
            )
        except IndexError:
            pass
        return result


class CAM_PT_MachinePresets(PresetPanel, Panel):
    bl_space_type = CAM_PT_PanelBase.bl_space_type
    bl_region_type = CAM_PT_PanelBase.bl_region_type
    bl_label = "Machine Presets"
    preset_subdir = "cam/machines"
    preset_operator = "script.execute_preset"
    preset_add_operator = "cam.preset_add_machine"


class CAM_PT_CutterPresets(PresetPanel, Panel):
    bl_space_type = CAM_PT_PanelBase.bl_space_type
    bl_region_type = CAM_PT_PanelBase.bl_region_type
    bl_label = "Cutter Presets"
    preset_subdir = "cam/cutters"
    preset_operator = "script.execute_preset"
    preset_add_operator = "cam.preset_add_cutter"


class CAM_PT_Panel(CAM_PT_PanelBase):
    def draw_list_row(
        self, list_id: str, dataptr, propname: str, active_propname: str, suffix: str
    ) -> None:
        list_is_sortable = len(getattr(dataptr, propname)) > 1
        rows = 5 if list_is_sortable else 3

        layout = self.layout
        row = layout.row()
        row.template_list(
            "CAM_UL_List",
            list_id,
            dataptr,
            propname,
            dataptr,
            active_propname,
            rows=rows,
        )

        col = row.column(align=True)
        pg = col.operator(ops.CAM_OT_Action.bl_idname, icon="ADD", text="")
        pg.type = f"ADD_{suffix}"

        pg = col.operator(ops.CAM_OT_Action.bl_idname, icon="DUPLICATE", text="")
        pg.type = f"DUPLICATE_{suffix}"

        pg = col.operator(ops.CAM_OT_Action.bl_idname, icon="REMOVE", text="")
        pg.type = f"REMOVE_{suffix}"

        if list_is_sortable:
            col.separator()
            pg = col.operator(ops.CAM_OT_Action.bl_idname, icon="TRIA_UP", text="")
            pg.type = f"MOVE_{suffix}"
            pg.move_direction = -1

            pg = col.operator(ops.CAM_OT_Action.bl_idname, icon="TRIA_DOWN", text="")
            pg.type = f"MOVE_{suffix}"
            pg.move_direction = 1


class CAM_PT_PanelJobs(CAM_PT_Panel):
    bl_label = "CAM Jobs"

    def draw(self, context: Context) -> None:
        scene = context.scene
        self.draw_list_row(
            "CAM_UL_ListJobs", scene, "cam_jobs", "cam_job_active_index", "JOB"
        )
        try:
            cam_job = scene.cam_job

            layout = self.layout
            row = layout.row()
            col = row.column(align=True)

            if all(count_coord == 1 for count_coord in cam_job.count):
                col.prop(cam_job, "count")
            else:
                split = col.split()
                col = split.column()
                col.prop(cam_job, "count")

                col = split.column()
                col.prop(cam_job, "gap")

            row = layout.row(align=True)
            pg = row.operator(ops.CAM_OT_Action.bl_idname, text="Compute", icon="PLAY")
            pg.type = "COMPUTE_JOB"

            pg = row.operator(ops.CAM_OT_Action.bl_idname, text="Export", icon="EXPORT")
            pg.type = "EXPORT_JOB"
        except IndexError:
            pass


class CAM_PT_PanelJobsOperations(CAM_PT_Panel):
    bl_label = "Operations"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw(self, context: Context) -> None:
        scene = context.scene
        cam_job = scene.cam_job
        self.draw_list_row(
            "CAM_UL_ListOperations",
            cam_job,
            "operations",
            "operation_active_index",
            "OPERATION",
        )
        try:
            operation = cam_job.operation
            strategy = operation.strategy

            layout = self.layout
            col = layout.box().column(align=True)
            col.prop(operation, "strategy_type")
            col.row().prop(strategy, "source_type", expand=True)

            col.row().prop(
                strategy,
                strategy.source_propname,
                icon=get_enum_item_icon(
                    strategy.source_type_items, strategy.source_type
                ),
            )
            self.draw_property_group(strategy, layout=col)
        except IndexError:
            pass


class CAM_PT_PanelJobsOperationCutter(CAM_PT_PanelJobsOperationSubPanel):
    bl_label = "Cutter"
    bl_parent_id = "CAM_PT_PanelJobsOperations"

    def draw_header_preset(self, context: Context) -> None:
        CAM_PT_CutterPresets.draw_panel_header(self.layout)

    def draw(self, context: Context) -> None:
        operation = context.scene.cam_job.operation
        cutter = operation.cutter
        col = self.layout.box().column(align=True)
        col.use_property_split = True
        col.prop(operation, "cutter_type")
        col.prop(cutter, "id")
        col.prop(cutter, "description")
        col.use_property_split = False
        self.draw_property_group(cutter, layout=col)


class CAM_PT_PanelJobsOperationFeedMovementSpindle(CAM_PT_PanelJobsOperationSubPanel):
    bl_label = "Feed, Movement & Spindle"
    bl_parent_id = "CAM_PT_PanelJobsOperations"

    def draw(self, context: Context) -> None:
        operation = context.scene.cam_job.operation
        if operation.strategy_type == "DRILL":
            layout = self.layout.box().column(align=True)
            layout.use_property_split = True
            row = layout.row(align=True)
            row.prop(operation.movement, "rapid_height")
        else:
            self.draw_property_group(operation.movement)
        self.draw_property_group(operation.spindle)

        col = self.layout.box().column(align=True)
        split = col.split(factor=0.85, align=True)
        split.row().prop(operation.feed, "rate")
        row = split.row()
        row.alignment = "RIGHT"
        row.label(text=UNITS["MIN"])
        self.draw_property_group(operation.feed, layout=col)


class CAM_PT_PanelJobsOperationWorkArea(CAM_PT_PanelJobsOperationSubPanel):
    bl_label = "Work Area"
    bl_parent_id = "CAM_PT_PanelJobsOperations"

    def draw(self, context: Context) -> None:
        operation = context.scene.cam_job.operation
        work_area = operation.work_area

        layout = self.layout
        col = layout.box().column(align=True)
        col.prop(work_area, "layer_size")
        if operation.strategy_type in {"DRILL", "PROFILE"}:
            row = col.row(align=True)
            if work_area.depth_end_type == "CUSTOM":
                row.prop(work_area, "depth_end")
            row = col.row()
            row.use_property_split = True
            row.prop(work_area, "depth_end_type", expand=True)
        # self.draw_property_group(work_area)


class CAM_PT_PanelJobsStock(CAM_PT_PanelBase):
    bl_label = "Stock"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw(self, context: Context) -> None:
        stock = context.scene.cam_job.stock

        layout = self.layout
        layout.row().prop(stock, "type", expand=True)
        row = layout.row(align=True)
        for propname in (
            pn for pn in utils.get_propnames(stock) if pn.startswith(stock.type.lower())
        ):
            row.column().prop(stock, propname)


class CAM_PT_PanelJobsMachine(CAM_PT_PanelBase):
    bl_label = "Machine"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw_header_preset(self, context: Context) -> None:
        CAM_PT_MachinePresets.draw_panel_header(self.layout)

    def draw(self, context: Context) -> None:
        machine = context.scene.cam_job.machine
        post_processor = machine.post_processor

        layout = self.layout
        box = layout.box()
        box.prop(machine, "post_processor_enum")
        # box.prop(post_processor, "use_custom_positions")
        # if post_processor.use_custom_positions:
        # self.draw_property_group(
        # post_processor.custom_positions, layout=box.column(align=True)
        # )
        self.draw_property_group(post_processor, layout=box.column(align=True))

        box = layout.box()
        box.prop(machine, "axes")

        # self.draw_property_group(
        #     machine.feed_rate,
        #     layout=layout.box().column(align=True),
        #     label_text=UNITS["MIN"],
        # )
        # self.draw_property_group(
        #     machine.spindle_rpm, layout=layout.box().column(align=True)
        # )


CLASSES = [
    CAM_UL_List,
    CAM_PT_CutterPresets,
    CAM_PT_MachinePresets,
    CAM_PT_PanelJobs,
    CAM_PT_PanelJobsOperations,
    CAM_PT_PanelJobsOperationCutter,
    CAM_PT_PanelJobsOperationFeedMovementSpindle,
    CAM_PT_PanelJobsOperationWorkArea,
    CAM_PT_PanelJobsStock,
    CAM_PT_PanelJobsMachine,
]


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
