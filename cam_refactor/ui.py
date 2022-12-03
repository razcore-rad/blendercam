from functools import reduce

import bpy

from . import ops, props


def get_icon(p: bpy.types.Property, propname: str) -> str:
    return getattr(p, "ICON_MAP", {}).get(propname, "NONE")


def get_enum_item_icon(items: list[tuple], item_type: str) -> str:
    return reduce(lambda acc, item: item[-2] if item_type == item[0] and len(item) == 5 else acc, items, "NONE")


class CAM_UL_List(bpy.types.UIList):
    ICON_MAP = {
        "is_hidden": {True: "HIDE_ON", False: "HIDE_OFF"},
        "use_modifiers": {True: "MODIFIER_ON", False: "MODIFIER_OFF"},
    }

    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row0 = layout.row()
            row0.prop(item, "name", text="", emboss=False, icon_value=icon)

            row1 = layout.row(align=True)
            for propname in self.ICON_MAP:
                if hasattr(item, propname):
                    row1.prop(
                        item,
                        propname,
                        text="",
                        emboss=False,
                        icon=self.ICON_MAP[propname][getattr(item, propname)],
                    )

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class PresetPanel:
    bl_label = "Presets"
    path_menu = bpy.types.Menu.path_menu

    @classmethod
    def draw_panel_header(cls, layout: bpy.types.UILayout) -> None:
        layout.emboss = "NONE"
        layout.popover(panel=cls.__name__, icon="PRESET", text="")

    @classmethod
    def draw_menu(cls, layout, text=None) -> None:
        text = text or cls.bl_label
        layout.popover(panel=cls.__name__, icon="PRESET", text=text)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.emboss = "PULLDOWN_MENU"
        layout.operator_context = "EXEC_DEFAULT"
        bpy.types.Menu.draw_preset(self, context)


class CAM_PT_PanelBase(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CAM"

    def __init__(self):
        super().__init__()
        self.layout.use_property_decorate = False

    def draw_property_group(self, pg: bpy.types.PropertyGroup, layout: bpy.types.UILayout = None) -> None:
        layout = self.layout.box().column(align=True) if layout is None else layout
        layout.use_property_split = True
        for propname in props.get_propnames(pg):
            if isinstance(getattr(pg, propname), bpy.types.PropertyGroup):
                continue
            layout.row().prop(pg, propname, icon=get_icon(pg, propname), expand=propname.endswith("type"))


class CAM_PT_MachinePresets(PresetPanel, CAM_PT_PanelBase):
    bl_label = "Machine Presets"
    preset_subdir = "cam/machines"
    preset_operator = "script.execute_preset"
    preset_add_operator = "cam.preset_add_machine"


class CAM_PT_Panel(CAM_PT_PanelBase):
    def draw_list_row(self, list_id: str, dataptr, propname: str, active_propname: str, suffix: str) -> None:
        list_is_sortable = len(getattr(dataptr, propname)) > 1
        rows = 5 if list_is_sortable else 3

        layout = self.layout
        row = layout.row()
        row.template_list("CAM_UL_List", list_id, dataptr, propname, dataptr, active_propname, rows=rows)

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

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        self.draw_list_row("CAM_UL_ListJobs", scene, "cam_jobs", "cam_job_active_index", "JOB")
        try:
            cam_job = scene.cam_jobs[scene.cam_job_active_index]

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
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        cam_job = scene.cam_jobs[scene.cam_job_active_index]
        self.draw_list_row("CAM_UL_ListOperations", cam_job, "operations", "operation_active_index", "OPERATION")
        try:
            operation = cam_job.operations[cam_job.operation_active_index]
            strategy = operation.strategy

            layout = self.layout
            col = layout.box().column(align=True)
            col.prop(operation, "strategy_type")
            col.row().prop(strategy, "source_type", expand=True)

            row = col.row()
            row.use_property_split = True
            row.prop(
                strategy,
                f"{strategy.source_type.lower()}_source",
                icon=get_enum_item_icon(strategy.source_type_items, strategy.source_type),
            )
            self.draw_property_group(strategy, col)
            self.draw_property_group(operation.movement)
        except IndexError:
            pass


class CAM_PT_PanelJobsOperationWorkArea(CAM_PT_PanelBase):
    bl_label = "Work Area"
    bl_parent_id = "CAM_PT_PanelJobsOperations"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        result = False
        try:
            scene = context.scene
            cam_job = scene.cam_jobs[scene.cam_job_active_index]
            operation = cam_job.operations[cam_job.operation_active_index]
            result = len(cam_job.operations) > 0 and operation.strategy.is_source_valid
        except IndexError:
            pass
        return result

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        cam_job = context.scene.cam_jobs[scene.cam_job_active_index]
        operation_work_area = cam_job.operations[cam_job.operation_active_index].work_area

        layout = self.layout
        col = layout.box().column(align=True)
        row = col.row(align=True)
        row.prop(operation_work_area, "depth_start")
        if operation_work_area.depth_end_type == "CUSTOM":
            row.prop(operation_work_area, "depth_end")

        row = col.row()
        row.use_property_split = True
        row.prop(operation_work_area, "depth_end_type", expand=True)
        self.draw_property_group(operation_work_area)


class CAM_PT_PanelJobsStock(CAM_PT_PanelBase):
    bl_label = "Stock"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        stock = scene.cam_jobs[scene.cam_job_active_index].stock

        layout = self.layout
        layout.row().prop(stock, "type", expand=True)
        row = layout.row(align=True)
        for propname in (pn for pn in props.get_propnames(stock) if pn.startswith(stock.type.lower())):
            row.column().prop(stock, propname)


class CAM_PT_PanelJobsMachine(CAM_PT_PanelBase):
    bl_label = "Machine"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw_header_preset(self, _context: bpy.types.Context) -> None:
        CAM_PT_MachinePresets.draw_panel_header(self.layout)

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        cam_job_machine = scene.cam_jobs[scene.cam_job_active_index].machine

        self.draw_property_group(cam_job_machine)
        col = self.layout.box().column(align=True)
        col.use_property_split = True
        col.prop(cam_job_machine, "post_processor")


CLASSES = [
    CAM_UL_List,
    CAM_PT_MachinePresets,
    CAM_PT_PanelJobs,
    CAM_PT_PanelJobsOperations,
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
