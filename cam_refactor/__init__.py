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

from . import ops, props, ui

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


classes = [
    props.CAMJob.Operation.WorkArea,
    props.CAMJob.Operation.BlockStrategy,
    props.CAMJob.Operation.CarveProjectStrategy,
    props.CAMJob.Operation.CirclesStrategy,
    props.CAMJob.Operation.CrossStrategy,
    props.CAMJob.Operation.CurveToPathStrategy,
    props.CAMJob.Operation.DrillStrategy,
    props.CAMJob.Operation.MedialAxisStrategy,
    props.CAMJob.Operation.OutlineFillStrategy,
    props.CAMJob.Operation.PocketStrategy,
    props.CAMJob.Operation.ProfileStrategy,
    props.CAMJob.Operation.ParallelStrategy,
    props.CAMJob.Operation.SpiralStrategy,
    props.CAMJob.Operation.WaterlineRoughingStrategy,
    props.CAMJob.Operation,
    props.CAMJob.PostProcessor,
    props.CAMJob,
    ops.CAM_OT_Action,
    ui.CAM_UL_List,
    ui.CAM_PT_PanelJobs,
    ui.CAM_PT_PanelJobsOperations,
    ui.CAM_PT_PanelJobsOperationWorkArea,
    ui.CAM_PT_PanelJobStock,
    ui.CAM_PT_PanelJobMovement,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cam_jobs = bpy.props.CollectionProperty(type=props.CAMJob)
    bpy.types.Scene.cam_job_active_index = bpy.props.IntProperty(default=0, min=0)


def unregister():
    del bpy.types.Scene.cam_jobs
    del bpy.types.Scene.cam_job_active_index
    for c in classes:
        bpy.utils.unregister_class(c)
