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


PRECISION = 5


def copy(from_prop: bpy.types.Property, to_prop: bpy.types.Property, depth=0) -> None:
    if type(from_prop) != type(to_prop):
        return

    if isinstance(from_prop, bpy.types.PropertyGroup):
        for propname in get_propnames(to_prop, use_exclude_propnames=False):
            from_subprop = getattr(from_prop, propname)
            if isinstance(from_subprop, bpy.types.PropertyGroup) or isinstance(
                from_subprop, bpy.types.bpy_prop_collection
            ):
                copy(from_subprop, getattr(to_prop, propname), depth + 1)
            else:
                setattr(to_prop, propname, from_subprop)
                if propname == "name" and depth == 0:
                    to_prop.name += "_copy"

    elif isinstance(from_prop, bpy.types.bpy_prop_collection):
        to_prop.clear()
        for from_subprop in from_prop.values():
            copy(from_subprop, to_prop.add(), depth + 1)


def get_propnames(props: bpy.types.PropertyGroup, use_exclude_propnames=True):
    exclude_propnames = ["rna_type"]
    if use_exclude_propnames:
        exclude_propnames += getattr(props, "exclude_propnames", [])

    return sorted(
        {
            propname
            for propname in props.rna_type.properties.keys()
            if propname not in exclude_propnames
        }
    )


class CAM_Job(bpy.types.PropertyGroup):
    class Operation(bpy.types.PropertyGroup):
        class DirectionMixin(bpy.types.PropertyGroup):
            direction: bpy.props.EnumProperty(
                items=[
                    ("IN_OUT", "In Out", "In Out"),
                    ("OUT_IN", "Out In", "Out In"),
                ],
                name="Direction",
            )

        class DistanceAlongPathsMixin(bpy.types.PropertyGroup):
            distance_along_paths: bpy.props.FloatProperty(
                name="Distance Along Paths",
                default=2e-4,
                min=1e-5,
                max=32,
                precision=PRECISION,
                unit="LENGTH",
            )

        class DistanceBetweenPathsMixin(bpy.types.PropertyGroup):
            distance_between_paths: bpy.props.FloatProperty(
                name="Distance Between Paths",
                default=1e-3,
                min=1e-5,
                max=32,
                precision=PRECISION,
                unit="LENGTH",
            )

        class PathsAngleMixin(bpy.types.PropertyGroup):
            paths_angle: bpy.props.FloatProperty(
                name="Paths Angle",
                default=0,
                min=-360,
                max=360,
                precision=0,
                subtype="ANGLE",
                unit="ROTATION",
            )

        class SourceMixin(bpy.types.PropertyGroup):
            exclude_propnames = [
                "name",
                "source_type",
                "mesh_source",
                "collection_source",
            ]

            source_type: bpy.props.EnumProperty(
                items=[
                    ("MESH", "Mesh", "Object Data Source", "MESH_DATA", 0),
                    (
                        "COLLECTION",
                        "Collection",
                        "Collection Data Source",
                        "OUTLINER_COLLECTION",
                        1,
                    ),
                ],
                name="Source Type",
            )
            mesh_source: bpy.props.PointerProperty(type=bpy.types.Mesh, name="Source")
            collection_source: bpy.props.PointerProperty(
                type=bpy.types.Collection, name="Source"
            )

        class BlockStrategy(
            DirectionMixin,
            DistanceAlongPathsMixin,
            DistanceBetweenPathsMixin,
            SourceMixin,
        ):
            pass

        class CarveProjectStrategy(DistanceAlongPathsMixin, SourceMixin):
            pass

        class CirclesStrategy(
            DirectionMixin,
            DistanceAlongPathsMixin,
            DistanceBetweenPathsMixin,
            SourceMixin,
        ):
            pass

        class CrossStrategy(
            DistanceAlongPathsMixin,
            DistanceBetweenPathsMixin,
            PathsAngleMixin,
            SourceMixin,
        ):
            pass

        name: bpy.props.StringProperty(default="Operation")
        is_hidden: bpy.props.BoolProperty(default=False)
        use_modifiers: bpy.props.BoolProperty(default=True)

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
                "Medial axis, must be used with V or ball cutter, for engraving various width shapes with a single stroke",
            ),
            (
                "OUTLINE_FILL",
                "Outline Fill",
                "Detect outline and fill it with paths as pocket then sample these paths on the 3D surface",
            ),
            ("POCKET", "Pocket", "Pocket"),
            ("PROFILE", "Profile", "Profile cutout"),
            ("PARALLEL", "Parallel", "Parallel lines at any angle"),
            ("SPIRAL", "Spiral", "Spiral path"),
            (
                "WATERLINE_ROUGHING",
                "Waterline Roughing",
                "Roughing below ZERO. Z is always below ZERO",
            ),
        ]
        strategy_type: bpy.props.EnumProperty(
            items=strategy_type_items, name="Strategy Type"
        )

        block_strategy: bpy.props.PointerProperty(type=BlockStrategy)
        carve_project_strategy: bpy.props.PointerProperty(type=CarveProjectStrategy)
        circles_strategy: bpy.props.PointerProperty(type=CirclesStrategy)
        cross_strategy: bpy.props.PointerProperty(type=CrossStrategy)

    name: bpy.props.StringProperty(name="Name", default="Job")
    is_hidden: bpy.props.BoolProperty(default=False)
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

        copy(collection[getattr(dataptr, active_propname)], collection.add())
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
    ICON_MAP = {
        "is_hidden": {True: "HIDE_ON", False: "HIDE_OFF"},
        "use_modifiers": {True: "MODIFIER_ON", False: "MODIFIER_OFF"},
    }

    def draw_item(
        self, _context, layout, _data, item, icon, _active_data, _active_propname
    ):
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
                        icon=f"{self.ICON_MAP[propname][getattr(item, propname)]}",
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
            layout.use_property_decorate = False

            col = layout.column(align=True)
            col.prop(operation, "strategy_type")
            strategy_attr = f"{operation.strategy_type.lower()}_strategy"
            if hasattr(operation, strategy_attr):
                props = getattr(operation, strategy_attr)
                col.row().prop(props, "source_type", expand=True)
                col.prop(props, f"{props.source_type.lower()}_source")
                for propname in get_propnames(props):
                    col.prop(props, propname)
        except IndexError:
            pass


classes = [
    CAM_Job.Operation.BlockStrategy,
    CAM_Job.Operation.CarveProjectStrategy,
    CAM_Job.Operation.CirclesStrategy,
    CAM_Job.Operation.CrossStrategy,
    CAM_Job.Operation,
    CAM_Job,
    CAM_OT_Action,
    CAM_UL_List,
    CAM_PT_PanelJobs,
    CAM_PT_PanelOperations,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cam_jobs = bpy.props.CollectionProperty(type=CAM_Job)
    bpy.types.Scene.cam_job_active_index = bpy.props.IntProperty(default=0, min=0)


def unregister():
    del bpy.types.Scene.cam_jobs
    del bpy.types.Scene.cam_job_active_index
    for c in classes:
        bpy.utils.unregister_class(c)
