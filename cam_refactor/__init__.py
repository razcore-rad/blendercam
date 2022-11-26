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


EXCLUDE_PROPNAMES = {"rna_type"}


class CAM_PropertyGroup(bpy.types.PropertyGroup):
    def copy_to(self, other: bpy.types.PropertyGroup) -> None:
        for propname in get_propnames(other):
            self_prop = getattr(self, propname)
            if isinstance(self_prop, bpy.types.bpy_prop_collection):
                other_collection = getattr(other, propname)
                other_collection.clear()
                for prop in self_prop.values():
                    other_prop = other_collection.add()
                    for propname in get_propnames(other_prop):
                        setattr(other_prop, propname, getattr(prop, propname))
            else:
                setattr(other, propname, self_prop)
                if propname == "name":
                    other.name = f"{other.name}_copy"


def get_propnames(props: CAM_PropertyGroup):
    return {
        propname
        for propname in props.rna_type.properties.keys()
        if propname not in EXCLUDE_PROPNAMES
    }


class CAM_Jobs(CAM_PropertyGroup):
    class Operation(CAM_PropertyGroup):
        name: bpy.props.StringProperty(default="Operation")
        data_source: bpy.props.EnumProperty(
            items=[
                ("OBJECT", "Object", "Object Data Source", "OBJECT_DATA", 0),
                (
                    "COLLECTION",
                    "Collection",
                    "Collection Data Source",
                    "OUTLINER_COLLECTION",
                    1,
                ),
            ],
            name="Data Source",
        )

    name: bpy.props.StringProperty(name="Name", default="Job")
    do_simplify: bpy.props.BoolProperty(name="Simplify G-code", default=True)
    do_export: bpy.props.BoolProperty(name="Export on compute", default=False)
    count: bpy.props.IntVectorProperty(
        name="Count", default=(1, 1), min=1, subtype="XYZ", size=2
    )
    gap: bpy.props.FloatVectorProperty(
        name="Gap", default=(0, 0), min=0, subtype="XYZ_LENGTH", size=2
    )
    operations: bpy.props.CollectionProperty(type=Operation)
    operation_active_index: bpy.props.IntProperty(default=0, min=0)


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
        ("DUPLICATE_OPERATION", "Duplicate CAM operation", "Duplicate CAM operation"),
        ("REMOVE_OPERATION", "Remove CAM operation", "Remove CAM operation"),
        ("MOVE_OPERATION", "Move CAM operation", "Move CAM operation"),
    ]
    type: bpy.props.EnumProperty(items=type_items)
    direction: bpy.props.IntProperty()

    def __init__(self):
        super().__init__()
        self.execute_funcs = {
            id: getattr(self, f"execute_{id.split('_')[0].lower()}", self.execute_todo)
            for id, *_ in self.type_items
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
        if propname.startswith("cam"):
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

        current_props = collection[getattr(dataptr, active_propname)]
        props = collection.add()
        current_props.copy_to(props)
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
        new_active_index = max(
            0, min(active_index + self.direction, len(collection) - 1)
        )
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


class CAM_UL_List(bpy.types.UIList):
    def draw_item(
        self, _context, layout, _data, item, icon, _active_data, _active_propname
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(
                item, "name", text="", emboss=False, translate=False, icon_value=icon
            )
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class CAM_PT_Panel(bpy.types.Panel):
    bl_category = "CAM"
    bl_region_type = "UI"
    bl_space_type = "VIEW_3D"

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
        props = col.operator(CAM_OT_Action.bl_idname, icon="ADD", text="")
        props.type = f"ADD_{suffix}"

        props = col.operator(CAM_OT_Action.bl_idname, icon="DUPLICATE", text="")
        props.type = f"DUPLICATE_{suffix}"

        props = col.operator(CAM_OT_Action.bl_idname, icon="REMOVE", text="")
        props.type = f"REMOVE_{suffix}"

        if list_is_sortable:
            col.separator()
            props = col.operator(CAM_OT_Action.bl_idname, icon="TRIA_UP", text="")
            props.type = f"MOVE_{suffix}"
            props.direction = -1

            props = col.operator(CAM_OT_Action.bl_idname, icon="TRIA_DOWN", text="")
            props.type = f"MOVE_{suffix}"
            props.direction = 1


class CAM_PT_PanelJobs(CAM_PT_Panel):
    bl_label = "CAM Jobs"

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        self.draw_list_row(
            "CAM_UL_ListJobs", scene, "cam_jobs", "cam_job_active_index", "JOB"
        )
        try:
            cam_job = scene.cam_jobs[scene.cam_job_active_index]

            layout = self.layout
            row = layout.row()
            col = row.column(align=True)
            col.prop(cam_job, "do_simplify")
            col.prop(cam_job, "do_export")

            if all(count_coord == 1 for count_coord in cam_job.count):
                col.prop(cam_job, "count")
            else:
                split = col.split()
                col = split.column()
                col.prop(cam_job, "count")

                col = split.column()
                col.prop(cam_job, "gap")

            row = layout.row()
            props = row.operator(CAM_OT_Action.bl_idname, text="Compute")
            props.type = "COMPUTE_JOB"
        except IndexError:
            pass


class CAM_PT_PanelOperations(CAM_PT_Panel):
    bl_label = "Operations"
    bl_parent_id = "CAM_PT_PanelJobs"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(context.scene.cam_jobs) > 0

    def draw(self, context: bpy.types.Context) -> None:
        scene = context.scene
        cam_job = scene.cam_jobs[scene.cam_job_active_index]
        self.draw_list_row(
            "CAM_UL_ListOperations",
            cam_job,
            "operations",
            "operation_active_index",
            "OPERATION",
        )
        try:
            operation = cam_job.operations[cam_job.operation_active_index]

            layout = self.layout
            row = layout.row()
            row.use_property_split = True
            row.use_property_decorate = False
            row.prop(operation, "data_source", expand=True)
        except IndexError:
            pass


classes = [
    CAM_Jobs.Operation,
    CAM_Jobs,
    CAM_OT_Action,
    CAM_UL_List,
    CAM_PT_PanelJobs,
    CAM_PT_PanelOperations,
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
