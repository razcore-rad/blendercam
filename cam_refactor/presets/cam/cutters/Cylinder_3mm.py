import bpy

scene = bpy.context.scene
cam_job = scene.cam_jobs[scene.cam_job_active_index]

cam_job.operation.cutter_type = "CYLINDER"
cam_job.operation.cutter.id = 1
cam_job.operation.cutter.description = "Default cylinder end mill"
cam_job.operation.cutter.diameter = 3e-3
cam_job.operation.cutter.flutes = 2
cam_job.operation.cutter.length = 2.5e-1
