import bpy
scene = bpy.context.scene
cam_job = scene.cam_jobs[scene.cam_job_active_index]

cam_job.machine.post_processor = "MACH3"
cam_job.machine.working_area = (8e-1, 5.6e-1, 9e-2)
cam_job.machine.feed_rate.default = 1.5
cam_job.machine.feed_rate.min = 1e-05
cam_job.machine.feed_rate.max = 2
cam_job.machine.spindle_rpm.default = 2e4
cam_job.machine.spindle_rpm.min = 5e3
cam_job.machine.spindle_rpm.max = 2.5e4
cam_job.machine.axes = 3
