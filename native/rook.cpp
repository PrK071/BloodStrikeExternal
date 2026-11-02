// C++ / native/rook.cpp / Windows x64 / BloodStrike ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>
#include <bcrypt.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <mutex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

using U=uint64_t;
using Clock=std::chrono::steady_clock;
namespace fs=std::filesystem;
constexpr U IMAGE_SIZE=0x94e9000;
constexpr char SAMPLE[]="ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747";
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
bool pointer(U p){return p>=0x10000&&p<=0x7ffffffffff8&&!(p&7);}
struct Handle{
 HANDLE h=nullptr;
 explicit Handle(HANDLE v=nullptr):h(v){}
 ~Handle(){if(h&&h!=INVALID_HANDLE_VALUE)CloseHandle(h);}
 Handle(const Handle&)=delete; Handle& operator=(const Handle&)=delete;
};
struct Reader{
 HANDLE h; U base; bool cache=true;
 size_t reads=0;
 std::unordered_map<U,std::array<unsigned char,4096>> pages;
 Reader(HANDLE h_,U b):h(h_),base(b){}
 void raw(U p,void* out,size_t n){
  require(p>=0x10000&&n<=16*1024*1024&&p+n>=p&&p+n<=0x800000000000,"invalid read range");
  SIZE_T got=0;++reads;
  if(!ReadProcessMemory(h,reinterpret_cast<void*>(p),out,n,&got)||got!=n)
   throw std::runtime_error("ReadProcessMemory failed: "+std::to_string(GetLastError()));
 }
 void read(U p,void* out,size_t n){
  if(!cache){raw(p,out,n);return;}
  require(n<=1024*1024,"metadata read budget");
  auto dst=static_cast<unsigned char*>(out);
  while(n){
   U page=p&~U(4095); size_t off=size_t(p-page),take=std::min(n,4096-off);
   auto it=pages.find(page);
   if(it==pages.end()){
    require(pages.size()<4096,"metadata page budget");
    std::array<unsigned char,4096> bytes{};
    SIZE_T got=0;++reads;
    if(!ReadProcessMemory(h,reinterpret_cast<void*>(page),bytes.data(),4096,&got)||got!=4096){raw(p,dst,take);p+=take;dst+=take;n-=take;continue;}
    it=pages.emplace(page,bytes).first;
   }
   std::memcpy(dst,it->second.data()+off,take);p+=take;dst+=take;n-=take;
  }
 }
 template<class T>T get(U p){T v{};read(p,&v,sizeof(v));return v;}
 U ptr(U p){U v=get<U>(p);require(pointer(v),"invalid pointer");return v;}
 template<class T>std::vector<T> vec(U p,size_t n){require(n<=1024*1024/sizeof(T),"vector byte budget");std::vector<T> v(n);if(n)read(p,v.data(),n*sizeof(T));return v;}
 U rva(U x,size_t n=8){require(x<IMAGE_SIZE&&n<=IMAGE_SIZE-x,"RVA outside build");return base+x;}
};
U castBase(Reader& r,U obj,U target=0x7DE5D78){
 U vt=r.ptr(obj);require(vt>=r.base+8&&vt<r.base+IMAGE_SIZE,"vtable outside module");
 U col=r.ptr(vt-8);require(col>=r.base&&col+24<r.base+IMAGE_SIZE,"COL outside module");
 auto c=r.get<std::array<uint32_t,6>>(col);
 require(c[0]==1&&r.base+c[5]==col&&!c[2],"unsupported COL");
 auto hi=r.get<std::array<uint32_t,4>>(r.rva(c[4],16));
 require(!hi[0]&&hi[2]>=1&&hi[2]<=256&&!(hi[1]&4),"invalid hierarchy");
 auto bases=r.vec<uint32_t>(r.rva(hi[3],hi[2]*4),hi[2]);
 int matches=0;int32_t displacement=0;
 for(size_t i=0;i<bases.size();++i){
  auto b=r.get<std::array<int32_t,6>>(r.rva(bases[i],24));
  if(i==0)require(U(uint32_t(b[0]))==c[3]&&b[1]==int(hi[2])-1&&!b[2]&&b[3]==-1,"hierarchy identity");
  if(U(uint32_t(b[0]))==target){require(b[3]==-1&&!(b[5]&31),"unsupported base");++matches;displacement=b[2];}
 }
 require(matches==1,"base absent/ambiguous");U result=obj-c[1]+displacement;require(pointer(result),"base address");return result;
}

