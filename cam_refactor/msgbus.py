import bpy

from bpy.types import PropertyGroup
from bpy.app.handlers import persistent


def on_cam_job_update_name(cam_job: PropertyGroup) -> None:
    cam_job.object.name = cam_job.data.name


@persistent
def on_load_post(file_path: str) -> None:
    for cam_job in bpy.context.scene.cam_jobs:
        bpy.msgbus.subscribe_rna(
            key=cam_job.data.path_resolve("name", False),
            owner=cam_job,
            args=(cam_job,),
            notify=on_cam_job_update_name,
        )
