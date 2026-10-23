const fs = require('fs');
const crypto = require('crypto');
const input = 'python-format/selected-models-static.json';
const raw = fs.readFileSync(input);
const mods = JSON.parse(raw);
const modules = new Map(mods.map(m => [m.index, m]));
const selected = [
  [17226, ['CreateModel','LoadSkeletonAndGraph','BindSkeletonAndGraph','DestroySimpleModel','DestroyCppModel']],
  [25281, ['WeaponModel.__init__','WeaponModel.AttachWeaponToHandEquip','WeaponModel.AttachWeaponToRightHand','WeaponModel.AttachWeaponToHandAnimWeapon']],
  [68957, ['SimpleModel.__init__','SimpleModel.Load','SimpleModel.ReloadSkeleton','SimpleModel.HasActorComponent']],
  [143510, ['AvatarModel.__init__','AvatarModel.Load','AvatarModel.ReloadSkeleton']]
];
const records=[];
for (const [idx, qnames] of selected) {
 const mod=modules.get(idx); if (!mod) throw new Error('module missing '+idx);
 for (const q of qnames) {
  const c=mod.codes.find(x=>x.qualname===q || x.name===q);
  if (!c) { records.push({module_index:idx, qualname:q, found:false}); continue; }
  const names=c.names||[];
  const interesting=[];
  for(let j=0;j<c.instructions.length;j++) {
   const i=c.instructions[j];
   const resolved=(['LOAD_GLOBAL','LOAD_ATTR','LOAD_METHOD','STORE_ATTR','STORE_GLOBAL'].includes(i.opname) ? names[i.arg>>1] : undefined);
   if (/ActorComponent|CreateObject|CreateModel|MHelper|Skeleton|Parent|AttachToParent|AddChild|IsCombatAvatar|IsATMGuardAI|IsPlayerCombatAvatar|SimpleModel|PoseSenderModel|super/.test(String(resolved||''))) {
    const a=Math.max(0,j-3), b=Math.min(c.instructions.length,j+5);
    interesting.push({anchor_offset:i.offset, window:c.instructions.slice(a,b).map(x=>({offset:x.offset,opname:x.opname,arg:x.arg,name:['LOAD_GLOBAL','LOAD_ATTR','LOAD_METHOD','STORE_ATTR','STORE_GLOBAL'].includes(x.opname)?names[x.arg>>1]:undefined,const:(x.opname==='LOAD_CONST'?c.consts[x.arg]:undefined)}))});
   }
  }
  records.push({module_index:idx,decoded_sha256:mod.decoded_sha256,filename:c.filename,qualname:c.qualname,firstlineno:c.firstlineno,marshal_offset:c.marshal_offset,marshal_end:c.marshal_end, names:c.names, consts:c.consts, code_hex:c.code, instruction_count:c.instructions.length, actor_parent_component_windows:interesting});
 }
}
const out={source:input, source_sha256:crypto.createHash('sha256').update(raw).digest('hex'), modules:mods.map(m=>({index:m.index,status:m.status,decoded_sha256:m.decoded_sha256,code_count:m.code_count})), records};
fs.writeFileSync('gameplay/python-model-links/model-link-static.json',JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({source_sha256:out.source_sha256, records:records.map(r=>({module_index:r.module_index,qualname:r.qualname,found:true,windows:r.actor_parent_component_windows?.length,decoded_sha256:r.decoded_sha256}))},null,2));



