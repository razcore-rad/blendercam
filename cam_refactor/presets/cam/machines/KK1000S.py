import bpy
scene = bpy.context.scene
unit_settings = scene.unit_settings
cam_job = scene.cam_jobs[scene.cam_job_active_index]

unit_settings.system = "METRIC"
cam_job.machine.post_processor = "MACH3"
cam_job.machine.working_area = (8e-1, 5.6e-1, 9e-2)
cam_job.machine.feedrate.default = 1.5
cam_job.machine.feedrate.min = 1e-05
cam_job.machine.feedrate.max = 2
cam_job.machine.spindle.default = 2e4
cam_job.machine.spindle.min = 5e3
cam_job.machine.spindle.max = 2.5e4
cam_job.machine.axes = 3
cam_job.machine.collet_size = 0.0
