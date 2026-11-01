from pathlib import Path
import re,ctypes,json
O=Path(__file__).parent;h=(O/'cpython-object.h').read_text();h=re.sub(r'/\*.*?\*/','',h,flags=re.S);h=re.sub(r'//[^\n]*','',h)
body=h.split('struct _typeobject {',1)[1].split('};',1)[0];fields=[('ob_refcnt',ctypes.c_uint64),('ob_type',ctypes.c_uint64),('ob_size',ctypes.c_int64)]
for raw in body.splitlines():
 s=raw.strip()
 if not s or s=='PyObject_VAR_HEAD':continue
 m=re.search(r'(tp_\w+)\s*;',s)
 if 'tp_basicsize, tp_itemsize' in s:fields.append(('tp_basicsize',ctypes.c_int64))
 if not m:print('UNPARSED',s);continue
 name=m.group(1);typ=ctypes.c_uint32 if name in ['tp_flags','tp_version_tag'] else ctypes.c_uint8 if name=='tp_watched' else ctypes.c_uint16 if name=='tp_versions_used' else ctypes.c_uint64
 fields.append((name,typ))
class Type(ctypes.Structure):_fields_=fields
# Header method-suite fields are function pointers, including reserved void* entries.
def count_struct(name,ending='}'):
 pass
sizes={}
for name in ['PyAsyncMethods','PyNumberMethods','PyMappingMethods','PySequenceMethods','PyBufferProcs']:
 m=re.search(r'typedef struct \{([^{}]*)\}\s*'+name+r'\s*;',h,re.S);n=m.group(1).count(';');sizes[name]=n*8
class Heap(ctypes.Structure):_fields_=[('ht_type',Type),('as_async',ctypes.c_ubyte*sizes['PyAsyncMethods']),('as_number',ctypes.c_ubyte*sizes['PyNumberMethods']),('as_mapping',ctypes.c_ubyte*sizes['PyMappingMethods']),('as_sequence',ctypes.c_ubyte*sizes['PySequenceMethods']),('as_buffer',ctypes.c_ubyte*sizes['PyBufferProcs']),('ht_name',ctypes.c_uint64),('ht_slots',ctypes.c_uint64),('ht_qualname',ctypes.c_uint64),('ht_cached_keys',ctypes.c_uint64)]
out={'abi':'WindowsAMD64 LLP64 pointer8 unsignedlong4 Py_GIL_DISABLED absent','sizeof_PyTypeObject':hex(ctypes.sizeof(Type)),'type_offsets':{n:hex(getattr(Type,n).offset) for n,t in fields},'method_suite_sizes':{k:hex(v) for k,v in sizes.items()},'heap_cached_keys':hex(Heap.ht_cached_keys.offset)}
(O/'header-derived-offsets.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

