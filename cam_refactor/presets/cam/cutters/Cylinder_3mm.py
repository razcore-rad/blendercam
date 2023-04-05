import bpy


operation = bpy.context.scene.cam_job.operation

operation.cutter_type = "CYLINDER"
operation.cutter.id = 1
operation.cutter.description = "Default cylinder end mill"
operation.cutter.diameter = 3e-3
operation.cutter.flutes = 2
operation.cutter.length = 2.5e-1
