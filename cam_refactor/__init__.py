# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

import bpy

bl_info = {
    "name": "CNC G-Code Tools",
    "author": "Răzvan C. Rădulescu (razcore-rad)",
    "version": (0, 0, 1),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar > CAM",
    "description": "Generate machining paths for CNC",
    "warning": "There is no warranty for the produced G-code",
    "wiki_url": "https://github.com/razcore-rad/blendercam/wiki",
    "tracker_url": "https://github.com/razcore-rad/blendercam/issues",
    "category": "CAM",
}


class CAM_Jobs(bpy.types.PropertyGroup):
    class Operation(bpy.types.PropertyGroup):
        name: bpy.props.StringProperty(default="Operation")

    EXCLUDE_ATTRS = {"rna_type", "name", "operations", "operation_active_index"}

    name: bpy.props.StringProperty(default="Job")
    do_simplify: bpy.props.BoolProperty(name="Simplify G-code", default=True)
    do_export: bpy.props.BoolProperty(name="Export on compute", default=False)
    operations: bpy.props.CollectionProperty(type=Operation)
    operation_active_index: bpy.props.IntProperty(default=0, min=0)

    def attrs(self):
        return {
            attr
            for attr in self.rna_type.properties.keys()
            if attr not in CAM_Jobs.EXCLUDE_ATTRS
        }


class CAM_OT_Action(bpy.types.Operator):
    bl_idname = "scene.cam_action"
    bl_label = "CAM Action"
    bl_options = {"UNDO"}

    type_items = [
        ("ADD_JOB", "Add CAM job", "Add CAM job"),
        ("DUPLICATE_JOB", "Duplicate CAM job", "Duplicate CAM job"),
        ("REMOVE_JOB", "Remove CAM job", "Remove CAM job"),
        ("MOVE_JOB", "Move CAM job", "Move CAM job"),
        ("COMPUTE_JOB", "Compute CAM job", "Compute CAM job"),
        ("ADD_OPERATION", "Add CAM operation", "Add CAM operation"),
        (
            "DUPLICATE_OPERATION",
            "Duplicate CAM operation",
            "Duplicate CAM operation",
        ),
        ("REMOVE_OPERATION", "Remove CAM operation", "Remove CAM operation"),
        ("MOVE_OPERATION", "Move CAM operation", "Move CAM operation"),
        ("COMPUTE_OPERATION", "Compute CAM operation", "Compute CAM operation"),
    ]
    type: bpy.props.EnumProperty(items=type_items)
    direction: bpy.props.IntProperty()

    def __init__(self):
        self.execute_funcs = {
            id: getattr(self, f"execute_{id.lower()}", self.execute_todo)
            for id, *_ in self.type_items
        }

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute_todo(self, context):
        self.report({"INFO"}, f"{self.bl_idname}:{self.type}:NOT_IMPLTEMENTED_YET")
        return {"FINISHED"}

    def execute_add_job(self, scene):
        scene.cam_jobs.add()
        scene.cam_job_active_index = len(scene.cam_jobs) - 1
        self.execute_add_operation(scene)
        return {"FINISHED"}

    def execute_duplicate_job(self, scene):
        result = {"FINISHED"}
        if len(scene.cam_jobs) == 0:
            return result

        current_cam_job = scene.cam_jobs[scene.cam_job_active_index]
        cam_job = scene.cam_jobs.add()
        for key in current_cam_job.attrs():
            setattr(cam_job, key, getattr(current_cam_job, key))
        cam_job.name = f"{current_cam_job.name}_copy"
        scene.cam_job_active_index = len(scene.cam_jobs) - 1
        return result

    def execute_remove_job(self, scene):
        scene.cam_jobs.remove(scene.cam_job_active_index)
        scene.cam_job_active_index -= 1
        return {"FINISHED"}

    def execute_move_job(self, scene):
        cam_job_new_active_index = scene.cam_job_active_index + self.direction
        cam_job_new_active_index = min(
            cam_job_new_active_index, len(scene.cam_jobs) - 1
        )
        cam_job_new_active_index = max(0, cam_job_new_active_index)
        scene.cam_jobs.move(scene.cam_job_active_index, cam_job_new_active_index)
        scene.cam_job_active_index = cam_job_new_active_index
        return {"FINISHED"}

    def execute_add_operation(self, scene):
        cam_job = scene.cam_jobs[scene.cam_job_active_index]
        cam_job.operations.add()
        cam_job.operation_active_index = len(cam_job.operations) - 1
        return {"FINISHED"}

    def execute(self, context):
        return self.execute_funcs[self.type](context.scene)


class CAM_UL_List(bpy.types.UIList):
    def draw_item(
        self,
        _context,
        layout,
        _data,
        item,
        icon,
        _active_data,
        _active_propname,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(item, "name", emboss=False, translate=False, icon_value=icon)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class CAM_PT_Panel(bpy.types.Panel):
    bl_label = "CAM Jobs"
    bl_category = "CAM"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw_list_row(self, list_id, collection, propname, active_propname, suffix):
        layout = self.layout
        list_is_sortable = len(getattr(collection, propname)) > 1
        rows = 5 if list_is_sortable else 3

        row = layout.row()
        row.template_list(
            "CAM_UL_List",
            list_id,
            collection,
            propname,
            collection,
            active_propname,
            rows=rows,
        )

        col = row.column(align=True)
        col.operator(
            CAM_OT_Action.bl_idname, icon="ADD", text=""
        ).type = f"ADD_{suffix}"
        col.operator(
            CAM_OT_Action.bl_idname, icon="DUPLICATE", text=""
        ).type = f"DUPLICATE_{suffix}"
        col.operator(
            CAM_OT_Action.bl_idname, icon="REMOVE", text=""
        ).type = f"REMOVE_{suffix}"

        if list_is_sortable:
            col.separator()

            props = col.operator(CAM_OT_Action.bl_idname, icon="TRIA_UP", text="")
            props.type = f"MOVE_{suffix}"
            props.direction = -1

            props = col.operator(CAM_OT_Action.bl_idname, icon="TRIA_DOWN", text="")
            props.type = f"MOVE_{suffix}"
            props.direction = 1

    def draw(self, context):
        scene = context.scene
        self.draw_list_row(
            "CAM_UL_ListJobs",
            scene,
            "cam_jobs",
            "cam_job_active_index",
            "JOB",
        )
        try:
            layout = self.layout
            row = layout.row()
            col = row.column(align=True)
            cam_job = scene.cam_jobs[scene.cam_job_active_index]
            for key in cam_job.attrs():
                if key == "name":
                    continue

                col.prop(cam_job, key)
            suffix = "OPERATION"
            props = col.operator(CAM_OT_Action.bl_idname, text="Compute")
            props.type = f"COMPUTE_{suffix}"

            self.draw_list_row(
                "CAM_UL_ListOperations",
                cam_job,
                "operations",
                "operation_active_index",
                suffix,
            )
        except IndexError:
            pass


classes = [
    CAM_Jobs.Operation,
    CAM_Jobs,
    CAM_OT_Action,
    CAM_UL_List,
    CAM_PT_Panel,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cam_jobs = bpy.props.CollectionProperty(type=CAM_Jobs)
    bpy.types.Scene.cam_job_active_index = bpy.props.IntProperty(default=0, min=0)


def unregister():
    del bpy.types.Scene.cam_jobs
    del bpy.types.Scene.cam_job_active_index
    for c in classes:
        bpy.utils.unregister_class(c)
