import importlib

import bpy

modnames = ["camjob", "utils"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f".{modname}", __package__)) for modname in modnames}
)

CLASSES = [
    camjob.operation.cutter.ConeMill,
    camjob.operation.cutter.Mill,
    camjob.operation.cutter.Drill,
    camjob.operation.cutter.Simple,
    camjob.operation.feedmovementspindle.Feed,
    camjob.operation.feedmovementspindle.Movement,
    camjob.operation.feedmovementspindle.Spindle,
    camjob.operation.workarea.WorkArea,
    camjob.operation.strategy.BlockStrategy,
    camjob.operation.strategy.CarveProjectStrategy,
    camjob.operation.strategy.CirclesStrategy,
    camjob.operation.strategy.CrossStrategy,
    camjob.operation.strategy.CurveToPathStrategy,
    camjob.operation.strategy.DrillStrategy,
    camjob.operation.strategy.MedialAxisStrategy,
    camjob.operation.strategy.OutlineFillStrategy,
    camjob.operation.strategy.PocketStrategy,
    camjob.operation.strategy.ProfileStrategy,
    camjob.operation.strategy.ParallelStrategy,
    camjob.operation.strategy.SpiralStrategy,
    camjob.operation.strategy.WaterlineRoughingStrategy,
    camjob.operation.Operation,
    camjob.machine.feedrate.FeedRate,
    camjob.machine.spindlerpm.SpindleRPM,
    camjob.machine.postprocessor.customlocations.CustomLocations,
    camjob.machine.postprocessor.PostProcessor,
    camjob.machine.postprocessor.LinuxCNCPostProcessor,
    camjob.machine.Machine,
    camjob.stock.Stock,
    camjob.CAMJob,
]


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cam_jobs = bpy.props.CollectionProperty(type=camjob.CAMJob)
    bpy.types.Scene.cam_job_active_index = bpy.props.IntProperty(default=0, min=0)


def unregister() -> None:
    del bpy.types.Scene.cam_jobs
    del bpy.types.Scene.cam_job_active_index
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
