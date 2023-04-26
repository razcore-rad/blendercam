import bpy
from bpy.types import Scene
from bpy.props import CollectionProperty, IntProperty, PointerProperty

from . import camjob, camtool


CLASSES = [
    camjob.operation.cutter.CylinderCutter,
    camjob.operation.cutter.BallCutter,
    camjob.operation.cutter.BullCutter,
    camjob.operation.cutter.ConeCutter,
    camjob.operation.cutter.CylinderConeCutter,
    camjob.operation.cutter.BallConeCutter,
    camjob.operation.cutter.BullConeCutter,
    camjob.operation.cutter.ConeConeCutter,
    camjob.operation.cutter.SimpleCutter,
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
    # camjob.machine.feedrate.FeedRate,
    # camjob.machine.spindlerpm.SpindleRPM,
    # camjob.machine.postprocessor.custompositions.CustomPositions,
    camjob.machine.postprocessor.Base,
    camjob.machine.postprocessor.LinuxCNC,
    camjob.machine.Machine,
    camjob.stock.Stock,
    camjob.CAMJob,
    camtool.CAMTool,
    camtool.CAMToolsLibrary,
]


def register() -> None:
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass
    Scene.cam_jobs = CollectionProperty(type=camjob.CAMJob)
    Scene.cam_job_active_index = IntProperty(default=0, min=0)
    Scene.cam_job = property(lambda self: self.cam_jobs[self.cam_job_active_index])
    Scene.cam_tools_library = PointerProperty(type=camtool.CAMToolsLibrary)


def unregister() -> None:
    del Scene.cam_tools_library
    del Scene.cam_job
    del Scene.cam_job_active_index
    del Scene.cam_jobs
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
