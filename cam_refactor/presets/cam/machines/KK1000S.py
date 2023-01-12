import bpy

machine = bpy.context.scene.cam_job.machine

machine.post_processor_enum = "MACH3"
machine.feed_rate.default = 1.5
machine.feed_rate.min = 1e-05
machine.feed_rate.max = 2
machine.spindle_rpm.default = 20000
machine.spindle_rpm.min = 5000
machine.spindle_rpm.max = 25000
machine.axes = 3
