# Python | install_static_providers.py | Python 3.12 standard library | portable Ghidra/JDK for file-only analysis.
import hashlib,json,stat,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).parent/'providers'
GHIDRA_URL='https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip'
GHIDRA_SHA='ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db'
JDK_URL='https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.9%2B10/OpenJDK21U-jdk_x64_windows_hotspot_21.0.9_10.zip'
JDK_SHA='1c67df516e9795c0b09f5714bfe151da2e3cc988082042f5bbb60d75e4e63fb5'

def acquire(url,expected,label):
 path=ROOT/(label+'.zip');temporary=ROOT/(label+'.download')
 if path.is_file() and hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==expected:return path
 request=urllib.request.Request(url,headers={'User-Agent':'LocalStaticAnalysis/1.0'})
 with urllib.request.urlopen(request,timeout=60) as response,temporary.open('wb') as output:
  digest=hashlib.sha256();total=0;last=0
  while chunk:=response.read(1048576):
   total+=len(chunk)
   if total>800*1048576:raise ValueError('archive size bound')
   output.write(chunk);digest.update(chunk)
   if total-last>=64*1048576:print(label,total//1048576,'MiB',flush=True);last=total
 assert digest.hexdigest()==expected,(label,'SHA mismatch')
 temporary.replace(path);return path

def unpack(archive,dest):
 dest.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  infos=z.infolist();assert len(infos)<=100000 and sum(x.file_size for x in infos)<=3*1024**3
  for info in infos:
   assert (dest/info.filename).resolve().is_relative_to(dest.resolve())
   assert not stat.S_ISLNK(info.external_attr>>16)
  assert z.testzip() is None
  z.extractall(dest)

def main():
 ROOT.mkdir(exist_ok=True)
 provenance=dict(ghidra=dict(url=GHIDRA_URL,sha256=GHIDRA_SHA),jdk=dict(api='https://api.github.com/repos/adoptium/temurin21-binaries/releases?per_page=3',version='21.0.9+10',url=JDK_URL,sha256=JDK_SHA),scope='workspace portable tools; no global PATH, client registration or game execution')
 (ROOT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 for label,url,sha in [('jdk21',JDK_URL,JDK_SHA),('ghidra12.1.4',GHIDRA_URL,GHIDRA_SHA)]:
  dest=ROOT/label
  if not dest.exists():unpack(acquire(url,sha,label),dest)
  print(label,'ready',flush=True)
 print(json.dumps(provenance,indent=2))

if __name__=='__main__':main()
