import bpy
from bpy.types import Scene

from . import cam_job


CLASSES = [
    cam_job.operation.cutter.ConeMill,
    cam_job.operation.cutter.Mill,
    cam_job.operation.cutter.Drill,
    cam_job.operation.cutter.Simple,
    cam_job.operation.feedmovementspindle.Feed,
    cam_job.operation.feedmovementspindle.Movement,
    cam_job.operation.feedmovementspindle.Spindle,
    cam_job.operation.workarea.WorkArea,
    cam_job.operation.strategy.Block,
    cam_job.operation.strategy.CarveProject,
    cam_job.operation.strategy.Circles,
    cam_job.operation.strategy.Cross,
    cam_job.operation.strategy.CurveToPath,
    cam_job.operation.strategy.Drill,
    cam_job.operation.strategy.MedialAxis,
    cam_job.operation.strategy.OutlineFill,
    cam_job.operation.strategy.Pocket,
    cam_job.operation.strategy.Profile,
    cam_job.operation.strategy.Parallel,
    cam_job.operation.strategy.Spiral,
    cam_job.operation.strategy.WaterlineRoughing,
    cam_job.operation.Operation,
    cam_job.machine.feedrate.FeedRate,
    cam_job.machine.spindlerpm.SpindleRPM,
    cam_job.machine.postprocessor.customlocations.CustomLocations,
    cam_job.machine.postprocessor.Base,
    cam_job.machine.postprocessor.LinuxCNC,
    cam_job.machine.Machine,
    cam_job.stock.Stock,
    cam_job.CAMJob,
]


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    Scene.cam_jobs = bpy.props.CollectionProperty(type=cam_job.CAMJob)
    Scene.cam_job_active_index = bpy.props.IntProperty(default=0, min=0)
    Scene.cam_job = property(lambda self: self.cam_jobs[self.cam_job_active_index])
    # Object.cam_is_source = property(
    #     lambda self: any(
    #         o.strategy.is_source(self)
    #         for c in bpy.context.scene.cam_jobs
    #         for o in c.operations
    #     )
    # )


def unregister() -> None:
    # del Object.cam_is_source
    del Scene.cam_job
    del Scene.cam_jobs
    del Scene.cam_job_active_index
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
