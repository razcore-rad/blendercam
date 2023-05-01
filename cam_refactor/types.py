from collections import namedtuple

from bmesh.types import BMVert


ComputeResult = namedtuple(
    "ComputeResult", ("execute", "computed"), defaults=(set(), [])
)

ShortEnumItems = list[tuple[str, str, str]]
MediumEnumItems = list[tuple[str, str, str, int]]

IslandsResult = dict[str, list[set[BMVert]]]
