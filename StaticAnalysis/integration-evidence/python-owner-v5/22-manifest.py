from pathlib import Path
import json,hashlib
O=Path(__file__).parent
sources=json.loads((O/'header-sources.json').read_text());sources.append(dict(file='boolobject.c',url='https://raw.githubusercontent.com/python/cpython/v3.14.0/Objects/boolobject.c',sha256=hashlib.sha256((O/'boolobject.c').read_bytes()).hexdigest()))
(O/'header-sources.json').write_text(json.dumps(sources,indent=2))
c=json.loads((O/'layout-contract.json').read_text());c['header_sources']=sources;c['sample_confirmation']={'PyObject.ob_type':'2a1cbef stores type into allocation+8;2039326 reads P+8','IEntity.tp_dictoffset':'20525ab stores 0x10 at79a0180=type79a0060+120','P.dict':'__dict__ getter1ccfa30 direct P+10','PyDictObject':'allocator2a93930 writes+10,+18,+20,+28','dict_entry_addressing':'lookup2a8bf80 reads kind+a,exponent+9, selects general/unicode entry strides','Unicode_masks_and_mro_tuple':'official header-derived; no native state/tuple consumer validation in this pass','singletons':'bool typename+tp_new2a14310+official bool_new source pattern; no matching selected PE export'}
(O/'layout-contract.json').write_text(json.dumps(c,indent=2))
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='artifact-manifest.json'}
(O/'artifact-manifest.json').write_text(json.dumps(manifest,indent=2))
print('artifact files',len(manifest),'header/source files',len(sources))
