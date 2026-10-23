import json
p=r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\audit-v4\spatial\render-source\tailcaller-caller-functions.json';rows=json.load(open(p))['0x222ed0']
for x in rows:
 r=int(x['rva'],16)
 if r<0x222f60 or 0x2234c0<r<0x2235a0:print(x['rva'],x['text'],x.get('rip_target_string') or '')
