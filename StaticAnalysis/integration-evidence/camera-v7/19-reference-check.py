"""Synthetic recording checks only. No process or input APIs are called."""
from pathlib import Path
import json,struct
from read_effective_camera import capture_effective_camera,VPTR,PINNED_SHA256
O=Path(__file__).parent
class Module:
 base=0x140000000;sha256=PINNED_SHA256
 def address(self,rva,size=1):return self.base+rva
module=Module();state=0x200000000;client=0x200001000;viewport=0x200004000;camera=client+0x80
base=module.base
data={base+0x80f3840:struct.pack('<Q',state),state+8:struct.pack('<Q',client),client:struct.pack('<Q',base+VPTR['client']),
 client+0x18:struct.pack('<Q',viewport),viewport:struct.pack('<Q',base+VPTR['viewport']),viewport+0x740:struct.pack('<Q',client),
 viewport+0x50:struct.pack('<Q',camera),camera:struct.pack('<Q',base+VPTR['aurora']),viewport+0x18:struct.pack('<HH',1920,1080),
 camera+0x6b4:struct.pack('<16f',*([1.0]*16))}
class Recording:
 def __init__(self,d):self.d=d
 def read(self,address,size):
  value=self.d[address]
  assert len(value)==size
  return value
result=capture_effective_camera(lambda:Recording(data),module)
assert result['camera']==camera and result['native_type']=='aurora'
checks=['positive_typed_aurora_recording']
for label,address,value in [('wrong_client_vptr',client,base+VPTR['viewport']),
 ('broken_camera_alias',viewport+0x50,camera+8),('broken_client_alias',viewport+0x740,client+8),
 ('unsupported_orthographic_storage',camera,base+VPTR['orthographic'])]:
 changed=dict(data);changed[address]=struct.pack('<Q',value)
 try:capture_effective_camera(lambda:Recording(changed),module)
 except ValueError:checks.append(label+'_rejected')
 else:raise AssertionError(label)
changed=dict(data);changed[camera+0x6b4]=struct.pack('<16f',*([2.0]*16));observations=iter([data,changed])
try:capture_effective_camera(lambda:Recording(next(observations)),module)
except ValueError:checks.append('changed_projection_rejected')
else:raise AssertionError('changed projection accepted')
(O/'reference-checks.json').write_text(json.dumps(dict(checks=checks,passed=True,process_access=False,target_execution=False),indent=2))
print(len(checks),'synthetic checks passed')
