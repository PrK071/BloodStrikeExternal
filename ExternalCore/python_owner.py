# Python | ExternalCore/python_owner.py | Python 3.12+ | bounded CPython 3.14 data inspection, pinned BloodStrike PE.
"""Read existing data only: no Py API, descriptors, properties or target calls.

Evidence: python-owner-v5/, gameplay-classifier-v5/ and the V6 integration files.
A positive observation links the primary stored model to a native area and host;
it does not establish opponent/life/visibility semantics or live-game success.
Supported managed/split instance storage uses the corroborated CPython 3.14 ABI.
Builtin side-table attributes and custom dispatch remain unresolved. Reading a
stored class/instance attribute never invokes a descriptor or target code.
"""
import struct

from .memory import MemoryReadError, read_exact, PageSnapshotReader
from .registry import _pointer
from .scene import Category, Classification, PlayerFacts, StateFact, observation_id

DICT_TYPE = 0x7A19900
STR_TYPE = 0x7A16E10
TUPLE_TYPE = 0x7A18CE0
TYPE_TYPE = 0x7A15170
TRUE = 0x7A129B0
FALSE = 0x7A12990
IENTITY_PYTYPE = 0x79A0060
AREA_PYTYPE = 0x796C240
ENTITY_PYTYPE = 0x796F3C0
NONE = 0x7A0A150  # Native area.owner() fallback, RVA130a230.
TYPE_DICT = 0x108
TYPE_MRO = 0x158
TYPE_DICTOFFSET = 0x120
TYPE_FLAGS = 0xA8
STATIC_BUILTIN = 2
MANAGED_DICT = 16
MAX_DICT_ENTRIES = 4096


class PythonLayoutError(ValueError):
    pass


