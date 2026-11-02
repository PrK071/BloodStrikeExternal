# Python / ExternalCore/skeleton.py / Python 3.12+ Windows x64 / pinned Actor pose matrices and parent indices
"""Sequential pose observation, corroborated by native GetBoneWorldTransform and GetPoseBoneParentIds."""
import math
import struct
from .memory import read_exact
from .registry import _pointer
from .screenpoint import project_screenpoint


def read_pose(reader,record):
    def pointer(address):return _pointer(struct.unpack('<Q',read_exact(reader,address,8))[0],'skeleton')
    if pointer(record.component+0xE8)!=record.actor:
        raise ValueError('SkeletonComponent and actor aliases disagree')
    resource=pointer(record.actor+0xD8)
    bounds=read_exact(reader,resource+0x10,16)
    begin,end=struct.unpack('<2Q',bounds)
    _pointer(begin,'pose vector')
    if end<begin or (end-begin)%0xA0 or not 2<=(end-begin)//0xA0<=2048:
        raise ValueError('unsupported pose vector bounds')
    raw=read_exact(reader,begin,end-begin)
    count=len(raw)//0xA0
    points=[];parents=[]
    for offset in range(0,len(raw),0xA0):
        matrix=struct.unpack_from('<12f',raw,offset+0x30)
        parent=struct.unpack_from('<h',raw,offset+0x94)[0]
        if (not all(math.isfinite(value) for value in matrix) or
            any(abs(value)>20 for value in matrix[9:]) or not -1<=parent<count):
            raise ValueError('invalid pose matrix or parent')
        points.append(matrix[9:12]);parents.append(parent)
    for index in range(count):
        current=index;seen=set()
        while current!=-1:
            if current in seen:raise ValueError('cyclic bone hierarchy')
            seen.add(current);current=parents[current]
    if (read_exact(reader,resource+0x10,16)!=bounds or pointer(record.actor+0xD8)!=resource or
        pointer(record.component+0xE8)!=record.actor):
        raise ValueError('pose ownership or vector changed during read')
    return tuple(points),tuple(parents)


def skeleton_commands(reader,record,camera):
    points,parents=read_pose(reader,record)
    transform=record.position.transform
    origin=record.position.local_translation
    projected=[]
    for point in points:
        world=tuple(origin[axis]+sum(point[index]*transform[index*3+axis] for index in range(3))
                    for axis in range(3))
        projected.append(project_screenpoint(camera,world))
    commands=[]
    for index,parent in enumerate(parents):
        if parent<0:continue
        length=math.dist(points[index],points[parent])
        if not 0.015<=length<=1.5:continue
        left,right=projected[parent],projected[index]
        if not left.in_front or not right.in_front:continue
        coordinates=(left.x,left.y,right.x,right.y)
        if any(abs(value)>32760 for value in coordinates):continue
        commands.append(dict(kind='line',x1=round(left.x),y1=round(left.y),
            x2=round(right.x),y2=round(right.y),color=[80,240,220],width=1))
    return tuple(commands)
