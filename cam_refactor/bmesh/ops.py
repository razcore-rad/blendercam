from typing import Iterator

from bmesh.types import BMesh, BMVert


# https://blender.stackexchange.com/questions/75332/how-to-find-the-number-of-loose-parts-with-blenders-python-api
def get_islands(bm: BMesh, verts: list[BMVert] = []) -> dict[str, list[set[BMVert]]]:
    def tag(vertices: list[BMVert], is_tagged: bool) -> None:
        for vertex in vertices:
            vertex.tag = is_tagged

    def walk_island(vert: BMVert) -> Iterator[BMVert]:
        vert.tag = True
        yield vert
        link_verts = (ov for e in vert.link_edges if not (ov := e.other_vert(vert)).tag)
        for link_vert in link_verts:
            if link_vert.tag:
                continue
            yield from walk_island(link_vert)

    result = {"islands": []}
    tag(bm.verts, True)
    tag(verts, False)
    verts = set(verts)
    while verts:
        vert = verts.pop()
        verts.add(vert)
        island = set(walk_island(vert))
        result["islands"].append(island)
        tag(island, False)
        verts -= island
    return result
