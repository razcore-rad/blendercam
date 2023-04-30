from bpy.types import Context


def update_cam_tools_library(self, context: Context) -> None:
    cam_tools_library = context.scene.cam_tools_library
    cam_tools_library.save()
