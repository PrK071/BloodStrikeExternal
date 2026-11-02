# Python | ExternalCore/python_runtime.py | Python 3.12+ | pinned interpreter/module data route, no target calls.
"""Offsets are corroborated by the image's xdebugpy table and native getters."""
from dataclasses import dataclass
import struct

from .python_owner import DataReader, PythonLayoutError, NONE, ENTITY_PYTYPE

RUNTIME_RVA = 0x925F000
HEAD_RVA = 0x925F328
INTERP_NEXT = 0x1C68
INTERP_ID = 0x1C70
INTERP_MODULES = 0x1DE8
MODULE_TYPE = 0x7A1B1F0


@dataclass(frozen=True, slots=True)
class ModuleContext:
    interpreter: int
    interpreter_id: int
    module: int
    globals: dict[str,int]


def find_module(data: DataReader, name: str, *, interpreter=None, wanted=None) -> ModuleContext:
    cookie,version,free = struct.unpack("<8sQQ",data.read(data.module.address(RUNTIME_RVA,24),24))
    if cookie != b"xdebugpy" or version != 0x030E00F0 or free:
        raise PythonLayoutError("runtime debug cookie/version/GIL layout mismatch")
    current = data.u64(data.module.address(HEAD_RVA,8))
    seen,matches = set(),[]
    while current:
        if current in seen or len(seen)>=64:
            raise PythonLayoutError("interpreter cycle or traversal budget exceeded")
        seen.add(current)
        interpreter_id, = struct.unpack("<q",data.read(current+INTERP_ID,8))
        if interpreter_id<0:
            raise PythonLayoutError("uninitialized interpreter identity")
        modules = data.u64(current+INTERP_MODULES)
        if modules and (interpreter is None or current==interpreter):
            module = data.dictionary(modules,wanted={name},max_entries=16384).get(name)
            if module:
                if data.u64(module+8) != data.module.address(MODULE_TYPE):
                    raise PythonLayoutError("module entry has an unsupported type")
                values = data.dictionary(data.pointer(module+0x10),wanted=None if wanted is None else set(wanted)|{'__name__'})
                module_name = values.get("__name__")
                if not module_name or data.ascii(module_name) != name:
                    raise PythonLayoutError("module key/name mismatch")
                matches.append(ModuleContext(current,interpreter_id,module,values))
        current = data.u64(current+INTERP_NEXT)
    if len(matches)!=1:
        raise PythonLayoutError(f"expected one interpreter/module context, found {len(matches)}")
    return matches[0]


def local_player(data: DataReader):
    def builtin_context():
        builtins = find_module(data,'builtins',wanted={'genv'})
        environment = builtins.globals.get('genv')
        if not environment:
            raise PythonLayoutError('builtins.genv is absent')
        name = data.c_string(struct.unpack_from('<Q',data.type_object(data.pointer(environment+8)),24)[0])
        if name.rsplit('.',1)[-1] != 'ClientEnv':
            raise PythonLayoutError('builtins.genv is not ClientEnv')
        return ModuleContext(builtins.interpreter,builtins.interpreter_id,
                             environment,data.instance_dict(environment,wanted={'player','main_player','replay_player','space'}))
    def legacy_context():
        return find_module(data,'gclient.genv',wanted={'player','main_player','replay_player','space'})
    primary,secondary=(builtin_context,legacy_context) if data.live_lookup else (legacy_context,builtin_context)
    try:
        context=primary()
    except PythonLayoutError as exc:
        if str(exc) != 'expected one interpreter/module context, found 0':
            raise
        context=secondary()
    player = context.globals.get("player")
    if not player or player == data.module.address(NONE):
        raise PythonLayoutError("genv.player is absent or None")
    main = context.globals.get("main_player")
    if main is not None and main != player:
        raise PythonLayoutError("genv.player/main_player disagree")
    replay = context.globals.get("replay_player")
    if replay and replay not in (player,data.module.address(NONE)):
        raise PythonLayoutError("separate replay-player context is unresolved")
    if data.module.address(ENTITY_PYTYPE) not in data.mro(player):
        raise PythonLayoutError("genv.player is not an Asio entity host")
    bridge = data.pointer(player+0x20)
    area = data.pointer(bridge+0x10)
    if data.area_host(area) != player:
        raise PythonLayoutError("local player/area identity disagrees")
    data.interpreter=context.interpreter
    return context,player,area
