from collections import namedtuple
from functools import reduce

import bpy

from . import shaders
# from .props.camjob.operation.feedmovementspindle import update_movement_rapid_height_min


HandlerItem = namedtuple("HandlerItem", ("handler", "args", "region_type", "draw_type"))

SUFFIX = {"types": "add", "app": "append"}

HANDLERS_ADD = {
    "types.SpaceView3D.draw_handler_{}": [
        HandlerItem(shaders.draw_stock, (), "WINDOW", "POST_VIEW"),
        HandlerItem(shaders.draw_features, (), "WINDOW", "POST_VIEW"),
        # HandlerItem(update_movement_rapid_height_min, (), "WINDOW", "POST_VIEW")
    ],
}

handlers_rem = {}


def register() -> None:
    for key, handler_items in HANDLERS_ADD.items():
        *keys, last_key = key.split(".")
        func_add = getattr(reduce(getattr, keys, bpy), last_key.format(SUFFIX[keys[0]]))
        for handler_item in handler_items:
            handler = func_add(*handler_item)
            item = [
                handler_item.handler if handler is None else handler,
            ] + ([] if handler_item.region_type is None else [handler_item.region_type])
            handlers_rem.setdefault(key, []).append(item)


def unregister() -> None:
    for key, handlers in handlers_rem.items():
        *keys, last_key = key.split(".")
        func_rem = getattr(reduce(getattr, keys, bpy), last_key.format("remove"))
        for handler_item in handlers:
            func_rem(*handler_item)
    handlers_rem.clear()
