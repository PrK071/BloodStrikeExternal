# Python | ExternalCore/life_state.py | Python 3.12+ | pinned CombatState schema and passive effective state reads.
"""Source definitions and enum metaclass are pinned in state-v7/.

Runtime class constants must still match those definitions. HP is independent.
Unknown states/layouts remain unknown; no descriptor or conversion is executed.
"""
from dataclasses import dataclass

from .python_dispatch import type_dictionary,integer_attribute,class_attribute
from .python_owner import PythonLayoutError
from .python_runtime import find_module
from .python_values import read_scalar

COMBAT_STATES={'ALIVE':0,'DYING':1,'DEAD':2,'GHOST':3,'NONE':4,'SPIRIT':5}


@dataclass(frozen=True,slots=True)
class StateContext:
    interpreter: int
    module: int
    enum: int
    members: tuple[tuple[str,int],...]


@dataclass(frozen=True,slots=True)
class LifeState:
    value: int
    name: str
    alive: bool
    source: str


def state_context(data,context):
    module=find_module(data,'gshare.consts',interpreter=context.interpreter)
    enum=module.globals.get('CombatState')
    if not enum:raise PythonLayoutError('CombatState is absent from the selected interpreter')
    metatype=data.pointer(enum+8)
    data.type_object(metatype)
    if data.u64(metatype+0x90)!=data.module.address(0x2A1DB20):
        raise PythonLayoutError('CombatState metaclass has an unsupported attribute hook')
    attrs=type_dictionary(data,enum,wanted=set(COMBAT_STATES)|{'__module__'})
    if '__module__' not in attrs or data.ascii(attrs['__module__'])!='gshare.consts':
        raise PythonLayoutError('CombatState class module is unresolved')
    for name,expected in COMBAT_STATES.items():
        _,shadow=class_attribute(data,enum,name)
        if shadow is not None:
            raise PythonLayoutError(f'CombatState.{name} is shadowed by its metaclass')
        if name not in attrs:raise PythonLayoutError(f'CombatState.{name} is absent')
        scalar=read_scalar(data,attrs[name])
        if scalar.kind!='int' or scalar.value!=expected:
            raise PythonLayoutError(f'CombatState.{name} differs from the pinned integer schema')
    return StateContext(context.interpreter,module.module,enum,tuple(COMBAT_STATES.items()))


def life_state(data,context: StateContext,host):
    value,source=integer_attribute(data,host,'combat_state')
    names={number:name for name,number in context.members}
    if value not in names:raise PythonLayoutError('effective combat_state is outside the verified schema')
    return LifeState(value,names[value],value==dict(context.members)['ALIVE'],source)
