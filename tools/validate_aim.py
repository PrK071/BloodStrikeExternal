# Python / tools/validate_aim.py / Python 3.12+ Windows x64 / selected Blood Strike training process
"""Validate ADS convergence and one training shot against observed opponent HP."""
import argparse
import ctypes as C
import json
import math
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ExternalCore.aim import AimProfile
from ExternalCore.build import ModuleIdentity,verify_sample
from ExternalCore.pipeline import process_frame
from ExternalCore.snapshot import write_json
from ExternalCore.win32_input import WindowsInput,movement_packet,INPUT
from ExternalCore.win32_memory import WindowsProcessMemory,find_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pid',type=int,required=True)
    p.add_argument('--hwnd',type=int,required=True)
    p.add_argument('--sample',type=Path,required=True)
    p.add_argument('--calibration',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--target-local-y',type=float,default=1.0)
    p.add_argument('--tau-ms',type=float,default=50.0)
    p.add_argument('--max-step-counts',type=float,default=25.0)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    report=dict(status='RUNNING',observations=[],events=[],body_hit_validated=False,head_hit_validated=False)
    write_json(a.output,report)
    source=WindowsInput(max_age_ms=250)
    ads=False
    def focused():
        owner=C.c_uint32()
        if (source.api.GetForegroundWindow()!=a.hwnd or not source.api.IsWindow(a.hwnd) or
            not source.api.GetWindowThreadProcessId(a.hwnd,C.byref(owner)) or owner.value!=a.pid):
            raise RuntimeError('game window lost foreground or owner changed')
    def button(flags):
        focused()
        packet=movement_packet(0,0);packet.mi.dwFlags=flags
        if source.api.SendInput(1,C.byref(packet),C.sizeof(INPUT))!=1:raise OSError('button event not inserted')
        report['events'].append(flags)
    try:
        calibration=json.loads(a.calibration.read_text(encoding='utf-8-sig'))
        if calibration['status']!='CALIBRATED':raise ValueError('calibration is not successful')
        profile=AimProfile(counts_per_pixel=tuple(calibration['counts_per_pixel']),require_visible=False,
                           radius_px=500,max_age_ms=250,tau_ms=a.tau_ms,max_step_counts=a.max_step_counts,deadzone_px=1)
        sample=verify_sample(a.sample)
        with WindowsProcessMemory(a.pid) as reader:
            if os.path.normcase(os.path.realpath(reader.image_path))!=os.path.normcase(sample['path']):
                raise ValueError('process path mismatch')
            mapped=find_module(a.pid,sample['path'])
            if mapped.size!=sample['image_size']:raise ValueError('mapped image size mismatch')
            module=ModuleIdentity(mapped.base,mapped.size,sample['sha256'])
            report.update(pid=a.pid,module=module,model_local_probe_y=a.target_local_y)
            focused()
            if source.api.GetAsyncKeyState(2)&0x8000:raise RuntimeError('right mouse button already pressed')
            button(8);ads=True;time.sleep(0.8)
            locked=None;last=time.perf_counter();consecutive=0;before_hp=None
            deadline=time.perf_counter()+12
            while time.perf_counter()<deadline:
                focused()
                now=time.perf_counter()
                frame=process_frame(reader,module,profile=profile,active=True,dt_ms=min(1000,(now-last)*1000),
                                    allow_motion=True,require_render_input=True,target_local_y=a.target_local_y,
                                    locked_target=locked)
                last=now
                camera=frame.capture.camera.camera
                if (abs(camera.field_of_view-calibration['field_of_view'])>0.1 or
                    (camera.width,camera.height)!=(calibration['width'],calibration['height'])):
                    raise RuntimeError('camera differs from measured calibration')
                target=frame.aim.target
                if target is None:
                    report['observations'].append(dict(reason=frame.aim.reason))
                    continue
                if locked is None:locked=target
                if target!=locked:raise RuntimeError('selected opponent changed during convergence')
                actor=next(actor for actor in frame.scene.actors if actor.observation==locked)
                error=math.hypot(actor.point.x-frame.scene.width/2,actor.point.y-frame.scene.height/2)
                hp=next((fact.value for fact in actor.classification.facts.values if fact.name=='server_hp'),None)
                if hp is None:raise RuntimeError('opponent HP is not readable')
                state=source.dispatch(frame.aim,a.hwnd,expected_pid=a.pid)
                report['observations'].append(dict(key=locked.key,error_px=error,hp=hp,input_status=state))
                consecutive=consecutive+1 if error<=3 and frame.render_status=='fresh' else 0
                write_json(a.output,report)
                if consecutive>=2:
                    before_hp=hp;break
            if before_hp is None:raise RuntimeError('aim did not converge within the observation window')
            report.update(converged=True,target=locked,hp_before=before_hp)
            button(2)
            try:time.sleep(0.035)
            finally:button(4)
            time.sleep(0.3)
            deadline=time.perf_counter()+3
            while time.perf_counter()<deadline:
                frame=process_frame(reader,module,allow_motion=True,require_render_input=True,target_local_y=a.target_local_y)
                actor=next((actor for actor in frame.scene.actors if actor.observation==locked),None)
                if actor and actor.classification.facts:
                    hp=next((fact.value for fact in actor.classification.facts.values if fact.name=='server_hp'),None)
                    if hp is not None and hp<before_hp:
                        report.update(status='BODY_HIT_OBSERVED',hp_after=hp,damage=before_hp-hp,
                            body_hit_validated=True,
                            limitation='One training opponent and one local model-space point; no head bone or general combat validation.')
                        break
            else:raise RuntimeError('no opponent HP decrease observed after the training shot')
    except Exception as exc:
        report.update(status='ERROR',error_type=type(exc).__name__,error=str(exc))
    finally:
        if ads:
            packet=movement_packet(0,0);packet.mi.dwFlags=16
            report['ads_released']=source.api.SendInput(1,C.byref(packet),C.sizeof(INPUT))==1
        write_json(a.output,report)
    return not report['body_hit_validated']


if __name__=='__main__':raise SystemExit(main())
