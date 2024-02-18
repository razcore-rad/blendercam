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

from . import ops, props, ui, handlers
from .utils import ADDON_PATH


mods = [ops, props, ui, handlers]

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
    # FIXME: more roboust solution with account for v3.11
    requirements_path = ADDON_PATH / "requirements.txt"
    try:
        with open(requirements_path) as r:
            for line in r.readlines():
                if (m := re.match(r"^\w*", line)) is not None:
                    importlib.import_module(m.group(0))
    except ModuleNotFoundError:
        ensurepip.bootstrap(upgrade=True, user=True)
        out = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                "--update",
                "-r",
                requirements_path,
            ]
        )
        print(out)
    except IndexError:
        pass


def register() -> None:
    ensure_modules()
    for mod in mods:
        mod.register()


def unregister() -> None:
    for mod in reversed(mods):
        mod.unregister()

    for mod in sorted(filter(lambda m: m.startswith(__name__), sys.modules)):
        del sys.modules[mod]
