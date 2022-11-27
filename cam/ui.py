# blender CAM ui.py (c) 2012 Vilem Novak
#
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
from bpy.types import UIList

from .ui_panels.buttons_panel import CAMButtonsPanel


class CAM_UL_orientations(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:

            layout.label(text=item.name, translate=False, icon_value=icon)
        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class CAM_GCODE_Panel(CAMButtonsPanel, bpy.types.Panel):
    """CAM operation g-code options panel"""

    bl_label = "CAM g-code options "
    bl_idname = "WORLD_PT_CAM_GCODE"

    COMPAT_ENGINES = {"BLENDERCAM_RENDER"}

    def draw(self, context):
        layout = self.layout
        scene = bpy.context.scene
        if len(scene.cam_operations) == 0:
            layout.label(text="Add operation first")
        if len(scene.cam_operations) > 0:
            ao = scene.cam_operations[scene.cam_active_operation]
            if ao.valid:
                layout.prop(ao, "output_header")

                if ao.output_header:
                    layout.prop(ao, "gcode_header")
                layout.prop(ao, "output_trailer")
                if ao.output_trailer:
                    layout.prop(ao, "gcode_trailer")
                layout.prop(ao, "enable_dust")
                if ao.enable_dust:
                    layout.prop(ao, "gcode_start_dust_cmd")
                    layout.prop(ao, "gcode_stop_dust_cmd")
                layout.prop(ao, "enable_hold")
                if ao.enable_hold:
                    layout.prop(ao, "gcode_start_hold_cmd")
                    layout.prop(ao, "gcode_stop_hold_cmd")
                layout.prop(ao, "enable_mist")
                if ao.enable_mist:
                    layout.prop(ao, "gcode_start_mist_cmd")
                    layout.prop(ao, "gcode_stop_mist_cmd")

            else:
                layout.label(text="Enable Show experimental features")
                layout.label(text="in Blender CAM Addon preferences")


class CAM_PACK_Panel(CAMButtonsPanel, bpy.types.Panel):
    """CAM material panel"""

    bl_label = "Pack curves on sheet"
    bl_idname = "WORLD_PT_CAM_PACK"

    COMPAT_ENGINES = {"BLENDERCAM_RENDER"}

    def draw(self, context):
        layout = self.layout
        scene = bpy.context.scene
        settings = scene.cam_pack
        layout.label(text="warning - algorithm is slow.")
        layout.label(text="only for curves now.")

        layout.operator("object.cam_pack_objects")
        layout.prop(settings, "sheet_fill_direction")
        layout.prop(settings, "sheet_x")
        layout.prop(settings, "sheet_y")
        layout.prop(settings, "distance")
        layout.prop(settings, "tolerance")
        layout.prop(settings, "rotate")
        if settings.rotate:
            layout.prop(settings, "rotate_angle")


class CAM_SLICE_Panel(CAMButtonsPanel, bpy.types.Panel):
    """CAM slicer panel"""

    bl_label = "Slice model to plywood sheets"
    bl_idname = "WORLD_PT_CAM_SLICE"

    COMPAT_ENGINES = {"BLENDERCAM_RENDER"}

    def draw(self, context):
        layout = self.layout
        scene = bpy.context.scene
        settings = scene.cam_slice

        layout.operator("object.cam_slice_objects")
        layout.prop(settings, "slice_distance")
        layout.prop(settings, "slice_above0")
        layout.prop(settings, "slice_3d")
        layout.prop(settings, "indexes")


# panel containing all tools


class VIEW3D_PT_tools_curvetools(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_context = "objectmode"
    bl_label = "Curve CAM Tools"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.curve_boolean")
        layout.operator("object.convex_hull")
        layout.operator("object.curve_intarsion")
        layout.operator("object.curve_overcuts")
        layout.operator("object.curve_overcuts_b")
        layout.operator("object.silhouete")
        layout.operator("object.silhouete_offset")
        layout.operator("object.curve_remove_doubles")
        layout.operator("object.mesh_get_pockets")


class VIEW3D_PT_tools_create(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_context = "objectmode"
    bl_label = "Curve CAM Creators"
    bl_option = "DEFAULT_CLOSED"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.curve_plate")
        layout.operator("object.curve_drawer")
        layout.operator("object.curve_mortise")
        layout.operator("object.curve_interlock")
        layout.operator("object.curve_puzzle")
        layout.operator("object.sine")
        layout.operator("object.lissajous")
        layout.operator("object.hypotrochoid")
        layout.operator("object.customcurve")
        layout.operator("object.curve_hatch")
        layout.operator("object.curve_gear")
        layout.operator("object.curve_flat_cone")