// These readers inspect the game's existing CPython objects as data. No Python runtime is linked or launched.
std::unordered_map<std::string,U> dictionaryHashes;
struct PyData{
 Reader& r; U interpreter=0;
 std::unordered_map<U,std::map<std::string,U>> dictionaries;
 std::unordered_map<U,std::map<std::string,U>> descriptorTables;
 explicit PyData(Reader& rr):r(rr){}
 bool exact(U o,U type){return pointer(o)&&r.get<U>(o+8)==r.base+type;}
 std::string ascii(U o){
  require(exact(o,0x7A16E10),"not Unicode");
  auto n=r.get<int64_t>(o+16);auto state=r.get<uint32_t>(o+32);
  require(n>=0&&n<=512&&(state&0x60)==0x60&&((state>>2)&7)==1,"unsupported Unicode");
  auto bytes=r.vec<char>(o+40,size_t(n)+1);require(bytes.back()==0,"Unicode terminator");
  for(int64_t i=0;i<n;++i)require(static_cast<unsigned char>(bytes[i])<128,"non-ASCII");
  std::string result{bytes.data(),size_t(n)};auto hash=r.get<int64_t>(o+24);if(hash!=-1)dictionaryHashes[result]=U(hash);return result;
 }
 std::map<std::string,U> table(U keys,U values=0){
  auto ls=r.get<uint8_t>(keys+8),lb=r.get<uint8_t>(keys+9),kind=r.get<uint8_t>(keys+10);
  auto count=r.get<int64_t>(keys+24);
  require(ls<=20&&lb>=ls&&lb<=23&&kind<=2&&count>=0&&count<=16384,"dict keys bounds");
  require((kind==2)==bool(values),"dict storage kind");
  if(values){auto cap=r.get<uint8_t>(values);require(cap>=1&&cap<=30&&count<=cap,"split capacity");}
  size_t stride=kind==0?24:16;U entries=keys+32+(U(1)<<lb);
  auto raw=r.vec<unsigned char>(entries,size_t(count)*stride);
  std::map<std::string,U> result;
  for(int64_t i=0;i<count;++i){
   U key=0,value=0;std::memcpy(&key,raw.data()+i*stride+(kind==0?8:0),8);
   if(values)value=r.get<U>(values+8+i*8);else std::memcpy(&value,raw.data()+i*stride+(kind==0?16:8),8);
   if(!key||!value||!exact(key,0x7A16E10))continue;
   try{auto name=ascii(key);require(!result.contains(name),"duplicate dictionary key");result.emplace(std::move(name),value);}catch(const std::exception&){continue;}
  }
  return result;
 }
 const std::map<std::string,U>& dict(U obj){
  auto it=dictionaries.find(obj);if(it!=dictionaries.end())return it->second;
  require(exact(obj,0x7A19900),"not dict");
  return dictionaries.emplace(obj,table(r.ptr(obj+32),r.get<U>(obj+40))).first->second;
 }
 U dictItem(U obj,const std::string& name){
  require(exact(obj,0x7A19900),"not dict");
  auto found=dictionaryHashes.find(name);U values=r.get<U>(obj+40);
  if(values||found==dictionaryHashes.end())return item(dict(obj),name);
  U keys=r.ptr(obj+32);auto ls=r.get<uint8_t>(keys+8),lb=r.get<uint8_t>(keys+9),kind=r.get<uint8_t>(keys+10);auto count=r.get<int64_t>(keys+24);
  require(ls<=20&&lb>=ls&&lb<=ls+3&&kind<=1&&count>=0&&count<=16384,"dict probe bounds");
  U hash=found->second,perturb=hash,mask=(U(1)<<ls)-1,bucket=hash&mask,entries=keys+32+(U(1)<<lb);size_t width=size_t(1)<<(lb-ls),stride=kind==0?24:16;
  for(U probe=0;probe<(U(1)<<ls)+16;++probe){
   U address=keys+32+bucket*width;int64_t index=width==1?r.get<int8_t>(address):width==2?r.get<int16_t>(address):width==4?r.get<int32_t>(address):r.get<int64_t>(address);
   if(index==-1)return 0;
   if(index>=0){require(index<count,"dict probe index");U entry=entries+index*stride,key=r.get<U>(entry+(kind==0?8:0)),value=r.get<U>(entry+(kind==0?16:8));if(key&&value&&exact(key,0x7A16E10)&&r.get<U>(key+24)==hash&&ascii(key)==name)return value;}
   else require(index==-2,"dict probe sentinel");
   perturb>>=5;bucket=(bucket*5+perturb+1)&mask;
  }
  throw std::runtime_error("dict probe exhausted");
 }
 std::vector<U> mro(U obj){
  U type=r.ptr(obj+8),tuple=r.ptr(type+0x158);require(exact(tuple,0x7A18CE0),"not MRO tuple");
  auto count=r.get<int64_t>(tuple+16);require(count>=1&&count<=64,"MRO count");
  auto v=r.vec<U>(tuple+32,count);require(v.front()==type,"MRO first type");return v;
 }
 bool derived(U obj,U type){auto v=mro(obj);return std::find(v.begin(),v.end(),r.base+type)!=v.end();}
 U item(const std::map<std::string,U>& d,const std::string& k){auto it=d.find(k);return it==d.end()?0:it->second;}
 std::map<std::string,U> instance(U o){
  U cls=r.ptr(o+8);auto flags=r.get<uint32_t>(cls+0xA8);auto size=r.get<int64_t>(cls+0x20);
  if(flags&16){
   if((flags&4)&&size>=16&&size<=8192&&r.get<uint8_t>(o+size+3)==1)return table(r.ptr(cls+0x370),o+size);
   U d=r.get<U>(o-0x18);return d?dict(d):std::map<std::string,U>{};
  }
  auto off=r.get<int64_t>(cls+0x120);require(off>=16&&off<=4096&&off+8<=size&&size<=8192,"instance dict offset");
  U d=r.get<U>(o+off);return d?dict(d):std::map<std::string,U>{};
 }
 U instanceItem(U o,const std::string& name){
  U cls=r.ptr(o+8);auto flags=r.get<uint32_t>(cls+0xA8);if(flags&16)return item(instance(o),name);
  auto off=r.get<int64_t>(cls+0x120),size=r.get<int64_t>(cls+0x20);require(off>=16&&off<=4096&&off+8<=size&&size<=8192,"instance dict offset");U d=r.get<U>(o+off);return d?dictItem(d,name):0;
 }
 std::map<std::string,U> classdict(U cls){
  U d=r.get<U>(cls+0x108);
  if(r.get<uint32_t>(cls+0xA8)&2){
   require(interpreter!=0,"interpreter needed for builtin type");
   U token=r.get<U>(cls+0x168);require(token>=1&&token<=200,"builtin type token");--token;
   U state=interpreter+0x2BF38+0x30*token;
   if(r.get<U>(state)!=cls){require(token<10,"builtin side table");state=interpreter+0x2E4C8+0x30*token;}
   require(r.get<U>(state)==cls&&!r.get<int32_t>(state+0xC),"builtin state identity");d=r.get<U>(state+0x18);
  }
  return d?dict(d):std::map<std::string,U>{};
 }
 U classattr(U obj,const std::string& name){for(U cls:mro(obj)){U v=0;if(r.get<uint32_t>(cls+0xA8)&2)v=item(classdict(cls),name);else{U d=r.get<U>(cls+0x108);if(d)v=dictItem(d,name);}if(v)return v;}return 0;}
 U area(U host){
  require(derived(host,0x796F3C0),"not entity host");U a=r.ptr(r.ptr(host+0x20)+0x10);
  require(derived(a,0x796C240),"not area");U n=r.ptr(r.ptr(a+0x20));
  require(r.get<U>(r.ptr(n+0x38))==host,"area reverse owner");return a;
 }
 U local(){
  auto cookie=r.get<std::array<char,8>>(r.base+0x925F000);
  require(!std::memcmp(cookie.data(),"xdebugpy",8)&&r.get<U>(r.base+0x925F008)==0x030E00F0&&!r.get<U>(r.base+0x925F010),"runtime build");
  U current=r.get<U>(r.base+0x925F328),found=0;std::set<U> seen;
  while(current){
   require(seen.size()<64&&seen.insert(current).second,"interpreter cycle");
   U modules=r.get<U>(current+0x1DE8);
   if(modules){
    U builtins=dictItem(modules,"builtins");
    if(builtins&&exact(builtins,0x7A1B1F0)){
     U env=dictItem(r.ptr(builtins+0x10),"genv");
     if(env){
      auto attrs=instance(env);U player=item(attrs,"player"),main=item(attrs,"main_player"),replay=item(attrs,"replay_player");
      if(player&&player!=r.base+0x7A0A150){
       require(!found&&(!main||main==player)&&(!replay||replay==player||replay==r.base+0x7A0A150),"ambiguous player");
       area(player);found=player;interpreter=current;
      }
     }
    }
   }
   current=r.get<U>(current+0x1C68);
  }
  require(found!=0,"local player absent");return found;
 }
 struct Avatar{U host=0,area=0,model=0,wrapper=0;};
 Avatar avatar(U native){
  U control=r.ptr(native+0x18),association=r.ptr(control+0x10),bridge=r.ptr(association+8),wrapper=r.ptr(association+0x10);
  require(r.get<U>(control+8)==native&&r.get<U>(association)==control&&r.get<U>(bridge+8)==wrapper&&r.get<U>(bridge+0x18)==native&&r.get<U>(wrapper+0x20)==bridge,"wrapper identity");
  require(derived(wrapper,0x79A0060),"not PyIEntity");
  auto attrs=instance(wrapper);U host=item(attrs,"owner");require(host&&derived(host,0x796F3C0),"no direct combat owner");
  U a=area(host),model=instanceItem(host,"model");require(model!=0,"no primary model");
  U stored=item(attrs,"instance");require(!stored||stored==model,"secondary model");
  require(instanceItem(model,"owner")==host&&instanceItem(model,"model")==wrapper,"primary model reverse association");
  bool modelType=false;
  for(U cls:mro(model)){
   U name=r.ptr(cls+0x18);std::string s;
   for(size_t i=0;i<256;++i){char c=r.get<char>(name+i);if(!c)break;s+=c;}
   if(s=="AvatarModel"||s.ends_with(".AvatarModel")){modelType=true;break;}
  }
  require(modelType,"not AvatarModel");
  U a1=classattr(host,"IsPlayerCombatAvatar"),a2=classattr(host,"IsRobotCombatAvatar");
  require((!a1||a1==r.base+0x7A129B0||a1==r.base+0x7A12990)&&(!a2||a2==r.base+0x7A129B0||a2==r.base+0x7A12990),"nonboolean combat marker");
  require(a1==r.base+0x7A129B0||a2==r.base+0x7A129B0,"not combat avatar");
  return {host,a,model,wrapper};
 }
};

