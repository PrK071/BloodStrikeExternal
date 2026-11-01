# Python | ExternalCore/python_dispatch.py | Python 3.12+ | passive, bounded attribute and enemy-predicate resolution.
"""Only corroborated dispatch paths are interpreted; target code is never called.

Unsupported descriptors, custom hooks and builtin side tables raise an explicit
layout error. Stored NumericMap data cannot bypass Python attribute precedence.
"""
from dataclasses import dataclass,replace
import struct

from .predicate import FUNCTION_TYPE,base_is_enemy_body,PredicateBody
from .python_owner import (DataReader,PythonLayoutError,STATIC_BUILTIN,MANAGED_DICT,
    TYPE_FLAGS,TYPE_DICT,TYPE_DICTOFFSET,TRUE,FALSE,NONE,STR_TYPE)
from .python_values import INT_TYPE,FLOAT_TYPE,read_scalar

GENERIC_GETATTRO=0x2A094D0
ENTITY_GETATTRO=0x1439F30
MAP_GETATTRO=0x12F94A0
GETATTR_HOOK=0x2A1DCA0
WRAPPER_DESCRIPTOR_TYPE=0x7A21E50
GETATTRIBUTE_WRAPPER_BASE=0x7A13E60


@dataclass(frozen=True,slots=True)
class Attribute:
    object: int
    name: str
    value: int | float
    source: str
    kind: str = "object"
    defining_class: int | None = None


def type_dictionary(data,cls,*,wanted=None):
    head=data.type_object(cls)
    flags=struct.unpack_from('<I',head,TYPE_FLAGS)[0]
    if flags & STATIC_BUILTIN:
        interpreter=getattr(data,'interpreter',None)
        token=data.u64(cls+0x168)
        if not interpreter or not 1<=token<=200:
            raise PythonLayoutError('builtin side-table interpreter/index is unresolved')
        index=token-1
        state=interpreter+0x2BF38+0x30*index
        if data.u64(state)!=cls:
            if index>=10:raise PythonLayoutError('builtin secondary state index is outside its array')
            state=interpreter+0x2E4C8+0x30*index
        if data.u64(state)!=cls:
            raise PythonLayoutError('builtin side-table type identity disagrees')
        readying,ready=struct.unpack('<2i',data.read(state+0xC,8))
        if readying or ready!=1:raise PythonLayoutError('builtin type dictionary is not ready')
        dictionary=data.pointer(state+0x18)
    else:dictionary=struct.unpack_from('<Q',head,TYPE_DICT)[0]
    return data.dictionary(dictionary,wanted=wanted) if dictionary else {}


def class_attribute(data: DataReader,obj,name):
    for cls in data.mro(obj):
        attributes=type_dictionary(data,cls,wanted={name})
        if name in attributes:return cls,attributes[name]
    return None,None


def instance_attributes(data: DataReader,obj):
    head=data.type_object(data.pointer(obj+8))
    flags=struct.unpack_from('<I',head,TYPE_FLAGS)[0]
    if not flags & MANAGED_DICT and not struct.unpack_from('<q',head,TYPE_DICTOFFSET)[0]:
        return {}
    return data.instance_dict(obj)


def _descriptor(data,value):
    """Return the exact builtin function role or ordinary raw descriptor slots."""
    if value in (data.module.address(TRUE),data.module.address(FALSE),data.module.address(NONE)):
        return False,False,False
    cls=data.pointer(value+8)
    if cls==data.module.address(FUNCTION_TYPE):return True,False,True
    if cls in {data.module.address(rva) for rva in (INT_TYPE,FLOAT_TYPE,STR_TYPE)}:
        return False,False,False
    head=data.type_object(cls)
    get,set_=struct.unpack_from('<2Q',head,0x110)
    return bool(get),bool(set_),False


def _generic(data,obj,name):
    cls,value=class_attribute(data,obj,name)
    has_get,is_data,function=(False,False,False) if value is None else _descriptor(data,value)
    if has_get and is_data:
        raise PythonLayoutError(f'{name}: a data descriptor requires target execution')
    stored=instance_attributes(data,obj)
    if name in stored:return Attribute(obj,name,stored[name],'instance')
    if value is not None:
        if has_get and not function:
            raise PythonLayoutError(f'{name}: unsupported non-data descriptor')
        return Attribute(obj,name,value,'class','function' if function else 'object',cls)
    return None


def effective_getter(data,obj):
    head=data.type_object(data.pointer(obj+8))
    getattro=struct.unpack_from('<Q',head,0x90)[0]
    if getattro==data.module.address(GETATTR_HOOK):
        cls,descriptor=class_attribute(data,obj,'__getattribute__')
        if descriptor is None or data.u64(descriptor+8)!=data.module.address(WRAPPER_DESCRIPTOR_TYPE):
            raise PythonLayoutError('custom __getattribute__ is unsupported')
        owner=data.pointer(descriptor+0x10)
        if (owner not in data.mro(obj) or data.ascii(data.pointer(descriptor+0x18))!='__getattribute__' or
                data.u64(descriptor+0x28)!=data.module.address(GETATTRIBUTE_WRAPPER_BASE)):
            raise PythonLayoutError('unsupported __getattribute__ wrapper identity')
        getattro=data.u64(descriptor+0x30)
    if getattro not in {data.module.address(rva) for rva in
                       (GENERIC_GETATTRO,ENTITY_GETATTRO,MAP_GETATTRO)}:
        raise PythonLayoutError('unsupported effective attribute hook')
    return getattro


