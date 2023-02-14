# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

import ensurepip
import importlib
import re
import subprocess
import sys
from pathlib import Path

import bpy

mods = {".handlers", ".ops", ".props", ".ui"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})

bl_info = {
    "name": "CNC G-Code Tools",
    "author": "Răzvan C. Rădulescu (razcore-rad)",
    "version": (0, 0, 1),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar > CAM",
    "description": "Generate machining paths for CNC",
    "warning": "There is no warranty for the produced G-code",
    "wiki_url": "https://github.com/razcore-rad/blendercam/wiki",
    "tracker_url": "https://github.com/razcore-rad/blendercam/issues",
    "category": "CAM",
}


def ensure_modules() -> None:
    addons_path = Path(bpy.utils.script_path_user()) / "addons"
    requirements_path = addons_path / "cam_refactor" / "requirements.txt"
    try:
        with open(requirements_path) as r:
            for line in r.readlines():
                importlib.import_module(re.match(r"^\w*", line).group(0))
    except ModuleNotFoundError:
        ensurepip.bootstrap(upgrade=True, user=True)
        print(subprocess.check_output(
            [sys.executable, "-m", "pip", "install", "--user", "--update", "-r", requirements_path]
        ))
    except IndexError:
        pass


def register() -> None:
    ensure_modules()
    for mod in mods:
        globals()[mod.lstrip(".")].register()


def unregister() -> None:
    for mod in mods:
        globals()[mod.lstrip(".")].unregister()