struct Numeric{
 Reader& r;PyData& py;U host,area,state,storage,schema,begin,count,nameIndex;int stride,kind;
 std::map<std::string,U> descriptors;
 Numeric(PyData& p,U h):r(p.r),py(p),host(h){
  area=p.area(h);U native=r.ptr(r.ptr(area+0x20)),map=r.ptr(native+0x1D8);
  require(p.derived(map,0x796A420),"not numeric map");state=r.ptr(r.ptr(map+0x20)+0x10);
  U meta=r.ptr(state);nameIndex=r.ptr(meta+0x20);schema=r.ptr(meta+0x28);storage=r.ptr(state+0x18);
  U vt=r.get<U>(storage)-r.base;kind=vt==0x555BA60?0:vt==0x555BB58?1:vt==0x555BD48?2:-1;
  require(kind>=0&&r.get<U>(storage+8)==state&&r.get<U>(storage+0x10)==schema,"numeric storage identity");
  stride=kind==2?16:8;count=r.get<U>(schema+0x10);begin=r.ptr(storage+0x18);
  U end=r.get<U>(storage+0x20),cap=r.get<U>(storage+0x28);
  require(count<=65536&&end==begin+count*stride&&cap>=end,"numeric bounds");
  if(auto cached=py.descriptorTables.find(nameIndex);cached!=py.descriptorTables.end()){descriptors=cached->second;return;}
  U sentinel=r.ptr(nameIndex+0x18),buckets=r.ptr(nameIndex+0x28),mask=r.get<U>(nameIndex+0x40);
  require(mask<65536&&!((mask+1)&mask),"numeric bucket mask");
  auto data=r.vec<std::array<U,2>>(buckets,mask+1);std::set<U> visited;
  for(auto b:data){
   if(b[1]==sentinel){require(b[0]==sentinel,"empty bucket mismatch");continue;}
   for(U node=b[1];;node=r.ptr(node+8)){
    require(node!=sentinel&&visited.size()<16384&&visited.insert(node).second,"numeric descriptor cycle");
    U key=r.ptr(node+0x10),d=r.ptr(node+0x18);
    try{descriptors.emplace(py.ascii(key),d);}catch(const std::exception&){}
    if(node==b[0])break;
   }
  }
  py.descriptorTables.emplace(nameIndex,descriptors);
 }
 double get(const std::string& name){
  auto it=descriptors.find(name);require(it!=descriptors.end(),"numeric property absent");
  auto idx=r.get<int32_t>(it->second);require(idx>=0&&U(idx)<count,"numeric index");
  // Verify membership in this schema, rather than trusting an unrelated descriptor.
  U first=r.get<U>(schema+0x40),last=r.get<U>(schema+0x48);require(last>=first&&(last-first)%16==0&&(last-first)/16<=16384,"schema bounds");
  bool member=false;for(auto pair:r.vec<std::array<U,2>>(first,(last-first)/16))if(pair[1]==it->second){member=true;break;}
  require(member,"foreign numeric descriptor");
  U cell=begin+U(idx)*stride;int k=kind==2?r.get<uint8_t>(cell+8):kind;require(k==0||k==1,"unsupported numeric tag");
  double v=k==0?double(r.get<int64_t>(cell)):r.get<double>(cell);require(std::isfinite(v),"nonfinite property");return v;
 }
};

