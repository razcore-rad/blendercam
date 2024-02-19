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

import importlib
import re
import subprocess
import sys

from .utils import ADDON_PATH


mods = []

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
    requirements_path = str(ADDON_PATH / "requirements.txt")
    dependencies_path = ADDON_PATH / "dependencies"
    site_path = (
        dependencies_path
        / "lib"
        / "python{major}.{minor}".format(major=sys.version_info.major, minor=sys.version_info.minor)
        / "site-packages"
    )
    sys.path.insert(0, str(site_path))

    try:
        import_dependencies(requirements_path)
    except ModuleNotFoundError:
        exec = [sys.executable, "-m", "pip", "--no-input", "--disable-pip-version-check"]
        exec += ["install", "--prefix", str(dependencies_path), "--upgrade", "--requirement", requirements_path]
        out = [
            "",
            "{name}::ensure_modules()".format(**bl_info),
            *subprocess.check_output(exec).decode("utf8").splitlines(),
            "",
        ]
        print("\n".join(out))
        importlib.invalidate_caches()

    from . import ops, props, ui, handlers

    mods.extend([ops, props, ui, handlers])


def import_dependencies(requirements_path: str) -> None:
    with open(requirements_path) as r:
        for line in r.readlines():
            if (m := re.match(r"^\w*", line)) is not None:
                importlib.import_module(m.group(0))


def register() -> None:
    ensure_modules()
    for mod in mods:
        mod.register()


def unregister() -> None:
    for mod in reversed(mods):
        mod.unregister()

    for mod in sorted(filter(lambda m: m.startswith(__name__), sys.modules)):
        del sys.modules[mod]
