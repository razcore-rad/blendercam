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


def get_keys(prop):
    return {key for key in prop.rna_type.properties.keys() if key != "rna_type"}


class CAM_Jobs(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="Job")
    do_simplify: bpy.props.BoolProperty(name="Simplify G-code", default=True)
    do_export: bpy.props.BoolProperty(name="Export on compute", default=False)


class CAM_UL_Jobs(bpy.types.UIList):
    def draw_item(
        self,
        _context,
        layout,
        _data,
        item,
        icon,
        _active_data,
        _active_propname,
        _index,
    ):
        cam_job = item
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(cam_job, "name", emboss=False, translate=False, icon_value=icon)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class CAM_PT_Panel(bpy.types.Panel):
    bl_label = "CAM Jobs"
    bl_category = "CAM"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        cam_jobs_are_sortable = len(scene.cam_jobs) > 1
        rows = 5 if cam_jobs_are_sortable else 3

        row = layout.row()
        row.template_list(
            "CAM_UL_Jobs",
            "",
            scene,
            "cam_jobs",
            scene,
            "cam_job_active_index",
            rows=rows,
        )

        col = row.column(align=True)
        col.operator("scene.cam_job_action", icon="ADD", text="").type = "ADD"
        col.operator(
            "scene.cam_job_action", icon="DUPLICATE", text=""
        ).type = "DUPLICATE"
        col.operator("scene.cam_job_action", icon="REMOVE", text="").type = "REMOVE"

        if cam_jobs_are_sortable:
            col.separator()

            operator = col.operator("scene.cam_job_action", icon="TRIA_UP", text="")
            operator.type = "MOVE"
            operator.direction = -1

            operator = col.operator("scene.cam_job_action", icon="TRIA_DOWN", text="")
            operator.type = "MOVE"
            operator.direction = 1

        try:
            cam_job = scene.cam_jobs[scene.cam_job_active_index]

            row = layout.row()
            col = row.column(align=True)
            for key in get_keys(cam_job):
                if key == "name":
                    continue

                col.prop(cam_job, key)
        except IndexError:
            pass


class CAM_OT_JobAction(bpy.types.Operator):
    bl_idname = "scene.cam_job_action"
    bl_label = "CAM Job Action"
    bl_options = {"UNDO"}

    type: bpy.props.EnumProperty(
        items=[
            ("ADD", "JobAdd", "Add CAM job"),
            ("REMOVE", "JobRemove", "Remove CAM job"),
            ("MOVE", "JobMove", "Move CAM Job"),
            ("DUPLICATE", "JobDuplicate", "Duplicate CAM job"),
        ]
    )
    direction: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        scene = context.scene

        if self.type == "ADD":
            cam_job = scene.cam_jobs.add()
            scene.cam_job_active_index = len(scene.cam_jobs) - 1

        elif self.type == "REMOVE":
            scene.cam_jobs.remove(scene.cam_job_active_index)
            scene.cam_job_active_index -= 1

        elif self.type == "MOVE":
            cam_job_new_active_index = scene.cam_job_active_index + self.direction
            cam_job_new_active_index = min(
                cam_job_new_active_index, len(scene.cam_jobs) - 1
            )
            cam_job_new_active_index = max(0, cam_job_new_active_index)
            scene.cam_jobs.move(scene.cam_job_active_index, cam_job_new_active_index)
            scene.cam_job_active_index = cam_job_new_active_index

        elif self.type == "DUPLICATE" and len(scene.cam_jobs) > 0:
            current_cam_job = scene.cam_jobs[scene.cam_job_active_index]
            cam_job = scene.cam_jobs.add()
            for key in get_keys(current_cam_job):
                setattr(cam_job, key, getattr(current_cam_job, key))
            cam_job.name = f"{current_cam_job.name}_copy"
            scene.cam_job_active_index = len(scene.cam_jobs) - 1

        return {"FINISHED"}


classes = [
    CAM_Jobs,
    CAM_OT_JobAction,
    CAM_PT_Panel,
    CAM_UL_Jobs,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cam_jobs = bpy.props.CollectionProperty(type=CAM_Jobs)
    bpy.types.Scene.cam_job_active_index = bpy.props.IntProperty(
        name="Active CAM Job Index",
        description="The selected CAM job index",
        default=0,
        min=0,
    )


def unregister():
    del bpy.types.Scene.cam_jobs
    del bpy.types.Scene.cam_job_active_index
    for c in classes:
        bpy.utils.unregister_class(c)