struct V3{float x=0,y=0,z=0;};
struct P2{float x=0,y=0;bool front=false,inside=false;};
struct Pose{
 std::array<float,12> m{};std::array<int32_t,3> anchor{};
 V3 world(V3 p)const{return {m[9]+p.x*m[0]+p.y*m[3]+p.z*m[6],m[10]+p.x*m[1]+p.y*m[4]+p.z*m[7],m[11]+p.x*m[2]+p.y*m[5]+p.z*m[8]};}
};
Pose pose(Reader& r,U entity){
 Pose p;p.m=r.get<std::array<float,12>>(entity+0x58);p.anchor=r.get<std::array<int32_t,3>>(entity+0x1AC);
 if(p.anchor==std::array<int32_t,3>{INT32_MAX,INT32_MAX,INT32_MAX})p.anchor={0,0,0};
 for(float f:p.m)require(std::isfinite(f)&&std::abs(f)<1e8,"invalid entity pose");return p;
}
struct Camera{
 std::array<float,12> view{};std::array<int32_t,3> anchor{};int width=0,height=0;float sx=0,sy=0,fov=0;
 P2 project(V3 p)const{
  float x=p.x*view[0]+p.y*view[3]+p.z*view[6]+view[9];
  float y=p.x*view[1]+p.y*view[4]+p.z*view[7]+view[10];
  float z=p.x*view[2]+p.y*view[5]+p.z*view[8]+view[11];
  if(!std::isfinite(z)||z>=-0.001f)return {};
  float px=width*.5f+(width*.5f)*sx*x/-z,py=height*.5f-(height*.5f)*sy*y/-z;
  if(!std::isfinite(px)||!std::isfinite(py)||std::abs(px)>32760||std::abs(py)>32760)return {};
  return {px,py,true,px>=0&&px<width&&py>=0&&py<height};
 }
};
Camera camera(Reader& r){
 U root=r.ptr(r.base+0x80D5980),gameplay=castBase(r,r.ptr(root+0x58),0x7E35098);
 U player=castBase(r,r.ptr(gameplay+0x58),0x7E57120),source=castBase(r,r.ptr(player+0xD88),0x7DE5D50);
 require(!r.get<uint8_t>(source+0x418),"orthographic camera");
 U state=r.ptr(r.base+0x80F3840),client=r.ptr(state+8),viewport=r.ptr(client+0x18);
 require(r.get<U>(client)==r.base+0x4E632F0&&r.get<U>(viewport)==r.base+0x52F0498&&r.get<U>(viewport+0x740)==client,"render viewport identity");
 U native=r.ptr(viewport+0x50),vt=r.get<U>(native);require(native==client+0x80,"render camera alias");
 U offset=vt==r.base+0x4EC0658?0x6B4:vt==r.base+0x4EBF848?0x2D8:0;require(offset!=0,"unsupported render camera");
 Camera c;auto wh=r.get<std::array<uint16_t,2>>(viewport+0x18);c.width=wh[0];c.height=wh[1];
 require(c.width>0&&c.height>0&&c.width<=8192&&c.height<=8192,"viewport dimensions");
 auto proj=r.get<std::array<float,16>>(native+offset);c.sx=proj[0];c.sy=proj[5];
 require(std::isfinite(c.sx)&&std::isfinite(c.sy)&&c.sx>0&&c.sy>0,"projection scale");
 c.fov=2*std::atan(1/c.sy)*180/3.14159265358979323846f;
 c.anchor=pose(r,source).anchor;
 c.view=r.get<std::array<float,12>>(client+0xEE0);
 for(float f:c.view)require(std::isfinite(f),"nonfinite render view");
 return c;
}
struct Actor{U node=0,component=0,actor=0,entity=0,host=0;uint32_t key=0;double hp=0,faction=0;bool alive=false,enemy=false;};
bool same(const Actor& a,const Actor& b){return a.key==b.key&&a.component==b.component&&a.actor==b.actor&&a.entity==b.entity&&a.host==b.host;}
bool identity(Reader& r,const Actor& a){return r.get<U>(a.node+0x18)==a.component&&r.get<uint32_t>(a.node+0x10)==a.key&&r.get<U>(a.component+0x40)==a.entity&&r.get<U>(a.component+0x378)==a.actor&&r.get<uint32_t>(a.actor+0xC)==a.key&&(r.get<uint8_t>(a.entity+0x130)&0x10);}
std::vector<Actor> registry(Reader& r){
 U root=r.ptr(r.base+0x8B7CD90),sentinel=r.ptr(root+8),node=r.get<U>(sentinel);std::set<U> seen;std::set<uint32_t> keys;std::vector<Actor> result;
 while(node!=sentinel){
  require(pointer(node)&&seen.size()<10000&&seen.insert(node).second,"registry cycle/budget");
  auto raw=r.get<std::array<U,4>>(node);Actor a;a.node=node;a.key=uint32_t(raw[2]);a.component=raw[3];
  require(keys.insert(a.key).second&&pointer(a.component),"registry duplicate/component");
  a.entity=r.get<U>(a.component+0x40);a.actor=r.ptr(a.component+0x378);require(r.get<uint32_t>(a.actor+0xC)==a.key,"registry serial");
  if(pointer(a.entity)&&(r.get<uint8_t>(a.entity+0x130)&0x10)){
   try{if(castBase(r,a.entity)==a.entity)result.push_back(a);}catch(const std::exception&){}
  }
  node=raw[0];
 }
 return result;
}
struct Bone{V3 model;int16_t parent=-1;};
void validateBones(const std::vector<Bone>& bones){
 require(!bones.empty()&&bones.size()<=512,"bone count");int roots=0;
 for(size_t i=0;i<bones.size();++i){
  auto b=bones[i];require(std::isfinite(b.model.x)&&std::isfinite(b.model.y)&&std::isfinite(b.model.z)&&std::abs(b.model.x)<100&&std::abs(b.model.y)<100&&std::abs(b.model.z)<100,"bone position");
  require(b.parent>=-1&&b.parent<int(bones.size())&&b.parent!=int(i),"bone parent");if(b.parent==-1)++roots;
  int index=int(i);for(size_t depth=0;index>=0;++depth){require(depth<bones.size(),"bone cycle");index=bones[index].parent;}
 }
 require(roots>=1,"bone root");
}
std::vector<Bone> skeleton(Reader& r,const Actor& a){
 require(r.get<U>(a.component+0xE8)==a.actor,"skeleton component alias");
 U resource=r.ptr(a.actor+0xD8),begin=r.ptr(resource+0x10),end=r.get<U>(resource+0x18);
 require(end>begin&&(end-begin)%0xA0==0&&(end-begin)/0xA0<=512,"pose bounds");
 auto raw=r.vec<unsigned char>(begin,end-begin);std::vector<Bone> out((end-begin)/0xA0);
 for(size_t i=0;i<out.size();++i){std::memcpy(&out[i].model,raw.data()+i*0xA0+0x54,12);std::memcpy(&out[i].parent,raw.data()+i*0xA0+0x94,2);}
 validateBones(out);
 require(r.get<U>(a.actor+0xD8)==resource&&r.get<U>(resource+0x10)==begin&&r.get<U>(resource+0x18)==end,"pose changed allocation");return out;
}

