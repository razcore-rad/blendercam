from functools import reduce

import bpy

from . import ops


def get_propnames(props: bpy.types.PropertyGroup, use_exclude_propnames=True):
    exclude_propnames = ["rna_type"]
    if use_exclude_propnames:
        exclude_propnames += getattr(props, "exclude_propnames", [])
    return sorted({propname for propname in props.rna_type.properties.keys() if propname not in exclude_propnames})


def get_icon(props: bpy.types.Property, propname: str) -> str:
    return getattr(props, "ICON_MAP", {}).get(propname, "NONE")


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


class CAM_PT_PanelBase(bpy.types.Panel):
    bl_category = "CAM"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def __init__(self):
        super().__init__()
        self.layout.use_property_decorate = False


class CAM_PT_Panel(CAM_PT_PanelBase):
    def draw_list_row(self, list_id: str, dataptr, propname: str, active_propname: str, suffix: str) -> None:
        list_is_sortable = len(getattr(dataptr, propname)) > 1
        rows = 5 if list_is_sortable else 3

        layout = self.layout
        row = layout.row()
        row.template_list("CAM_UL_List", list_id, dataptr, propname, dataptr, active_propname, rows=rows)

        col = row.column(align=True)
        props = col.operator(ops.CAM_OT_Action.bl_idname, icon="ADD", text="")
        props.type = f"ADD_{suffix}"

        props = col.operator(ops.CAM_OT_Action.bl_idname, icon="DUPLICATE", text="")
        props.type = f"DUPLICATE_{suffix}"

        props = col.operator(ops.CAM_OT_Action.bl_idname, icon="REMOVE", text="")
        props.type = f"REMOVE_{suffix}"

        if list_is_sortable:
            col.separator()
            props = col.operator(ops.CAM_OT_Action.bl_idname, icon="TRIA_UP", text="")
            props.type = f"MOVE_{suffix}"
            props.move_direction = -1

            props = col.operator(ops.CAM_OT_Action.bl_idname, icon="TRIA_DOWN", text="")
            props.type = f"MOVE_{suffix}"
            props.move_direction = 1


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
            props = row.operator(ops.CAM_OT_Action.bl_idname, text="Compute", icon="PLAY")
            props.type = "COMPUTE_JOB"

            props = row.operator(ops.CAM_OT_Action.bl_idname, text="Export", icon="EXPORT")
            props.type = "EXPORT_JOB"
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

            layout = self.layout
            col = layout.box().column(align=True)
            col.prop(operation, "strategy_type")
            strategy_propname = f"{operation.strategy_type.lower()}_strategy"
            if hasattr(operation, strategy_propname):
                props = getattr(operation, strategy_propname)
                col.row().prop(props, "source_type", expand=True)
                col.prop(
                    props,
                    f"{props.source_type.lower()}_source",
                    icon=get_enum_item_icon(props.source_type_items, props.source_type),
                )
                for propname in get_propnames(props):
                    col.prop(props, propname, icon=get_icon(props, propname))
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

        col = layout.column(align=True)
        col.use_property_split = True
        col.prop(operation_work_area, "layer_size")
        col.row(align=True).prop(operation_work_area, "ambient", expand=True)
        col.prop(operation_work_area, "curve_limit", icon="OUTLINER_OB_CURVE")


class CAM_PT_PanelJobStock(CAM_PT_PanelBase):
    bl_label = "Stock"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        stock = scene.cam_jobs[scene.cam_job_active_index].stock

        layout = self.layout
        col = layout.column(align=True)
        col.use_property_split = True
        col.prop(stock, "type", expand=True)
        row = layout.row(align=True)
        for propname in (pn for pn in get_propnames(stock) if pn.startswith(stock.type.lower())):
            row.column().prop(stock, propname)


class CAM_PT_PanelJobPostProcessor(CAM_PT_PanelBase):
    bl_label = "Post Processor"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        cam_job = scene.cam_jobs[scene.cam_job_active_index]
        post_processor = cam_job.post_processor

        layout = self.layout
        col = layout.box().column(align=True)
        col.use_property_split = True
        for propname in get_propnames(post_processor):
            col.prop(post_processor, propname, expand=True)
