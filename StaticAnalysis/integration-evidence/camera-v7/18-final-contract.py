"""Build the implementation contract from selected native evidence, no execution."""
exec((__import__('pathlib').Path(__file__).parent/'01-seeds.py').read_text().split('O=')[0])
O=Path(__file__).parent
vptrs={'scene_client':0x4e632f0,'main_viewport':0x52f0498,'perspective':0x4ebf848,'orthographic':0x4ebfaa0,'aurora':0x4ec0658}
types={}
for label,rva in vptrs.items():
 col=pe.unpack('<Q',rva-8)[0]-pe.base;sig,offset,construction,td,chd,selfr=pe.unpack('<6I',col)
 assert sig==1 and selfr==col and offset==construction==0
 types[label]=dict(vptr_rva=hex(rva),col_rva=hex(col),col_bytes=pe.d[pe.offset(col):pe.offset(col)+24].hex(' '),type_descriptor_rva=hex(td),name=pe.string(td+16),object_offset=offset,
  vptr_prefix=pe.d[pe.offset(rva):pe.offset(rva)+32].hex(' '))
out=dict(target_sha256=pe.sha,scope='disk-only native pointer-flow and RTTI; target never loaded/executed or attached',
 status='typed native render-input camera route established; exact final presented-pixel projection convention remains unproven',
 runtime_root_rva='0x80f3840',pointer_size=8,endian='little',
 route=[dict(name='render_state',read='ptr(module_base + 0x80f3840)',evidence='5fc385'),
        dict(name='client',read='ptr(render_state + 0x08)',require_type='scene_client',evidence='5fc393 passes this provider to MainRenderViewport construction'),
        dict(name='viewport',read='ptr(client + 0x18)',require_type='main_viewport',evidence='db8d15 calls provider slot0x80; SceneViewportClient slot0x80=293980 writes [client+0x18]=viewport'),
        dict(name='effective_camera',read='ptr(viewport + 0x50)',require_type=['aurora','perspective','orthographic'],evidence='db8cb2 provider slot0x50 -> 3afcf0 returns client+0x80; db8cf6->db7870->db7110 writes camera atviewport+0x50')],
 mandatory_alias_gates=['ptr(viewport+0x740) == client','effective_camera == client+0x80','all exact vptrs and nonnull bounded canonical pointers match pinned image'],
 types=types,
 viewport_dimensions=dict(width=dict(offset='0x18',type='uint16'),height=dict(offset='0x1a',type='uint16'),source='db74f0 updates fields and camera via slot0x128; image/display-coordinate scaling not derived'),
 projection_storage=dict(aurora=dict(offset='0x6b4',bytes=64,float_count=16,getter_rva='0x493c00',getter_slot='0x70'),
                         perspective=dict(offset='0x2d8',bytes=64,float_count=16,getter_rva='0x485230',getter_slot='0x70'),
                         orthographic=dict(read_supported=False,reason='slot0x70 at4876a0 computes output; no equivalent fixed stored64-byte matrix established')),
 projection_convention=dict(row_or_column_vectors='unresolved',clip_depth_range='unresolved',handedness='unresolved',pixel_mapping='unresolved',matrix_meaning='projection output of concrete native camera virtualslot0x70; not a claimed combined view-projection',
   final_shader_alias='the CameraProjection writer c47f8c consumes a virtualslot0x70 and stores64bytes at+0xfa0; its specific camera/context alias to this viewport is not yet proved'),
 source_to_effective=dict(source='existing typed GetGameplay/ClientPlayer.Camera acquisition',
 update_function_rva='0x343ef0',update_class='scene_client',update_vtable_slot='0xb8',caller_rva='0x343040',caller_vtable_slot='0x90',
 source_fields=dict(view_matrix='0x41c..0x44b',fov='0x454',near='0x458',far='0x45c',is_orthographic='0x418',use_aurora='0x450',extra_projection_enable='0x419'),
 selection_precedence=['UseAuroraCamera !=0 -> AuroraCamera','otherwise IsOrthographic !=0 -> Orthographic3dCamera','otherwise -> PerspectiveCamera'],
 transforms='SceneViewportClient update copies48bytes from ICamera+0x41c into client+0xee0 then calls effective camera slot0x68 with that copy',
 lifetime='null gameplay or null source camera causes update to return without refreshing destination; previous native rendercamera values can remain',
 identity='ICamera source and effective nativecamera are separate objects, connected by a copy/update path; require current observation comparisons, not pointer equality'),
 acquisition_requirements=['Read only; no virtual calls or engine calls are necessary for Aurora/Perspective storedprojection capture',
 'Bracket/recheck global/root/client/viewport/camera pointers, vptrs, required aliases, dimensions and64projectionbytes',
 'Validate projection elements finite; reject unsupported orthographic storage rather than use a guessed offset',
 'Keep source camera and effective camera snapshots distinct; compare gates/type/dimensions and copied fields only when validated',
 'Record that equal reads cannot prove lifetime/atomicity or absence of ABA, and paused/teardown states can retain older effectivecamera data'],
 remaining_unknowns=['root creation/lifetime and actual live subtype availability not observed',
 'current camera-to-mainviewport binding must satisfy all runtime alias/type gates',
 'other writers/overrides after the shown update, scheduling, final shader alias, jitter, resolution scaling and finalpixel convention remain unresolved'])
(O/'effective-camera-contract.json').write_text(json.dumps(out,indent=2))
# Keep a small implementation-facing evidence cut; large search catalogues remain exploratory.
sources=['selected-functions.json','main-viewport-functions.json','render-camera-link.json','viewport-client-selector.json','effective-camera-types.json','projection-storage.json']
selection={0x343040,0x343ef0,0x3afcf0,0x293980,0xdb8c90,0xdb7870,0xdb7110,0x493c00,0x485230,0x276280}
cut={}
for name in sources:
 j=json.loads((O/name).read_text())
 for key,value in j.items():
  try:r=int(key,16)
  except ValueError:continue
  if r in selection:cut[key]=value
callers=json.loads((O/'direct-callers.json').read_text());cut['0x5fc290']=dict(rows=callers['functions']['0x5fc290'])
cut['native_types']=types
(O/'discriminating-native-evidence.json').write_text(json.dumps(cut,indent=2))
print('contract and discriminating native cut written',len(cut))