struct Settings{
 std::atomic<bool> aim{true},esp{true},boxes{true},bones{true},tracers{true},labels{true},running{true};
 std::atomic<int> radius{500},speed{300};
} settings;
fs::path appDir;
void atomicFile(const fs::path& path,const std::string& data){
 auto tmp=path;tmp+=L".tmp";{std::ofstream f(tmp,std::ios::binary|std::ios::trunc);if(!f)return;f<<data;}
 MoveFileExW(tmp.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);
}
std::string loadFile(const fs::path& p){std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
void saveSettings(){
 std::ostringstream o;o<<"{\"aim\":"<<settings.aim<<",\"esp\":"<<settings.esp<<",\"boxes\":"<<settings.boxes<<",\"skeleton\":"<<settings.bones<<",\"tracers\":"<<settings.tracers<<",\"labels\":"<<settings.labels<<",\"radius\":"<<settings.radius<<",\"speed\":"<<settings.speed<<"}\n";
 atomicFile(appDir/L"settings.json",o.str());
}
bool readBool(const std::string& s,const char* k,bool fallback){auto p=s.find(std::string("\"")+k+"\"");if(p==s.npos)return fallback;p=s.find(':',p);if(p==s.npos)return fallback;p=s.find_first_not_of(" \t\r\n",p+1);if(s.compare(p,4,"true")==0||s.compare(p,1,"1")==0)return true;if(s.compare(p,5,"false")==0||s.compare(p,1,"0")==0)return false;return fallback;}
void loadSettings(){
 auto s=loadFile(appDir/L"settings.json");settings.aim=readBool(s,"aim",true);settings.esp=readBool(s,"esp",true);settings.boxes=readBool(s,"boxes",true);settings.bones=readBool(s,"skeleton",true);settings.tracers=readBool(s,"tracers",true);settings.labels=readBool(s,"labels",true);
 auto readInt=[&](const char* k,int fallback,int maximum){try{auto p=s.find(std::string("\"")+k+"\"");if(p==s.npos)return fallback;p=s.find(':',p);int n=std::stoi(s.substr(p+1));return n>=1&&n<=maximum?n:fallback;}catch(...){return fallback;}};
 settings.radius=readInt("radius",500,4096);settings.speed=readInt("speed",300,1000);
}
struct Calibration{double gx=0,gy=0,fov=0;int width=0,height=0;bool valid=false;};
Calibration calibration(){
 auto s=loadFile(appDir/L"calibration.json");Calibration c;
 require(s.find("CALIBRATED")!=s.npos,"calibration status missing");
 auto number=[&](const char* name){auto p=s.find(std::string("\"")+name+"\"");require(p!=s.npos,"calibration field");p=s.find(':',p);return std::stod(s.substr(p+1));};
 auto p=s.find("\"counts_per_pixel\"");require(p!=s.npos,"calibration gains");p=s.find('[',p);size_t consumed=0;c.gx=std::stod(s.substr(p+1),&consumed);p=s.find(',',p+1+consumed);c.gy=std::stod(s.substr(p+1));
 c.fov=number("field_of_view");c.width=int(number("width"));c.height=int(number("height"));
 require(std::isfinite(c.gx)&&std::isfinite(c.gy)&&c.gx>0&&c.gx<100&&c.gy>0&&c.gy<100&&c.fov>1&&c.fov<179&&c.width>0&&c.height>0,"invalid calibration");c.valid=true;return c;
}

std::string hashFile(const fs::path& p){
 BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;
 require(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0,"SHA256 provider");
 struct Clean{BCRYPT_ALG_HANDLE& a;BCRYPT_HASH_HANDLE& h;~Clean(){if(h)BCryptDestroyHash(h);if(a)BCryptCloseAlgorithmProvider(a,0);}}clean{alg,hash};
 DWORD len=0,got=0;require(BCryptGetProperty(alg,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&len),4,&got,0)>=0,"SHA256 length");
 std::vector<unsigned char> state(len);require(BCryptCreateHash(alg,&hash,state.data(),len,nullptr,0,0)>=0,"SHA256 create");
 std::ifstream f(p,std::ios::binary);require(bool(f),"game file unavailable");std::array<char,65536> b;
 while(f){f.read(b.data(),b.size());auto n=f.gcount();if(n)require(BCryptHashData(hash,reinterpret_cast<PUCHAR>(b.data()),ULONG(n),0)>=0,"SHA256 update");}
 require(f.eof(),"game file read error");std::array<unsigned char,32> digest;require(BCryptFinishHash(hash,digest.data(),32,0)>=0,"SHA256 finish");
 std::ostringstream o;for(auto c:digest)o<<std::hex<<std::setw(2)<<std::setfill('0')<<int(c);return o.str();
}
struct Game{DWORD pid=0;U base=0;fs::path path;HWND window=nullptr;};
BOOL CALLBACK findWindow(HWND h,LPARAM param){auto& g=*reinterpret_cast<Game*>(param);DWORD pid=0;GetWindowThreadProcessId(h,&pid);if(pid==g.pid&&IsWindowVisible(h)&&!GetWindow(h,GW_OWNER)){g.window=h;return FALSE;}return TRUE;}
Game findGame(){
 Game g;Handle snap(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0));require(snap.h!=INVALID_HANDLE_VALUE,"process snapshot");PROCESSENTRY32W e{};e.dwSize=sizeof(e);
 if(Process32FirstW(snap.h,&e))do{if(!_wcsicmp(e.szExeFile,L"BloodStrike.exe")){require(g.pid==0,"multiple game processes");g.pid=e.th32ProcessID;}}while(Process32NextW(snap.h,&e));
 require(g.pid!=0,"BloodStrike.exe is not running");Handle mods(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,g.pid));require(mods.h!=INVALID_HANDLE_VALUE,"module snapshot");
 MODULEENTRY32W m{};m.dwSize=sizeof(m);if(Module32FirstW(mods.h,&m))do{if(!_wcsicmp(m.szModule,L"BloodStrike.exe")){g.base=reinterpret_cast<U>(m.modBaseAddr);g.path=m.szExePath;require(m.modBaseSize==IMAGE_SIZE,"unsupported image size");break;}}while(Module32NextW(mods.h,&m));
 require(g.base!=0,"game module absent");EnumWindows(findWindow,reinterpret_cast<LPARAM>(&g));require(g.window!=nullptr,"game window absent");return g;
}

// A complete transparent frame is submitted once with UpdateLayeredWindow; no front-buffer BitBlt.
struct Surface{
 HWND hwnd=nullptr;HDC dc=nullptr;HBITMAP bitmap=nullptr;HGDIOBJ oldBitmap=nullptr;void* pixels=nullptr;int width=0,height=0;HFONT font=nullptr;
 std::map<std::pair<COLORREF,int>,HPEN> pens;
 ~Surface(){reset();for(auto entry:pens)DeleteObject(entry.second);if(font)DeleteObject(font);if(hwnd)DestroyWindow(hwnd);}
 void reset(){if(dc&&oldBitmap)SelectObject(dc,oldBitmap);if(bitmap)DeleteObject(bitmap);if(dc)DeleteDC(dc);dc=nullptr;bitmap=nullptr;pixels=nullptr;oldBitmap=nullptr;}
 void init(HINSTANCE instance){
  WNDCLASSW wc{};wc.lpfnWndProc=DefWindowProcW;wc.hInstance=instance;wc.lpszClassName=L"Rook.Native.Overlay";RegisterClassW(&wc);
  hwnd=CreateWindowExW(WS_EX_LAYERED|WS_EX_TRANSPARENT|WS_EX_TOPMOST|WS_EX_NOACTIVATE|WS_EX_TOOLWINDOW,wc.lpszClassName,L"Rook Overlay",WS_POPUP,0,0,1,1,nullptr,nullptr,instance,nullptr);require(hwnd!=nullptr,"overlay window");
  font=CreateFontW(-15,0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,NONANTIALIASED_QUALITY,DEFAULT_PITCH,L"Segoe UI");require(font!=nullptr,"overlay font");
 }
 void begin(int w,int h){
  if(w!=width||h!=height||!dc){reset();width=w;height=h;dc=CreateCompatibleDC(nullptr);require(dc!=nullptr,"overlay DC");BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=w;info.bmiHeader.biHeight=-h;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&pixels,nullptr,0);require(bitmap!=nullptr,"overlay DIB");oldBitmap=SelectObject(dc,bitmap);}
  std::memset(pixels,0,size_t(w)*h*4);SetBkMode(dc,TRANSPARENT);SelectObject(dc,font);
 }
 void line(P2 a,P2 b,COLORREF color,int thick=1){if(!a.front||!b.front)return;auto key=std::pair{color,thick};auto it=pens.find(key);if(it==pens.end()){HPEN pen=CreatePen(PS_SOLID,thick,color);require(pen!=nullptr,"overlay pen");it=pens.emplace(key,pen).first;}auto old=SelectObject(dc,it->second);MoveToEx(dc,int(std::lround(a.x)),int(std::lround(a.y)),nullptr);LineTo(dc,int(std::lround(b.x)),int(std::lround(b.y)));SelectObject(dc,old);}
 void rect(float l,float t,float rr,float bb,COLORREF color){line({l,t,true},{rr,t,true},color);line({rr,t,true},{rr,bb,true},color);line({rr,bb,true},{l,bb,true},color);line({l,bb,true},{l,t,true},color);}
 void text(float x,float y,const std::wstring& s,COLORREF color){SetTextColor(dc,RGB(1,1,1));TextOutW(dc,int(x)+1,int(y)+1,s.c_str(),int(s.size()));SetTextColor(dc,color);TextOutW(dc,int(x),int(y),s.c_str(),int(s.size()));}
 void present(POINT origin){
  // GDI writes RGB but not alpha. Color-key composition preserves crisp opaque strokes.
  SIZE sz{width,height};POINT src{0,0};require(UpdateLayeredWindow(hwnd,nullptr,&origin,&sz,dc,&src,RGB(0,0,0),nullptr,ULW_COLORKEY)!=0,"overlay present");
  SetWindowPos(hwnd,HWND_TOPMOST,origin.x,origin.y,width,height,SWP_NOACTIVATE|SWP_SHOWWINDOW);
 }
 void hide(){if(hwnd)ShowWindow(hwnd,SW_HIDE);}
};

