# Python / tools/diagnose_live_frame.py / Python 3.12+ Windows x64 / selected Blood Strike build
"""Compare independent registry observations without asserting a coherent frame."""
import argparse
from pathlib import Path
import os
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ExternalCore.build import ModuleIdentity, verify_sample
from ExternalCore.registry import _read_pass
from ExternalCore.snapshot import write_json
from ExternalCore.win32_memory import WindowsProcessMemory, find_module
from ExternalCore.python_owner import DataReader
from ExternalCore.python_runtime import local_player
from ExternalCore.python_runtime import HEAD_RVA, INTERP_MODULES, INTERP_NEXT
from ExternalCore.python_runtime import find_module as find_python_module
import struct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--sample', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = dict(status='RUNNING', gameplay_validated=False, input_dispatched=False)
    write_json(args.output, report)
    try:
        sample = verify_sample(args.sample)
        with WindowsProcessMemory(args.pid) as reader:
            if os.path.normcase(os.path.realpath(reader.image_path)) != os.path.normcase(sample['path']):
                raise ValueError('process path mismatch')
            selected = find_module(args.pid, sample['path'])
            if selected.size != sample['image_size']:
                raise ValueError('module size mismatch')
            module = ModuleIdentity(selected.base, selected.size, sample['sha256'])
            start = time.perf_counter_ns()
            first = _read_pass(reader, module, 10000)
            middle = time.perf_counter_ns()
            second = _read_pass(reader, module, 10000)
            end = time.perf_counter_ns()
            differences = []
            for index, (left, right) in enumerate(zip(first.observations, second.observations)):
                if left != right:
                    item = dict(index=index, first_address=hex(left[0]), second_address=hex(right[0]),
                                first_size=len(left[1]), second_size=len(right[1]))
                    if left[0] == right[0] and len(left[1]) == len(right[1]):
                        item['changed_offsets'] = [hex(i) for i, (a,b) in enumerate(zip(left[1],right[1])) if a != b]
                    differences.append(item)
            report.update(status='OBSERVED', module=module, pid=args.pid,
                first_duration_ms=(middle-start)/1e6, second_duration_ms=(end-middle)/1e6,
                first_reads=len(first.observations), second_reads=len(second.observations),
                first_records=first.records, second_records=second.records,
                differences=differences,
                observations_equal=first.observations == second.observations,
                limitation='Independent sequential observations; no coherent frame or gameplay classification asserted.')
            models=[]
            for record in second.records:
                info=dict(key=record.key)
                data=DataReader(reader,module)
                try:
                    wrapper=data.wrapper(record.parent)
                    attrs=data.instance_dict(wrapper)
                    info.update(wrapper=hex(wrapper), attributes={k:hex(v) for k,v in attrs.items()})
                    if attrs.get('name'):
                        try: info['name']=data.ascii(attrs['name'])
                        except ValueError: pass
                    if attrs.get('owner'):
                        owner=attrs['owner']
                        try:
                            info['direct_owner_attributes']={k:hex(v) for k,v in data.instance_dict(owner).items()}
                            model=data.instance_dict(owner).get('model')
                            if model:
                                info['primary_model_attributes']={k:hex(v) for k,v in data.instance_dict(model).items() if k in ('model','owner','entity','area','instance')}
                                info['primary_model_mro']=[dict(name=data.c_string(struct.unpack_from('<Q',data.type_object(cls),24)[0]),
                                    module=data.ascii(data.class_dict(cls)['__module__']) if data.class_dict(cls).get('__module__') else None)
                                    for cls in data.mro(model)]
                            info['host_native_bridge_bytes']=data.read(owner+0x20,24).hex()
                            try:
                                bridge=data.pointer(owner+0x20)
                                area=data.pointer(bridge+0x10)
                                info['native_area']=hex(area)
                                area_bridge=data.pointer(area+0x20)
                                native_area=data.pointer(area_bridge)
                                host_bridge=data.pointer(native_area+0x38)
                                info['area_chain']=dict(host_bridge=hex(bridge),area_bridge=hex(area_bridge),
                                    native_area=hex(native_area),native_host_bridge=hex(host_bridge),
                                    host_at_bridge=hex(data.u64(host_bridge)),
                                    host_plus20=hex(data.u64(data.pointer(host_bridge)+0x20)),
                                    bridge_plus10=hex(data.u64(host_bridge+0x10)))
                                info['reverse_area_host']=hex(data.area_host(area))
                            except Exception as exc: info['native_area_error']=str(exc)
                            info['direct_owner_mro']=[dict(name=data.c_string(struct.unpack_from('<Q',data.type_object(cls),24)[0]),
                                module=data.ascii(data.class_dict(cls)['__module__']) if data.class_dict(cls).get('__module__') else None)
                                for cls in data.mro(owner)]
                        except Exception as exc: info['direct_owner_error']=str(exc)
                        try:
                            host=data.area_host(attrs['owner'])
                            info['owner_host']=hex(host)
                            info['host_attributes']={k:hex(v) for k,v in data.instance_dict(host).items()}
                            owner_types=[]
                            for cls in data.mro(host):
                                fields=data.class_dict(cls)
                                name=data.c_string(struct.unpack_from('<Q',data.type_object(cls),24)[0])
                                owner_types.append(dict(name=name,module=data.ascii(fields['__module__']) if fields.get('__module__') else None,
                                    player_marker=hex(fields['IsPlayerCombatAvatar']) if fields.get('IsPlayerCombatAvatar') else None))
                            info['owner_mro']=owner_types
                        except Exception as exc: info['owner_error']=str(exc)
                    instance=attrs.get('instance')
                    if instance:
                        types=[]
                        for cls in data.mro(instance):
                            fields=data.class_dict(cls)
                            name=data.c_string(struct.unpack_from('<Q',data.type_object(cls),24)[0])
                            module_name=data.ascii(fields['__module__']) if fields.get('__module__') else None
                            types.append(dict(name=name,module=module_name))
                        info['instance_mro']=types
                    info['player_avatar']=data.player_avatar(record.parent)
                except Exception as exc:
                    info.update(error_type=type(exc).__name__,error=str(exc))
                models.append(info)
            report['models']=models
            try:
                context,host,area=local_player(DataReader(reader,module))
                report['local_player']=dict(host=hex(host),area=hex(area),interpreter_id=context.interpreter_id)
            except Exception as exc:
                report['local_player']=dict(error_type=type(exc).__name__,error=str(exc))
            data=DataReader(reader,module,max_reads=200000)
            current=data.u64(module.address(HEAD_RVA,8))
            interpreters=[]
            seen=set()
            while current and current not in seen and len(seen)<64:
                seen.add(current)
                item=dict(address=hex(current))
                try:
                    modules=data.dictionary(data.pointer(current+INTERP_MODULES),max_entries=16384)
                    item['module_count']=len(modules)
                    item['selected_modules']={k:hex(v) for k,v in modules.items() if any(term in k.lower() for term in ('genv','combat','avatar','global','environment'))}
                except Exception as exc: item['error']=str(exc)
                interpreters.append(item)
                current=data.u64(current+INTERP_NEXT)
            report['interpreters']=interpreters
            try:
                from ExternalCore.camera_capture import capture_world
                from ExternalCore.python_owner import classify_player_models
                capture=capture_world(reader,module,allow_motion=True)
                classification_diagnostics={}
                classify_player_models(reader,module,capture,diagnostics=classification_diagnostics)
                report['classification_diagnostics']=classification_diagnostics
            except Exception as exc: report['classification_error']=str(exc)
            try:
                context=find_python_module(DataReader(reader,module),'gclient.gameplay.logic_base.entities.combat_avatar')
                genv=context.globals.get('genv')
                report['consumer_genv']=dict(pointer=hex(genv) if genv else None)
                if genv:
                    data=DataReader(reader,module)
                    report['consumer_genv']['type_name']=data.c_string(struct.unpack_from('<Q',data.type_object(data.u64(genv+8)),24)[0])
                    report['consumer_genv']['attributes']={k:hex(v) for k,v in data.instance_dict(genv).items()}
            except Exception as exc: report['consumer_genv_error']=str(exc)
            try:
                context=find_python_module(DataReader(reader,module),'builtins')
                genv=context.globals.get('genv')
                report['builtin_genv']=dict(pointer=hex(genv) if genv else None)
                if genv:
                    data=DataReader(reader,module)
                    report['builtin_genv']['type_name']=data.c_string(struct.unpack_from('<Q',data.type_object(data.u64(genv+8)),24)[0])
                    report['builtin_genv']['attributes']={k:hex(v) for k,v in data.instance_dict(genv).items()}
            except Exception as exc: report['builtin_genv_error']=str(exc)
    except Exception as exc:
        report.update(status='ERROR', error_type=type(exc).__name__, error=str(exc))
    write_json(args.output, report)
    return report['status'] == 'ERROR'


if __name__ == '__main__':
    raise SystemExit(main())
