exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
for m in __import__('re').finditer(rb'[ -~]{4,}\x00',pe.d):
 s=m.group()[:-1].decode()
 if any(t in s for t in ['WorldPosition','WorldTransform','ProjectInner','CameraMatrix','IEntity.Position','ICamera.Project']):print(hex(pe.rva(m.start())),s[:200])
for r in [0x954ad0,0x93f1a0]:
 print('\nFUNCTION',hex(r))
 for i in pe.decode(r):print(pe.row(i))