struct Projected{
 Actor actor;P2 aim,feet;std::vector<P2> points;std::vector<Bone> bones;float l=0,t=0,r=0,b=0;bool box=false;
};
Projected geometry(Reader& r,const Camera& c,const Actor& a){
 require(identity(r,a),"actor association expired");Pose p=pose(r,a.entity);require(p.anchor==c.anchor,"coordinate anchors differ");Projected out;out.actor=a;
 out.feet=c.project(p.world({0,0,0}));out.aim=c.project(p.world({0,1.55f,0}));
 try{out.bones=skeleton(r,a);for(auto bone:out.bones)out.points.push_back(c.project(p.world(bone.model)));}catch(const std::exception&){out.bones.clear();out.points.clear();}
 std::vector<P2> good;
 for(size_t i=0;i<out.points.size();++i){auto pt=out.points[i];auto v=out.bones[i].model;
  // Bound the humanoid, excluding distant weapon/accessory attachment points.
  if(pt.front&&v.y>=-0.2f&&v.y<=2.4f&&std::hypot(v.x,v.z)<=1.25f)good.push_back(pt);
 }
 if(good.size()>=5){out.l=out.r=good[0].x;out.t=out.b=good[0].y;for(auto pt:good){out.l=std::min(out.l,pt.x);out.r=std::max(out.r,pt.x);out.t=std::min(out.t,pt.y);out.b=std::max(out.b,pt.y);}float pad=std::max(2.f,(out.b-out.t)*.04f);out.l-=pad;out.r+=pad;out.t-=pad;out.b+=pad;out.box=out.b-out.t>3;}
 else{auto top=c.project(p.world({0,1.8f,0}));if(top.front&&out.feet.front){float h=std::abs(out.feet.y-top.y);out.l=out.feet.x-h*.22f;out.r=out.feet.x+h*.22f;out.t=std::min(top.y,out.feet.y);out.b=std::max(top.y,out.feet.y);out.box=h>3;}}
 require(identity(r,a),"actor association changed during pose");return out;
}
int drawActor(Surface& s,const Projected& a){
 COLORREF red=RGB(255,90,80);int primitives=0;
 if(settings.bones){for(size_t i=0;i<a.bones.size();++i){int parent=a.bones[i].parent;if(parent<0)continue;V3 x=a.bones[i].model,y=a.bones[parent].model;float distance=std::hypot(x.x-y.x,x.y-y.y,x.z-y.z);if(distance<.015f||distance>1.5f)continue;if(a.points[i].front&&a.points[parent].front){s.line(a.points[i],a.points[parent],RGB(255,220,130));++primitives;}}}
 if(settings.boxes&&a.box){s.rect(a.l,a.t,a.r,a.b,red);primitives+=4;}
 if(settings.tracers&&a.feet.front){s.line({s.width*.5f,float(s.height-1),true},a.feet,RGB(230,100,90));++primitives;}
 if(settings.labels&&a.box){s.text(a.l,a.t-18,L"HP "+std::to_wstring(int(a.actor.hp)),red);++primitives;}
 return primitives;
}
std::string escaped(const std::string& s){std::string out;for(unsigned char c:s){if(c=='"'||c=='\\'){out+='\\';out+=char(c);}else if(c>=32)out+=char(c);}return out;}
std::mutex statusMutex;std::wstring statusText=L"Iniciando...";
HWND menuWindow=nullptr,statusWindow=nullptr;std::atomic<bool> workerDone{false};
void status(const std::string& s){std::lock_guard lock(statusMutex);statusText.assign(s.begin(),s.end());}
struct Options{bool probe=false;int seconds=0;};
void worker(Options options){
 U frames=0,inputPackets=0,errors=0;std::string lastError,aimReason="inactive";Game game;Clock::time_point started=Clock::now(),lastReport=started;Actor locked{};int validFrames=0;
 auto report=[&](int candidates,int enemies,int primitives,int boneCount,double ms,double fps){
  std::ostringstream o;o<<"{\n\"runtime\":\"native-cpp\",\"pid\":"<<game.pid<<",\"frames\":"<<frames<<",\"valid_frames\":"<<validFrames<<",\"errors\":"<<errors<<",\"actors\":"<<candidates<<",\"opponents\":"<<enemies<<",\"draw_primitives\":"<<primitives<<",\"bone_count\":"<<boneCount<<",\"frame_ms\":"<<ms<<",\"fps\":"<<fps<<",\"input_packets\":"<<inputPackets<<",\"aim_reason\":\""<<escaped(aimReason)<<"\",\"last_error\":\""<<escaped(lastError)<<"\",\"aim\":"<<settings.aim<<",\"esp\":"<<settings.esp<<",\"boxes\":"<<settings.boxes<<",\"skeleton\":"<<settings.bones<<",\"tracers\":"<<settings.tracers<<",\"labels\":"<<settings.labels<<",\"finished\":"<<workerDone<<"\n}\n";
  atomicFile(appDir/(options.probe?L"native-probe.json":L"native-session.json"),o.str());
 };
 try{
  game=findGame();status("Verificando build...");require(hashFile(game.path)==SAMPLE,"unsupported game SHA256");
  Handle process(OpenProcess(PROCESS_VM_READ|PROCESS_QUERY_LIMITED_INFORMATION,FALSE,game.pid));require(process.h!=nullptr,"OpenProcess denied");
  Calibration cal;try{cal=calibration();}catch(const std::exception& e){lastError=e.what();}
  Surface overlay;if(!options.probe)overlay.init(GetModuleHandleW(nullptr));
  auto fpsStart=Clock::now();int fpsFrames=0;double fps=0;int candidates=0,enemies=0,primitives=0,boneCount=0;
  while(settings.running){
   MSG pending;while(PeekMessageW(&pending,nullptr,0,0,PM_REMOVE)){TranslateMessage(&pending);DispatchMessageW(&pending);}
   auto frameStart=Clock::now();++frames;primitives=boneCount=0;std::string stage="process";
   try{
    DWORD exitCode=0;require(GetExitCodeProcess(process.h,&exitCode)&&exitCode==STILL_ACTIVE,"game process exited");
    Reader metadata(process.h,game.base);PyData py(metadata);stage="local player";U local=py.local();stage="local numeric map";Numeric ln(py,local);double localFaction=ln.get("faction");stage="registry";auto actors=registry(metadata);candidates=int(actors.size());std::vector<Actor> classified;
    std::string classificationError;
    for(auto a:actors){try{
     auto av=py.avatar(a.entity);a.host=av.host;if(a.host==local)continue;Numeric n(py,a.host);a.hp=n.get("server_hp");double life=n.get("combat_state");a.faction=n.get("faction");
     a.alive=life==0&&a.hp>0;a.enemy=localFaction<0||a.faction<0||localFaction!=a.faction;
     if(a.alive&&a.enemy)classified.push_back(a);
    }catch(const std::exception& e){classificationError=e.what();}}
    enemies=int(classified.size());
    // Metadata reads finish before geometry. No page cache survives into the current camera/pose sample.
    Reader fresh(process.h,game.base);fresh.cache=false;
    stage="current geometry";auto geometryStart=Clock::now();Camera c=camera(fresh);
    std::vector<Projected> projected;for(auto a:classified){try{projected.push_back(geometry(fresh,c,a));}catch(const std::exception&) {}}
    RECT rect{};POINT origin{0,0};require(GetClientRect(game.window,&rect)&&ClientToScreen(game.window,&origin),"game client geometry");
    int clientWidth=rect.right-rect.left,clientHeight=rect.bottom-rect.top;
    require(clientWidth>0&&clientHeight>0,"game minimized");
    bool focused=GetForegroundWindow()==game.window&&!IsIconic(game.window);
    bool held=(GetAsyncKeyState(VK_RBUTTON)&0x8000)!=0;
    bool eligible=settings.aim&&!options.probe&&focused&&held;
    if(!eligible){locked={};aimReason=options.probe?"probe_no_input":!settings.aim?"disabled":!focused?"game_not_focused":"hold_RMB";}
    else if(!cal.valid){locked={};aimReason="calibration_missing";}
    else if(std::abs(c.fov-cal.fov)>.6||c.width!=cal.width||c.height!=cal.height){locked={};aimReason="calibration_FOV_or_resolution_mismatch";}
    else if(std::chrono::duration<double,std::milli>(Clock::now()-frameStart).count()>100||std::chrono::duration<double,std::milli>(Clock::now()-geometryStart).count()>20){locked={};aimReason="stale_frame";}
    else{
     Projected* chosen=nullptr;double best=settings.radius.load()*settings.radius.load();
     for(auto& p:projected){if(!p.aim.inside)continue;double d=std::hypot(p.aim.x-c.width*.5,p.aim.y-c.height*.5);if(d>settings.radius)continue;if(locked.host&&same(locked,p.actor)){chosen=&p;break;}if(d*d<best){best=d*d;chosen=&p;}}
     if(!chosen){locked={};aimReason="no_target";}
     else{
      locked=chosen->actor;double ex=chosen->aim.x-c.width*.5,ey=chosen->aim.y-c.height*.5;
      if(std::hypot(ex,ey)<=.65)aimReason="inside_deadzone";
      else{
       double dx=ex*cal.gx,dy=ey*cal.gy,length=std::hypot(dx,dy),limit=settings.speed.load();if(length>limit){dx*=limit/length;dy*=limit/length;}
       INPUT input{};input.type=INPUT_MOUSE;input.mi.dx=LONG(dx);input.mi.dy=LONG(dy);input.mi.dwFlags=MOUSEEVENTF_MOVE;
       // Check focus, activation, identity and age again immediately before sending input.
       if(GetForegroundWindow()==game.window&&(GetAsyncKeyState(VK_RBUTTON)&0x8000)&&settings.aim&&identity(fresh,chosen->actor)&&std::chrono::duration<double,std::milli>(Clock::now()-geometryStart).count()<20){
        require(SendInput(1,&input,sizeof(input))==1,"SendInput failed");++inputPackets;aimReason="tracking";
       }else aimReason="input_recheck_failed";
      }
     }
    }
    if(!options.probe&&settings.esp&&focused){
     overlay.begin(clientWidth,clientHeight);float scaleX=float(clientWidth)/c.width,scaleY=float(clientHeight)/c.height;
     // Render pixels map to the current client rectangle (including DPI/resolution changes).
     for(auto a:projected){
      auto scale=[&](P2& p){p.x*=scaleX;p.y*=scaleY;};scale(a.feet);scale(a.aim);for(auto& p:a.points)scale(p);a.l*=scaleX;a.r*=scaleX;a.t*=scaleY;a.b*=scaleY;
      primitives+=drawActor(overlay,a);boneCount=std::max(boneCount,int(a.bones.size()));
     }
     overlay.present(origin);
    }else overlay.hide();
    if(options.probe)for(auto& p:projected)boneCount=std::max(boneCount,int(p.bones.size()));
    ++validFrames;++fpsFrames;auto now=Clock::now();double fpsElapsed=std::chrono::duration<double>(now-fpsStart).count();if(fpsElapsed>=1){fps=fpsFrames/fpsElapsed;fpsStart=now;fpsFrames=0;}
    double ms=std::chrono::duration<double,std::milli>(now-frameStart).count();
    if(now-lastReport>=std::chrono::seconds(1)||options.probe){
     if(classified.empty()&&!classificationError.empty())lastError=classificationError;else lastError.clear();
     report(candidates,enemies,primitives,boneCount,ms,fps);
     status("C++ | "+std::to_string(enemies)+" alvos | "+std::to_string(int(fps))+" FPS | "+aimReason);lastReport=now;
    }
   }catch(const std::exception& e){++errors;lastError=stage+": "+e.what();locked={};aimReason="read_failed";overlay.hide();status(lastError);if(Clock::now()-lastReport>=std::chrono::seconds(1)){report(candidates,enemies,0,0,0,fps);lastReport=Clock::now();}std::this_thread::sleep_for(std::chrono::milliseconds(40));}
   if(options.seconds>0&&Clock::now()-started>=std::chrono::seconds(options.seconds))break;
   auto target=frameStart+std::chrono::microseconds(8333);if(Clock::now()<target)std::this_thread::sleep_until(target);
  }
  workerDone=true;report(candidates,enemies,primitives,boneCount,0,fps);
 }catch(const std::exception& e){++errors;lastError=e.what();status(lastError);workerDone=true;report(0,0,0,0,0,0);}
 workerDone=true;
}

