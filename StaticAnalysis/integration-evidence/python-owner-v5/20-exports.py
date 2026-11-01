exec((__import__('pathlib').Path(__file__).parent/'01-factory.py').read_text().split('O=')[0])
O=Path(__file__).parent;r,n=pe.dirs[0];d=pe.unpack('<IIHHIIIIIII',r);count=d[7];names=d[9];ords=d[10];fns=d[8];out=[]
for i in range(count):
 sr=pe.unpack('<I',names+i*4)[0];name=pe.string(sr)
 if name and ('PyBool' in name or name in ['PyObject_GenericGetAttr','PyObject_GenericSetAttr','PyObject_SetAttr','PyDict_Next','PyUnicode_Type','PyDict_Type','PyBool_Type','_Py_TrueStruct','_Py_FalseStruct']):
  oi=pe.unpack('<H',ords+i*2)[0];fr=pe.unpack('<I',fns+oi*4)[0];out.append(dict(name=name,rva=hex(fr),forwarder=pe.string(fr) if r<=fr<r+n else None));print(name,hex(fr))
(O/'python-export-identities.json').write_text(json.dumps({'name_count':count,'selected':out},indent=2))
