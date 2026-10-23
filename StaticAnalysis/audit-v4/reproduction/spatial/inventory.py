exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
for m in __import__('re').finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if s.startswith('ICamera.') or s.startswith('IEntity.') or ('project' in s.lower() and len(s)<40):print(hex(pe.rva(m.start())),s)
