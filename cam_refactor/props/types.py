from collections import namedtuple


ComputeResult = namedtuple(
    "ComputeResult", ("execute", "msg", "vectors"), defaults=(set(), "", [])
)

ShortEnumItems = list[tuple[str, str, str]]
