# Python | ExternalCore/native_properties.py | Python 3.12+ | named Asio numeric properties, fixed sample.
"""Walk the demonstrated name index and typed storage; never call a getter.

No property index is hardcoded. Names map to descriptors in this observation.
Unsupported tags/types remain unknown. Numeric data alone does not define life,
teams, damageability or an authoritative opponent predicate.
"""
from dataclasses import dataclass
import math
import struct

from .python_owner import DataReader, PythonLayoutError, AREA_PYTYPE
from .registry import _pointer

MAP_PYTYPE=0x796A420
STORAGE_INT=0x555BA60
STORAGE_FLOAT=0x555BB58
STORAGE_MIXED=0x555BD48


@dataclass(frozen=True, slots=True)
class NumericProperty:
    name: str
    kind: str
    value: int | float
    descriptor: int
    index: int
    storage: int


class NumericMap:
    def __init__(self,data: DataReader,area):
        self.data=data
        if data.module.address(AREA_PYTYPE) not in data.mro(area):
            raise PythonLayoutError("numeric-property owner is not a native area")
        native=data.pointer(data.pointer(area+0x20))
        self.map=data.pointer(native+0x1D8)
        if data.module.address(MAP_PYTYPE) not in data.mro(self.map):
            raise PythonLayoutError("property object is not an Asio area_map")
        self.state=data.pointer(data.pointer(self.map+0x20)+0x10)
        meta=data.pointer(self.state)
        self.name_index=data.pointer(meta+0x20)
        self.schema=data.pointer(meta+0x28)
        self.storage=data.pointer(self.state+0x18)
        kind=data.u64(self.storage)
        cases={data.module.address(STORAGE_INT):("int",8),data.module.address(STORAGE_FLOAT):("float",8),
               data.module.address(STORAGE_MIXED):("mixed",16)}
        if kind not in cases:raise PythonLayoutError("unsupported numeric storage type")
        self.kind,self.stride=cases[kind]
        if data.u64(self.storage+8)!=self.state or data.u64(self.storage+0x10)!=self.schema:
            raise PythonLayoutError("numeric storage backlinks disagree")
        self.count=data.u64(self.schema+0x10)
        self.begin,self.end,self.capacity=struct.unpack("<3Q",data.read(self.storage+0x18,24))
        if self.count>65536 or not self.begin<=self.end<=self.capacity or self.begin%8 or self.end%8 or self.capacity%8:
            raise PythonLayoutError("invalid or excessive numeric storage bounds")
        if self.end-self.begin!=self.count*self.stride or (self.count and not self.begin):
            raise PythonLayoutError("numeric schema and vector lengths disagree")
        if self.count:_pointer(self.begin,"numeric values")
        first,last=struct.unpack("<2Q",data.read(self.schema+0x40,16))
        if first>last or first%8 or last%8 or (last-first)%16 or (last-first)//16>16384:
            raise PythonLayoutError("invalid/excessive schema definition vector")
        pairs=data.read(first,last-first) if last>first else b""
        self.members={struct.unpack_from("<Q",pairs,i+8)[0] for i in range(0,len(pairs),16)}
        for member in self.members:_pointer(member,"numeric descriptor")

    def descriptors(self,names):
        data=self.data
        sentinel=data.pointer(self.name_index+0x18)
        buckets=data.pointer(self.name_index+0x28)
        mask=data.u64(self.name_index+0x40)
        if mask>=65536 or (mask+1)&mask:
            raise PythonLayoutError("invalid/excessive descriptor bucket mask")
        raw=data.read(buckets,16*(mask+1))
        result,seen={},set()
        for index in range(mask+1):
            first,last=struct.unpack_from("<2Q",raw,index*16)
            if last==sentinel:
                if first!=sentinel:raise PythonLayoutError("inconsistent empty property bucket")
                continue
            current=last
            while True:
                _pointer(current,"descriptor node")
                if current==sentinel or current in seen or len(seen)>=16384:
                    raise PythonLayoutError("descriptor cycle/duplicate or traversal limit")
                seen.add(current)
                previous,key,descriptor=struct.unpack("<3Q",data.read(current+8,24))
                try:name=data.ascii(key)
                except PythonLayoutError:name=None
                if name in names:
                    if name in result:raise PythonLayoutError("duplicate property name")
                    result[name]=descriptor
                if current==first:break
                current=previous
        return result

    def read(self,names):
        result={}
        for name,descriptor in self.descriptors(frozenset(names)).items():
            if descriptor not in self.members:
                raise PythonLayoutError("property descriptor is outside this numeric schema")
            index,=struct.unpack("<i",self.data.read(descriptor,4))
            if not 0<=index<self.count:
                raise PythonLayoutError("property index is outside the numeric vector")
            address=self.begin+index*self.stride
            payload=self.data.read(address,self.stride)
            kind=self.kind
            if kind=="mixed":
                tag=payload[8]
                if tag not in (0,1):raise PythonLayoutError("unsupported mixed numeric tag")
                kind="int" if tag==0 else "float"
            value,=struct.unpack_from("<q" if kind=="int" else "<d",payload)
            if kind=="float" and not math.isfinite(value):
                raise PythonLayoutError("nonfinite native property")
            result[name]=NumericProperty(name,kind,value,descriptor,index,self.storage)
        return result