class DataReader:
    """A bounded read cache scoped to one pass; a second pass is independent."""
    def __init__(self, reader, module, *, max_bytes=8*1024*1024, max_reads=80000):
        self.reader = PageSnapshotReader(reader) if getattr(reader,"page_size",None)==4096 else reader
        self.module = module
        self.max_bytes, self.max_reads = max_bytes, max_reads
        self.bytes_read, self.cache = 0, {}
        self.trace = []

    def read(self, address, size, *, mask_ranges=()):
        key = (address, size, mask_ranges)
        if key in self.cache:
            return self.cache[key]
        if self.bytes_read + size > self.max_bytes or len(self.trace) >= self.max_reads:
            raise PythonLayoutError("Python metadata read budget exhausted")
        raw = read_exact(self.reader, address, size)
        self.bytes_read += size
        self.cache[key] = raw
        compared = bytearray(raw)
        for start,end in mask_ranges:
            compared[start:end] = bytes(end-start)
        self.trace.append((address, bytes(compared)))
        return raw

    def u64(self, address):
        return struct.unpack("<Q", self.read(address, 8))[0]

    def pointer(self, address):
        return _pointer(self.u64(address), "Python metadata")

    def c_string(self, address, *, max_length=512):
        if type(address) is not int or not 0x10000 <= address <= 0x7FFFFFFFFFFF:
            raise PythonLayoutError("invalid type-name address")
        raw = bytearray()
        for offset in range(max_length+1):
            value = self.read(address+offset, 1)[0]
            if not value:
                return raw.decode("ascii")
            if value > 127:
                raise PythonLayoutError("non-ASCII type name is unsupported")
            raw.append(value)
        raise PythonLayoutError("type name exceeds budget")

    def ascii(self, obj, *, max_length=512):
        _pointer(obj, "Unicode")
        head = self.read(obj, 40, mask_ranges=((0,8),(24,32)))  # refcount and cached string hash
        if struct.unpack_from("<Q", head, 8)[0] != self.module.address(STR_TYPE):
            raise PythonLayoutError("not an exact pinned Unicode object")
        length, = struct.unpack_from("<q", head, 16)
        state, = struct.unpack_from("<I", head, 32)
        if not 0 <= length <= max_length or state & 0x60 != 0x60 or (state >> 2) & 7 != 1:
            raise PythonLayoutError("unsupported Unicode representation or length")
        raw = self.read(obj + 40, length + 1)
        if raw[-1] or any(value > 127 for value in raw[:-1]):
            raise PythonLayoutError("invalid compact ASCII data")
        return raw[:-1].decode("ascii")

    def dictionary(self, obj, *, wanted=None, max_entries=MAX_DICT_ENTRIES):
        if type(max_entries) is not int or not 1 <= max_entries <= 65536:
            raise ValueError("invalid dictionary entry budget")
        if wanted is not None:
            wanted = frozenset(wanted)
            if any(not isinstance(k,str) or not k.isascii() or len(k)>512 for k in wanted):
                raise ValueError("requested dictionary names must be bounded ASCII")
            wanted_lengths = {len(k) for k in wanted}
        _pointer(obj, "dict")
        head = self.read(obj, 48, mask_ranges=((0,8),))
        if struct.unpack_from("<Q", head, 8)[0] != self.module.address(DICT_TYPE):
            raise PythonLayoutError("not an exact pinned dict")
        used, = struct.unpack_from("<q", head, 16)
        keys, values = struct.unpack_from("<2Q", head, 32)
        _pointer(keys, "dict keys")
        if values:
            raise PythonLayoutError("split dict values are unsupported")
        key_head = self.read(keys, 32)
        log_size, log_bytes, kind = key_head[8:11]
        usable, count = struct.unpack_from("<2q", key_head, 16)
        if not 0 <= log_size <= 20 or not log_size <= log_bytes <= 20 or kind not in (0,1):
            raise PythonLayoutError("unsupported dict key table")
        capacity = ((1 << log_size) * 2) // 3
        if not 0 <= used <= count <= min(max_entries, capacity) or usable < 0 or count+usable > capacity:
            raise PythonLayoutError("invalid/excessive dict counts")
        stride, key_offset, value_offset = (24,8,16) if kind == 0 else (16,0,8)
        index_width = (1 << log_bytes) // (1 << log_size)
        if index_width not in (1,2,4,8):
            raise PythonLayoutError("unsupported dict index width")
        indices = self.read(keys+32, 1 << log_bytes)
        index_format = {1:"b",2:"h",4:"i",8:"q"}[index_width]
        referenced = []
        for (index,) in struct.iter_unpack("<"+index_format, indices):
            if index in (-1,-2):
                continue
            if not 0 <= index < count:
                raise PythonLayoutError("dict index is outside its entry array")
            referenced.append(index)
        if len(set(referenced)) != used or len(referenced) != used:
            raise PythonLayoutError("dict index/live count mismatch")
        entries = self.read(keys + 32 + (1 << log_bytes), count * stride)
        result, live = {}, set()
        for index in range(count):
            key, = struct.unpack_from("<Q", entries, index*stride+key_offset)
            value, = struct.unpack_from("<Q", entries, index*stride+value_offset)
            if not key or not value:
                continue
            live.add(index)
            # General dictionaries may legitimately contain non-string keys.
            if self.u64(key+8) != self.module.address(STR_TYPE):
                if kind == 1:
                    raise PythonLayoutError("non-Unicode key in a Unicode table")
                continue
            if wanted is not None and struct.unpack("<q",self.read(key+16,8))[0] not in wanted_lengths:
                continue
            try:
                name = self.ascii(key)
            except PythonLayoutError:
                continue  # Non-ASCII/long names cannot match the supported keys.
            if wanted is not None and name not in wanted:
                continue
            if name in result:
                raise PythonLayoutError("duplicate named dict entry")
            result[name] = value
        if live != set(referenced):
            raise PythonLayoutError("dict live count changed or is inconsistent")
        return result

    def tuple_items(self, obj):
        head = self.read(_pointer(obj, "MRO tuple"), 32, mask_ranges=((0,8),(24,32)))
        if struct.unpack_from("<Q", head, 8)[0] != self.module.address(TUPLE_TYPE):
            raise PythonLayoutError("MRO is not an exact pinned tuple")
        count, = struct.unpack_from("<q", head, 16)
        if not 1 <= count <= 64:
            raise PythonLayoutError("invalid/excessive MRO size")
        # Python 3.14 cached hash occupies +18; item array begins at +20.
        items = struct.unpack(f"<{count}Q", self.read(obj+32, count*8))
        if len(set(items)) != count:
            raise PythonLayoutError("duplicate MRO entries")
        for item in items: _pointer(item, "MRO class")
        return items

    def type_object(self, address, *, depth=0):
        _pointer(address, "type")
        if depth > 2:
            raise PythonLayoutError("unsupported metaclass recursion")
        head = self.read(address, TYPE_MRO+8, mask_ranges=((0,8),))
        metaclass, = struct.unpack_from("<Q", head, 8)
        if metaclass != self.module.address(TYPE_TYPE):
            meta = self.type_object(metaclass, depth=depth+1)
            mro = self.tuple_items(struct.unpack_from("<Q", meta, TYPE_MRO)[0])
            if self.module.address(TYPE_TYPE) not in mro:
                raise PythonLayoutError("metaclass is not derived from the pinned type")
        return head

    def mro(self, obj):
        cls = self.pointer(obj+8)
        head = self.type_object(cls)
        items = self.tuple_items(struct.unpack_from("<Q", head, TYPE_MRO)[0])
        if items[0] != cls:
            raise PythonLayoutError("MRO does not start with the object's type")
        return items

    def class_dict(self, cls):
        head = self.type_object(cls)
        flags, = struct.unpack_from("<I", head, TYPE_FLAGS)  # unsigned long is 32 bits on LLP64.
        if flags & STATIC_BUILTIN:
            return {}  # Attributes may live in an interpreter side table.
        dictionary, = struct.unpack_from("<Q", head, TYPE_DICT)
        return self.dictionary(dictionary) if dictionary else {}

    def instance_dict(self, obj):
        cls = self.pointer(obj+8)
        head = self.type_object(cls)
        flags, = struct.unpack_from("<I", head, TYPE_FLAGS)
        size, = struct.unpack_from("<q", head, 32)
        offset, = struct.unpack_from("<q", head, TYPE_DICTOFFSET)
        if flags & MANAGED_DICT:
            from .python_managed import managed_instance_dict
            return managed_instance_dict(self,obj,head)
        if not 16 <= offset <= 4096 or offset%8 or not offset+8 <= size <= 8192:
            raise PythonLayoutError("unsupported negative/invalid instance dict offset")
        dictionary = self.u64(obj+offset)
        return self.dictionary(dictionary) if dictionary else {}

    def area_host(self, area):
        """Native area.owner() storage with native entity.area reverse checks."""
        if self.module.address(AREA_PYTYPE) not in self.mro(area):
            raise PythonLayoutError("model owner is not a native Asio area proxy")
        bridge = self.pointer(area+0x20)
        native = self.pointer(bridge)
        host_bridge = self.pointer(native+0x38)
        host = self.pointer(host_bridge)
        if self.module.address(ENTITY_PYTYPE) not in self.mro(host):
            raise PythonLayoutError("area host is not an Asio entity")
        if self.u64(host+0x20) != host_bridge or self.u64(host_bridge+0x10) != area:
            raise PythonLayoutError("area/entity reverse association changed")
        return host

    def wrapper(self, native):
        control = self.pointer(native+0x18)
        association = self.pointer(control+0x10)
        wrapper, python = struct.unpack("<2Q", self.read(association+8, 16))
        _pointer(wrapper, "native wrapper"); _pointer(python, "Python wrapper")
        if (self.u64(control+8) != native or self.u64(association) != control or
                self.u64(wrapper+8) != python or self.u64(wrapper+0x18) != native or
                self.u64(python+0x20) != wrapper):
            raise PythonLayoutError("expired or inconsistent native/Python association")
        if self.module.address(IENTITY_PYTYPE) not in self.mro(python):
            raise PythonLayoutError("Parent wrapper is not a PyIEntity")
        if self.u64(python+8)==self.module.address(IENTITY_PYTYPE):
            flags,=struct.unpack_from("<I",self.type_object(self.u64(python+8)),TYPE_FLAGS)
            if flags & MANAGED_DICT:
                raise PythonLayoutError("unsupported mutated native PyIEntity dictionary layout")
        return python

    def player_avatar(self, native):
        python = self.wrapper(native)
        attributes = self.instance_dict(python)
        owner, instance = attributes.get("owner"), attributes.get("instance")
        if not owner or not instance:
            return False
        avatar_model = False
        for cls in self.mro(instance):
            attrs = self.class_dict(cls)
            module = attrs.get("__module__")
            if module and self.ascii(module) == "gclient.gameplay.logic_base.models.avatar_model":
                # __name__/__qualname__ are type descriptors, not necessarily dict entries.
                name = self.c_string(struct.unpack_from("<Q", self.type_object(cls), 24)[0])
                if name.rsplit(".",1)[-1] == "AvatarModel":
                    avatar_model = True
                    break
        if not avatar_model:
            return False
        # STORE_ATTR owner receives self.area, not the Python host. See V6 errata.
        host = self.area_host(owner)
        if self.instance_dict(host).get("model") != instance or self.instance_dict(instance).get("model") != python:
            raise PythonLayoutError("model/instance/host primary association disagrees")
        for cls in self.mro(host):
            value = self.class_dict(cls).get("IsPlayerCombatAvatar")
            if value is None:
                continue
            if value not in (self.module.address(TRUE), self.module.address(FALSE)):
                raise PythonLayoutError("player class marker is not a boolean singleton")
            return (owner,host,instance) if value == self.module.address(TRUE) else None
        return False


