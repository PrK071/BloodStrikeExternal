exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
names=['IEntity.Position','IEntity.WorldPosition','IEntity.WorldTransform','ICamera.Project','ICamera.ProjectInner','ICamera.CameraMatrix','ProjectInner','CameraMatrix']
result={n:{enc:pe.d.count(n.encode(enc)) for enc in ['ascii','utf-16-le']} for n in names}
(out/'negative-string-scan.json').write_text(json.dumps(result,indent=2))
print(result)
print((out/'selected-code.json').read_text())
