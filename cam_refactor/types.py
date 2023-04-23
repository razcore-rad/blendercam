from collections import namedtuple

from bmesh.types import BMVert


ComputeResult = namedtuple(
    "ComputeResult", ("execute", "msg", "computed"), defaults=(set(), "", [])
)

ShortEnumItems = list[tuple[str, str, str]]

IslandsResult = dict[str, list[set[BMVert]]]
