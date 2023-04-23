import bpy
from bpy.types import Scene

from . import camjob


CLASSES = [
    camjob.operation.cutter.ConeMill,
    camjob.operation.cutter.Mill,
    camjob.operation.cutter.Drill,
    camjob.operation.cutter.Simple,
    camjob.operation.feedmovementspindle.Feed,
    camjob.operation.feedmovementspindle.Movement,
    camjob.operation.feedmovementspindle.Spindle,
    camjob.operation.workarea.WorkArea,
    camjob.operation.strategy.Block,
    camjob.operation.strategy.CarveProject,
    camjob.operation.strategy.Circles,
    camjob.operation.strategy.Cross,
    camjob.operation.strategy.CurveToPath,
    camjob.operation.strategy.Drill,
    camjob.operation.strategy.MedialAxis,
    camjob.operation.strategy.OutlineFill,
    camjob.operation.strategy.Pocket,
    camjob.operation.strategy.Profile,
    camjob.operation.strategy.Parallel,
    camjob.operation.strategy.Spiral,
    camjob.operation.strategy.WaterlineRoughing,
    camjob.operation.Operation,
    camjob.machine.feedrate.FeedRate,
    camjob.machine.spindlerpm.SpindleRPM,
    camjob.machine.postprocessor.custompositions.CustomPositions,
    camjob.machine.postprocessor.Base,
    camjob.machine.postprocessor.LinuxCNC,
    camjob.machine.Machine,
    camjob.stock.Stock,
    camjob.CAMJob,
]


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    Scene.cam_jobs = bpy.props.CollectionProperty(type=camjob.CAMJob)
    Scene.cam_job_active_index = bpy.props.IntProperty(default=0, min=0)
    Scene.cam_job = property(lambda self: self.cam_jobs[self.cam_job_active_index])


def unregister() -> None:
    del Scene.cam_job
    del Scene.cam_jobs
    del Scene.cam_job_active_index
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