#include "menu.hpp"
void selfTest(){
 Camera c;c.width=1920;c.height=1080;c.sx=1;c.sy=1;c.view={1,0,0,0,1,0,0,0,1,0,0,0};
 auto center=c.project({0,0,-10});require(center.inside&&center.x==960&&center.y==540,"projection center");
 auto right=c.project({1,0,-10});require(std::abs(right.x-1056)<.001,"projection horizontal");
 auto up=c.project({0,1,-10});require(std::abs(up.y-486)<.001,"projection vertical");require(!c.project({0,0,10}).front,"behind camera rejection");
 c.view[9]=-2;require(c.project({2,0,-10}).x==960,"view translation");
 Pose p;p.m={1,0,0,0,1,0,0,0,1,10,20,30};auto w=p.world({1,2,3});require(w.x==11&&w.y==22&&w.z==33,"entity transform");
 validateBones({{{0,0,0},-1},{{0,1,0},0}});bool rejected=false;try{validateBones({{{0,0,0},1},{{0,1,0},0}});}catch(...){rejected=true;}require(rejected,"bone cycle rejection");
 rejected=false;try{validateBones({{{0,0,0},3}});}catch(...){rejected=true;}require(rejected,"bone out of range rejection");
 Actor a;a.key=1;a.host=4;Actor b=a;require(same(a,b),"sticky identity");b.key=2;require(!same(a,b),"serial changed");
 require(readBool("{\"aim\":false}","aim",true)==false&&readBool("{}","aim",true),"settings parser");
 require(escaped("a\"b\\c")=="a\\\"b\\\\c","JSON escaping");
 void* memory=VirtualAlloc(nullptr,65536,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);require(memory!=nullptr,"fixture allocation");
 struct Free{void* p;~Free(){VirtualFree(p,0,MEM_RELEASE);}}freeMemory{memory};
 U base=reinterpret_cast<U>(memory);
 auto put=[&]<class T>(size_t offset,T value){std::memcpy(static_cast<char*>(memory)+offset,&value,sizeof(value));};
 auto text=[&](size_t offset,const char* value){put(offset+8,base+0x7A16E10);put(offset+16,int64_t(std::strlen(value)));put(offset+32,uint32_t(0x64));std::memcpy(static_cast<char*>(memory)+offset+40,value,std::strlen(value)+1);};
 text(0x1000,"owner");text(0x1100,"model");
 put(0x1018,U(42));put(0x1118,U(77));
 put(0x2008,base+0x7A19900);put(0x2010,int64_t(2));put(0x2020,base+0x3000);put(0x2028,U(0));
 put(0x3008,uint8_t(3));put(0x3009,uint8_t(3));put(0x300A,uint8_t(1));put(0x3018,int64_t(2));
 std::memset(static_cast<char*>(memory)+0x3020,0xff,8);put(0x3022,int8_t(0));put(0x3025,int8_t(1));
 put(0x3028,base+0x1000);put(0x3030,U(0x12340000));put(0x3038,base+0x1100);put(0x3040,U(0x56780000));
 Reader reader(GetCurrentProcess(),base);PyData py(reader);auto d=py.dict(base+0x2000);
 require(d.at("owner")==0x12340000&&d.at("model")==0x56780000,"native combined dictionary read");
 require(py.dictItem(base+0x2000,"owner")==0x12340000&&py.dictItem(base+0x2000,"model")==0x56780000,"native hash dictionary lookup");
 put(0x3022,int8_t(-2));put(0x3024,int8_t(0));reader.pages.clear();require(py.dictItem(base+0x2000,"owner")==0x12340000,"native dummy bucket probing");
 put(0x300A,uint8_t(2));put(0x4000,uint8_t(2));put(0x4001,uint8_t(2));put(0x4002,uint8_t(1));put(0x4003,uint8_t(1));put(0x4008,U(0x11110000));put(0x4010,U(0x22220000));
 reader.pages.clear();PyData split(reader);auto sd=split.table(base+0x3000,base+0x4000);
 require(sd.at("owner")==0x11110000&&sd.at("model")==0x22220000,"native split dictionary read");
 reader.cache=false;put(0x3028,base+0x1000);put(0x3038,base+0x1100);put(0x5008,base+0x6000);put(0x6020,int64_t(48));put(0x60A8,uint32_t(0x214));put(0x6370,base+0x3000);
 put(0x5030,uint8_t(2));put(0x5031,uint8_t(2));put(0x5032,uint8_t(1));put(0x5033,uint8_t(1));put(0x5038,U(0xAAAA0000));put(0x5040,U(0xBBBB0000));
 PyData managed(reader);auto md=managed.instance(base+0x5000);require(md.at("owner")==0xAAAA0000&&md.at("model")==0xBBBB0000,"native inline dictionary read");
 bool failedRead=false;try{reader.get<U>(8);}catch(...){failedRead=true;}require(failedRead,"invalid memory rejection");
 atomicFile(appDir/L"self-test.json","{\"status\":\"PASS\",\"checks\":19,\"runtime\":\"native-cpp\"}\n");
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,LPWSTR,int){
 wchar_t exe[32768]{};GetModuleFileNameW(nullptr,exe,32768);appDir=fs::path(exe).parent_path();
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
 int argc=0;LPWSTR* argv=CommandLineToArgvW(GetCommandLineW(),&argc);Options options;bool test=false,preview=false;
 for(int i=1;i<argc;++i){if(!wcscmp(argv[i],L"--self-test"))test=true;if(!wcscmp(argv[i],L"--preview"))preview=true;if(!wcscmp(argv[i],L"--probe"))options.probe=true;if(!wcscmp(argv[i],L"--seconds")&&i+1<argc)options.seconds=_wtoi(argv[++i]);}LocalFree(argv);
 try{
  if(test){selfTest();return 0;}
  if(preview){loadSettings();renderDesignPreview();return 0;}
  if(!IsUserAnAdmin()){
   SHELLEXECUTEINFOW launch{};launch.cbSize=sizeof(launch);launch.fMask=SEE_MASK_NOCLOSEPROCESS;launch.lpVerb=L"runas";launch.lpFile=exe;
   // Rebuild only supported arguments; never splice the executable name into parameters.
   std::wstring args;if(options.probe)args=L"--probe ";if(options.seconds)args+=L"--seconds "+std::to_wstring(options.seconds);launch.lpParameters=args.c_str();launch.nShow=options.probe?SW_HIDE:SW_SHOWNORMAL;
   require(ShellExecuteExW(&launch)!=0,"administrator elevation cancelled");if(launch.hProcess)CloseHandle(launch.hProcess);return 0;
  }
  loadSettings();if(options.probe){worker(options);return 0;}
  BrandTypeface typeface;
  Handle singleton(CreateMutexW(nullptr,TRUE,L"Local\\RookNativeBloodStrike"));require(GetLastError()!=ERROR_ALREADY_EXISTS,"aeon is already running");
  WNDCLASSW wc{};wc.lpfnWndProc=menuProc;wc.hInstance=instance;wc.hCursor=LoadCursorW(nullptr,IDC_ARROW);wc.hbrBackground=reinterpret_cast<HBRUSH>(COLOR_WINDOW+1);wc.lpszClassName=L"Rook.Native.Menu";require(RegisterClassW(&wc)!=0,"menu class");
  HWND hwnd=CreateWindowExW(0,wc.lpszClassName,L"aeon",WS_POPUP|WS_MINIMIZEBOX|WS_CLIPCHILDREN,CW_USEDEFAULT,CW_USEDEFAULT,770,557,nullptr,nullptr,instance,nullptr);require(hwnd!=nullptr,"menu creation");
  ShowWindow(hwnd,SW_SHOW);std::thread live(worker,options);MSG msg;while(GetMessageW(&msg,nullptr,0,0)>0){if(!IsDialogMessageW(hwnd,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}settings.running=false;live.join();if(menuFont)DeleteObject(menuFont);if(brandFont)DeleteObject(brandFont);if(smallFont)DeleteObject(smallFont);return 0;
 }catch(const std::exception& e){atomicFile(appDir/L"native-error.json","{\"error\":\""+escaped(e.what())+"\"}\n");if(!options.probe&&!test)MessageBoxA(nullptr,e.what(),"aeon",MB_OK|MB_ICONERROR);return 1;}
}
