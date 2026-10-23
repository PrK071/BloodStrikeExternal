# Python | bootstrap_npm.py | Python 3.12 standard library | portable npm dependency for local REA CLI.
import base64,hashlib,io,json,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).parent;VERSION='11.16.0';DEST=ROOT/('npm-'+VERSION)
def main():
 url='https://registry.npmjs.org/npm/'+VERSION
 with urllib.request.urlopen(url,timeout=30) as r:meta=json.load(r)
 assert meta['name']=='npm' and meta['version']==VERSION
 dist=meta['dist'];tarball=dist['tarball'];assert tarball.startswith('https://registry.npmjs.org/npm/-/')
 with urllib.request.urlopen(tarball,timeout=60) as r:raw=r.read(20*1024*1024+1)
 assert len(raw)<=20*1024*1024
 algo,encoded=dist['integrity'].split('-',1);assert algo=='sha512'
 assert base64.b64encode(hashlib.sha512(raw).digest()).decode()==encoded
 DEST.mkdir(exist_ok=True)
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tf:
  members=tf.getmembers();assert sum(m.size for m in members)<=100*1024*1024
  for m in members:
   target=(DEST/m.name).resolve();assert target.is_relative_to(DEST.resolve())
  tf.extractall(DEST,filter='data')
 result=dict(name=meta['name'],version=VERSION,source=url,tarball=tarball,integrity=dist['integrity'],
  sha256=hashlib.sha256(raw).hexdigest(),cli=str(DEST/'package/bin/npm-cli.js'),scope='workspace portable copy; no global install or client configuration edits')
 (DEST/'provenance.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
