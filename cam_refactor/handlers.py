import importlib
from collections import namedtuple
from functools import reduce

import bpy

mods = {".shaders"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})


HandlerItem = namedtuple("HandlerItem", ("handler", "args", "region_type", "draw_type"), defaults=3 * (None,))


HANDLERS_ADD = {
    "types.SpaceView3D.draw_handler_{}": [
        HandlerItem(shaders.draw_stock, (), "WINDOW", "POST_VIEW"),
    ],
}

handlers_rem = {}


def register() -> None:
    suffix = {"types": "add", "app": "append"}
    for key, handlers in HANDLERS_ADD.items():
        *keys, last_key = key.split(".")
        func_add = getattr(reduce(getattr, keys, bpy), last_key.format(suffix[keys[0]]))
        for handler_item in handlers:
            handlers_rem.setdefault(key, []).append(
                [handler if (handler := func_add(*handler_item)) is not None else handler_item.func]
                + [handler_item.region_type if handler_item.region_type is not None else []]
            )


def unregister() -> None:
    for key, handlers in handlers_rem.items():
        *keys, last_key = key.split(".")
        func_rem = getattr(reduce(getattr, keys, bpy), last_key.format("remove"))
        for handler_item in handlers:
            func_rem(*handler_item)
    handlers_rem.clear()
