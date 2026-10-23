# Python | seal_audit_v3.py | Python 3.12 standard library | offline report/evidence integrity.
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=True)+'\n',encoding='utf8')

def seal(root):
 out=root/'audit-v3'
 summary=json.loads((out/'summary.json').read_text());assert summary['status']=='PASS_SELECTED_EVIDENCE'
 locked=json.loads((out/'baseline-lock.json').read_text())
 for name,expected in locked['input_sha256'].items():assert sha(root/name)==expected,name
 assert sha(Path(summary['binary']))==summary['sha256']
 graphs=json.loads((out/'reachable-code.json').read_text())
 rows={r['evidence_id']:r for g in graphs for r in g['instructions']}
 assert len(rows)==summary['unique_reachable_instructions']
 claims=json.loads((out/'claims.json').read_text());data=json.loads((out/'data-evidence.json').read_text())
 report=(root/'AUDITORIA-V3.md').read_text(encoding='utf8')
 dataids={d['id'] for d in data};claimids=[c['id'] for c in claims]
 assert len(claimids)==len(set(claimids))
 for c in claims:
  assert c['id'] in report,c['id']
  assert c['sample_sha256']==summary['sha256']
  assert all(i in rows for i in c['instruction_evidence'])
  assert all(i in dataids for i in c['data_evidence'])
  assert all(i in locked['inherited_claim_ids'] for i in c['legacy_ids'])
 def pt(n):return f'{n:,}'.replace(',','.')
 assert f'**{pt(len(graphs))}**' in report
 assert f'**{pt(len(rows))}**' in report
 with Path(summary['binary']).open('rb') as f:
  for r in list(rows.values())+data:
   raw=bytes.fromhex(r['bytes']);f.seek(int(r['file_offset'],16));assert f.read(len(raw))==raw,r.get('rva')
 for link in re.findall(r'\]\(([^)]+)\)',report):
  if '://' not in link and not link.endswith('artifact-sha256.json'):assert (root/link).is_file(),link
 verification=dict(status='PASS_REPORT_AND_DELIVERY',generated_utc=datetime.now(timezone.utc).isoformat(),
                   sha256=summary['sha256'],claim_ids=claimids,instruction_records_rechecked=len(rows),
                   data_blocks_rechecked=len(data),prior_artifacts_unchanged=True,runtime_game_access=False,
                   limitation='Cross-reference/integrity checks; not an independent semantic review or runtime validation.')
 save(out/'delivery-verification.json',verification)
 files=[p for p in out.iterdir() if p.is_file() and p.name!='artifact-sha256.json']
 files += [root/n for n in ('AUDITORIA-V3.md','audit_v3.py','v3-claims-spec.json','run-audit-v3.ps1','seal_audit_v3.py')]
 save(out/'artifact-sha256.json',{str(p.relative_to(root)):sha(p) for p in sorted(files)})
 print(json.dumps(verification,indent=2))

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).parent)
 a=p.parse_args();out=a.root/'audit-v3';out.mkdir(parents=True,exist_ok=True)
 save(out/'delivery-verification.json',dict(status='RUNNING',runtime_game_access=False))
 try:seal(a.root)
 except Exception as exc:
  save(out/'delivery-verification.json',dict(status='FAIL',error=repr(exc),runtime_game_access=False))
  raise

if __name__=='__main__':main()