def classify_player_models(reader, module, capture):
    """Consecutive matching metadata reads; unknown is retained on any ambiguity."""
    def one_pass():
        data, result = DataReader(reader, module), {}
        from .python_runtime import local_player
        from .native_properties import NumericMap
        from .python_dispatch import enemy_context,evaluate_base_enemy
        from .life_state import state_context,life_state
        local_host,context,context_error=None,None,None
        relation_context,relation_error=None,None
        life_context,life_error=None,None
        try:
            context,local_host,_=local_player(data)
        except (PythonLayoutError,MemoryReadError,ValueError) as exc:
            context_error=f"local context: {exc}"
        if context is not None:
            try:relation_context=enemy_context(data,context)
            except (PythonLayoutError,MemoryReadError,ValueError) as exc:
                relation_error=f"opponent context: {exc}"
            try:life_context=state_context(data,context)
            except (PythonLayoutError,MemoryReadError,ValueError) as exc:
                life_error=f"life context: {exc}"
        for record in capture.registry.records:
            identity = observation_id(record)
            value = Classification()
            if not record.in_world or record.entity is None or record.parent != record.entity:
                result[identity] = value
                continue
            try:
                # Revalidate the observed registry association around metadata reads.
                if (data.u64(record.node+0x18) != record.component or data.u64(record.component+0x40) != record.parent or
                        data.u64(record.component+0x378) != record.actor or
                        struct.unpack("<I", data.read(record.actor+0xC,4))[0] != record.key or
                        struct.unpack("<I", data.read(record.node+0x10,4))[0] != record.key or
                        not data.read(record.parent+0x130,1)[0] & 0x10):
                    raise PythonLayoutError("registry association changed")
                linked=data.player_avatar(record.parent)
                if linked:
                    area,host,instance=linked
                    diagnostics=[context_error] if context_error else []
                    values={}
                    try:
                        values=NumericMap(data,area).read({"server_hp","combat_state","faction","combat_team_id",
                                                       "peek_role","is_finder"})
                    except (PythonLayoutError,MemoryReadError,ValueError) as exc:
                        diagnostics.append(f"numeric properties: {exc}")
                    relation=None
                    if relation_context is not None:
                        try:relation=evaluate_base_enemy(data,relation_context,local_host,host)
                        except (PythonLayoutError,MemoryReadError,ValueError) as exc:
                            diagnostics.append(f"opponent operands: {exc}")
                    elif relation_error:diagnostics.append(relation_error)
                    life=None
                    if life_context is not None:
                        try:life=life_state(data,life_context,host)
                        except (PythonLayoutError,MemoryReadError,ValueError) as exc:
                            diagnostics.append(f"life operand: {exc}")
                    elif life_error:diagnostics.append(life_error)
                    facts=PlayerFacts(area,host,tuple(StateFact(value.name,value.kind,value.value,value.descriptor,value.index,value.storage)
                                    for _,value in sorted(values.items())),
                        context.interpreter_id if context else None,
                        "genv.player_with_reverse_area_identity" if context else "unresolved",
                        tuple(diagnostics),relation.enemy if relation else None,
                        relation.rule if relation else None,
                        relation_context.body.function if relation_context else None,
                        life.name if life else None,life.source if life else None)
                    category=Category.OPPONENT if relation and relation.enemy else Category.PLAYER
                    evidence=("verified_base_IsEnemy_dispatch_and_integer_operands" if category is Category.OPPONENT else
                        "observed_area_host_AvatarModel_and_stored_primary_links_no_team_or_life_proof")
                    if life is not None:evidence+='; effective_CombatState_verified'
                    value = Classification(category,life.alive if life else None,None,
                        host==local_host if local_host else None,evidence,facts)
            except (PythonLayoutError, MemoryReadError, ValueError) as exc:
                value = Classification(evidence=f"unresolved: {exc}"[:512])
            result[identity] = value
        return result, data.trace
    first, trace1 = one_pass()
    second, trace2 = one_pass()
    if trace1 != trace2 or first != second:
        return {observation_id(record): Classification(evidence="Python metadata changed between reads")
                for record in capture.registry.records}
    return second
