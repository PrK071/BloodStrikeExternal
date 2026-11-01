# Python | tests/state_fixture.py | Python 3.12+ | data-only native area/map and interpreter fixture.
import struct

from ExternalCore.memory import Segment,SnapshotMemory
from python_owner_fixture import python_fixture
from registry_fixture import patch


class StateFixture:
    def __init__(self):
        self.segments,self.module,self.a=python_fixture()
        self.cursor=max(s.address+len(s.data) for s in self.segments)+0x1000
    def alloc(self,size,fields=()):
        address=(self.cursor+7)&~7;self.cursor=address+max(size,8)
        raw=bytearray(max(size,8))
        for offset,fmt,values in fields:struct.pack_into(fmt,raw,offset,*values)
        self.segments.append(Segment(address,bytes(raw)));return address
    def set(self,address,fmt,*values):
        self.segments=patch(self.segments,address,fmt,*values)
    def ascii(self,value):
        raw=value.encode()+b'\0'
        return self.alloc(40+len(raw),[(0,'<QQq',[1,self.module.base+0x7A16E10,len(value)]),
            (32,'<I',[0x64]),(40,f'<{len(raw)}s',[raw])])
    def dictionary(self,values):
        count=len(values);size=8
        while size*2//3<count:size*=2
        width=1 if size<=128 else 2 if size<=32768 else 4
        index_bytes=size*width
        raw=bytearray(32+index_bytes+count*16)
        raw[8:11]=bytes([size.bit_length()-1,index_bytes.bit_length()-1,1])
        struct.pack_into('<q',raw,0,1);struct.pack_into('<qq',raw,16,size*2//3-count,count)
        raw[32:32+index_bytes]=b'\xff'*index_bytes
        for index,(name,value) in enumerate(values.items()):
            struct.pack_into('<'+{1:'b',2:'h',4:'i'}[width],raw,32+index*width,index)
            struct.pack_into('<QQ',raw,32+index_bytes+16*index,self.ascii(name),value)
        keys=self.alloc(len(raw),[(0,f'<{len(raw)}s',[bytes(raw)])])
        return self.alloc(48,[(0,'<QQqQQQ',[1,self.module.base+0x7A19900,count,0,keys,0])])
    def mro(self,items):
        return self.alloc(32+8*len(items),[(0,'<QQqQ',[1,self.module.base+0x7A18CE0,len(items),0]),
            (32,f'<{len(items)}Q',items)])
    def type(self,address,name,attrs=None,bases=(),dict_offset=16,basicsize=40):
        dictionary=self.dictionary(attrs or {})
        cname=self.alloc(len(name)+1,[(0,f'<{len(name)+1}s',[name.encode()+b'\0'])])
        raw=bytearray(352)
        struct.pack_into('<QQ',raw,0,1,self.module.base+0x7A15170)
        struct.pack_into('<Qq',raw,24,cname,basicsize);struct.pack_into('<I',raw,0xA8,0x1000)
        struct.pack_into('<Q',raw,0x108,dictionary);struct.pack_into('<q',raw,0x120,dict_offset)
        struct.pack_into('<Q',raw,0x158,self.mro([address,*bases]))
        self.segments.append(Segment(address,bytes(raw)));return address
    def memory(self):return SnapshotMemory(self.segments)
    def runtime(self,*,replay=None,main=None,extra_interpreter=False,extra_modules=0):
        values={'__name__':self.ascii('gclient.genv'),'player':self.a['host'],
                'main_player':self.a['host'] if main is None else main,
                'replay_player':self.module.base+0x7A0A150 if replay is None else replay}
        self.genv_dict=self.dictionary(values)
        self.genv=self.alloc(56,[(0,'<QQQ',[1,self.module.base+0x7A1B1F0,self.genv_dict])])
        modules={f'fixture_module_{i}':self.genv for i in range(extra_modules)}
        modules['gclient.genv']=self.genv
        self.modules=self.dictionary(modules)
        self.interpreter=self.alloc(0x1DF0,[(0x1C70,'<q',[0]),(0x1DE8,'<Q',[self.modules])])
        head=self.interpreter
        if extra_interpreter:
            head=self.alloc(0x1DF0,[(0x1C68,'<Q',[self.interpreter]),(0x1C70,'<q',[7]),
                                  (0x1DE8,'<Q',[self.dictionary({})])])
        self.segments.append(Segment(self.module.base+0x925F000,struct.pack('<8sQQ',b'xdebugpy',0x030E00F0,0)))
        self.segments.append(Segment(self.module.base+0x925F328,struct.pack('<Q',head)))
        return self
    def properties(self,values=None,*,kind='mixed'):
        values=values if values is not None else {'server_hp':('float',100.0),'faction':('int',1),
            'combat_state':('int',7),'combat_team_id':('int',3)}
        data_type=self.type(self.module.base+0x796A420,'asiocore.area_map')
        count=len(values);stride=16 if kind=='mixed' else 8
        payload=bytearray(count*stride);self.descriptors={}
        nodes=[]
        sentinel=self.alloc(32)
        for index,(name,(value_kind,value)) in enumerate(values.items()):
            descriptor=self.alloc(128,[(0,'<i',[index])]);self.descriptors[name]=descriptor
            node=self.alloc(32,[(8,'<QQQ',[nodes[-1] if nodes else sentinel,self.ascii(name),descriptor])]);nodes.append(node)
            struct.pack_into('<q' if value_kind=='int' else '<d',payload,index*stride,value)
            if kind=='mixed':payload[index*stride+8]=0 if value_kind=='int' else 1
        begin=self.alloc(len(payload),[(0,f'<{len(payload)}s',[bytes(payload)])]) if count else 0
        pairs=self.alloc(16*count,[(16*i+8,'<Q',[d]) for i,d in enumerate(self.descriptors.values())]) if count else 0
        schema=self.alloc(80,[(0x10,'<Q',[count]),(0x40,'<QQ',[pairs,pairs+16*count])])
        bucket=self.alloc(16,[(0,'<QQ',[nodes[0] if nodes else sentinel,nodes[-1] if nodes else sentinel])])
        index_map=self.alloc(72,[(0x18,'<Q',[sentinel]),(0x28,'<Q',[bucket]),(0x40,'<Q',[0])])
        meta=self.alloc(48,[(0x20,'<QQ',[index_map,schema])])
        state=self.alloc(32,[(0,'<Q',[meta])])
        vtable={'int':0x555BA60,'float':0x555BB58,'mixed':0x555BD48}[kind]
        storage=self.alloc(48,[(0,'<QQQ',[self.module.base+vtable,state,schema]),
                              (0x18,'<QQQ',[begin,begin+count*stride,begin+count*stride])])
        self.set(state+0x18,'<Q',storage)
        backing=self.alloc(40,[(0x10,'<Q',[state])])
        prop=self.alloc(40,[(0,'<QQ',[1,data_type]),(0x20,'<Q',[backing])])
        self.set(self.a['native_area']+0x1D8,'<Q',prop)
        self.a.update(schema=schema,storage=storage,values=begin,name_index=index_map,bucket=bucket,
                      property_node=nodes[-1] if nodes else 0,prop=prop)
        return self
