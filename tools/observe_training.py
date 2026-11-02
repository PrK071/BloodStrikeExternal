# Python / tools/observe_training.py / Python 3.12+ Windows x64 / selected Blood Strike process
"""Collect bounded pipeline observations and classifier diagnostics without another image dump."""
import argparse
import os
from pathlib import Path
import sys
import time
import struct

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ExternalCore.build import ModuleIdentity, verify_sample
from ExternalCore.pipeline import process_frame
from ExternalCore.python_owner import classify_player_models
from ExternalCore.snapshot import write_json
from ExternalCore.win32_memory import WindowsProcessMemory,find_module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--sample',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--frames',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.frames<=30: parser.error('frames must be between 1 and 30')
    if args.output.exists(): raise FileExistsError(args.output)
    report=dict(status='RUNNING',frames=[],input_dispatched=False,gameplay_validated=False)
    write_json(args.output,report)
    try:
        sample=verify_sample(args.sample)
        with WindowsProcessMemory(args.pid) as reader:
            if os.path.normcase(os.path.realpath(reader.image_path))!=os.path.normcase(sample['path']):
                raise ValueError('process path mismatch')
            selected=find_module(args.pid,sample['path'])
            if selected.size!=sample['image_size']: raise ValueError('module size mismatch')
            module=ModuleIdentity(selected.base,selected.size,sample['sha256'])
            report['module']=module
            for index in range(args.frames):
                item=dict(index=index)
                diagnostics={}
                def classify(capture):
                    return classify_player_models(reader,module,capture,diagnostics=diagnostics)
                start=time.perf_counter_ns()
                try:
                    item['frame']=process_frame(reader,module,allow_motion=True,
                        require_render_input=True,classifier=classify)
                    source=item['frame'].capture.camera.camera_address
                    item['source_view_transform']=struct.unpack('<12f',reader.read(source+0x41C,48))
                    item['status']='OBSERVED'
                except Exception as exc:
                    item.update(status='ERROR',error_type=type(exc).__name__,error=str(exc))
                item['duration_ms']=(time.perf_counter_ns()-start)/1e6
                item['classification_diagnostics']=diagnostics
                report['frames'].append(item)
                write_json(args.output,report)
            report['status']='FINISHED'
    except Exception as exc:
        report.update(status='ERROR',error_type=type(exc).__name__,error=str(exc))
    write_json(args.output,report)
    return report['status']=='ERROR'


if __name__=='__main__': raise SystemExit(main())