def attribute(data: DataReader,obj,name) -> Attribute:
    if not isinstance(name,str) or not name.isascii() or not 1<=len(name)<=128:
        raise ValueError('attribute name must be bounded ASCII')
    getattro=effective_getter(data,obj)
    result=_generic(data,obj,name)
    if result is not None:return result
    if getattro==data.module.address(GENERIC_GETATTRO):
        raise PythonLayoutError(f'{name}: generic attribute is absent')
    from .native_properties import NumericMap,MAP_PYTYPE
    from .python_owner import ENTITY_PYTYPE
    if getattro==data.module.address(MAP_GETATTRO):
        # This entry point requires an independently validated area association.
        raise PythonLayoutError(f'{name}: standalone native map fallback needs area identity')
    if data.module.address(ENTITY_PYTYPE) not in data.mro(obj):
        raise PythonLayoutError('native entity getter on an unsupported host hierarchy')
    bridge=data.pointer(obj+0x20)
    if not data.u64(bridge+0x20):
        raise PythonLayoutError('native host alternate-object fallback is unresolved')
    area=data.pointer(bridge+0x10)
    if data.area_host(area)!=obj:
        raise PythonLayoutError('native host/area reverse identity disagrees')
    mapping=NumericMap(data,area)
    if (data.u64(bridge+0x18)!=mapping.map or
            data.u64(bridge+0x20)!=data.u64(mapping.map+0x20)):
        raise PythonLayoutError('host cached map and area property map disagree')
    if data.module.address(MAP_PYTYPE) not in data.mro(mapping.map):
        raise PythonLayoutError('unsupported cached property map')
    shadow=_generic(data,mapping.map,name)
    if shadow is not None:return shadow
    values=mapping.read({name})
    if name not in values:raise PythonLayoutError(f'{name}: native property is absent')
    entry=values[name]
    return Attribute(obj,name,entry.value,'native_numeric',entry.kind)


def integer_attribute(data,obj,name):
    result=attribute(data,obj,name)
    if result.source=='native_numeric':
        if result.kind!='int':raise PythonLayoutError(f'{name}: expected integer property')
        return result.value,result.source
    value=read_scalar(data,result.value)
    if value.kind!='int':raise PythonLayoutError(f'{name}: expected exact integer operand')
    return value.value,result.source


def passive_truth(data,obj):
    if obj in (data.module.address(FALSE),data.module.address(NONE)):return False
    if obj==data.module.address(TRUE):return True
    head=data.type_object(data.pointer(obj+8))
    for suite_offset,slot_offset in [(0x60,0x48),(0x70,0),(0x68,0)]:
        suite=struct.unpack_from('<Q',head,suite_offset)[0]
        if suite and data.u64(suite+slot_offset):
            raise PythonLayoutError('operand truth requires an unsupported bool/length callback')
    return True


@dataclass(frozen=True,slots=True)
class EnemyContext:
    space: int
    game_logic: int
    body: PredicateBody


def enemy_context(data,context):
    space=context.globals.get('space')
    if not space or space==data.module.address(NONE):raise PythonLayoutError('genv.space is absent')
    logic=attribute(data,space,'game_logic')
    if logic.kind!='object' or not logic.value or logic.value==data.module.address(NONE):
        raise PythonLayoutError('space.game_logic has no supported object value')
    method=attribute(data,logic.value,'IsEnemy')
    if method.source!='class' or method.kind!='function':
        raise PythonLayoutError('IsEnemy is not a supported bound class function')
    body=replace(base_is_enemy_body(data,method.value),active_dispatch_verified=True)
    return EnemyContext(space,logic.value,body)


@dataclass(frozen=True,slots=True)
class EnemyDecision:
    enemy: bool
    local_faction: int | None
    target_faction: int | None
    rule: str


def evaluate_base_enemy(data,context: EnemyContext,local,target):
    # Keep the order of the verified body's identity/truth/faction short circuits.
    if local==target:return EnemyDecision(False,None,None,'same_object')
    if not passive_truth(data,local) or not passive_truth(data,target):
        return EnemyDecision(False,None,None,'falsey_operand')
    left,_=integer_attribute(data,local,'faction')
    if left<0:return EnemyDecision(True,left,None,'negative_local_faction')
    right,_=integer_attribute(data,target,'faction')
    if right<0:return EnemyDecision(True,left,right,'negative_target_faction')
    return EnemyDecision(left!=right,left,right,'verified_base_faction_comparison')
