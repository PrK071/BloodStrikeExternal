# Python / tools/calibrate_aim.py / Python 3.12+ Windows x64 / selected Blood Strike training window
"""Measure ADS mouse counts against observed camera projection, then restore motion."""
import argparse
import ctypes as C
import math
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ExternalCore.build import ModuleIdentity,verify_sample
from ExternalCore.camera_capture import _camera_pass
from ExternalCore.screenpoint import project_screenpoint
from ExternalCore.snapshot import write_json
from ExternalCore.win32_memory import WindowsProcessMemory,find_module
from ExternalCore.win32_input import WindowsInput,INPUT,movement_packet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--hwnd',type=int,required=True)
    parser.add_argument('--sample',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    report=dict(status='RUNNING',pid=args.pid,hwnd=args.hwnd,events=[],gameplay_validated=False)
    write_json(args.output,report)
    source=WindowsInput()
    def focused():
        owner=C.c_uint32()
        if (not source.api.IsWindow(args.hwnd) or source.api.GetForegroundWindow()!=args.hwnd or
            not source.api.GetWindowThreadProcessId(args.hwnd,C.byref(owner)) or owner.value!=args.pid):
            raise RuntimeError('selected game window must remain foreground')
    def send(dx=0,dy=0,flags=1):
        focused()
        packet=movement_packet(dx,dy)
        packet.mi.dwFlags=flags
        if source.api.SendInput(1,C.byref(packet),C.sizeof(INPUT))!=1:
            raise OSError('SendInput did not insert calibration event')
        report['events'].append(dict(dx=dx,dy=dy,flags=flags))
        write_json(args.output,report)
    ads=False
    try:
        sample=verify_sample(args.sample)
        report['sample']=sample
        with WindowsProcessMemory(args.pid) as reader:
            if os.path.normcase(os.path.realpath(reader.image_path))!=os.path.normcase(sample['path']):
                raise ValueError('selected process path mismatch')
            mapped=find_module(args.pid,sample['path'])
            if mapped.size!=sample['image_size']:raise ValueError('module size mismatch')
            module=ModuleIdentity(mapped.base,mapped.size,sample['sha256'])
            focused()
            if source.api.GetAsyncKeyState(2)&0x8000:raise RuntimeError('release the right mouse button before calibration')
            send(flags=8);ads=True
            time.sleep(0.8)
            start=_camera_pass(reader,module)[0].camera
            b=start.basis
            forward=(b[2],b[5],b[8])
            length=math.sqrt(sum(value*value for value in forward))
            point=tuple(origin-10*axis/length for origin,axis in zip(start.origin,forward))
            reference=project_screenpoint(start,point)
            time.sleep(0.15)
            stable=_camera_pass(reader,module)[0].camera
            check=project_screenpoint(stable,point)
            if math.hypot(check.x-reference.x,check.y-reference.y)>2:
                raise RuntimeError('camera is moving before calibration')
            gains=[];measurements=[]
            for axis in (0,1):
                before=_camera_pass(reader,module)[0].camera
                baseline=project_screenpoint(before,point)
                delta=[0,0];delta[axis]=16
                moved=False
                try:
                    send(*delta);moved=True
                    time.sleep(0.2)
                    after=_camera_pass(reader,module)[0].camera
                    projected=project_screenpoint(after,point)
                    primary=(projected.x-baseline.x,projected.y-baseline.y)[axis]
                    secondary=(projected.y-baseline.y,projected.x-baseline.x)[axis]
                    gain=-16/primary if abs(primary)>0.2 else float('nan')
                    if (not math.isfinite(gain) or not 0<gain<10000 or
                        abs(secondary)>max(2,abs(primary)*0.2) or abs(after.field_of_view-before.field_of_view)>0.05):
                        raise RuntimeError('camera response does not support independent positive gains')
                    gains.append(gain)
                    measurements.append(dict(axis=axis,counts=16,pixel_change=primary,cross_axis_change=secondary))
                finally:
                    if moved:
                        send(-delta[0],-delta[1])
                        time.sleep(0.2)
            restored=_camera_pass(reader,module)[0].camera
            final=project_screenpoint(restored,point)
            restore_error=math.hypot(final.x-reference.x,final.y-reference.y)
            if restore_error>2:raise RuntimeError('camera did not return within two projected pixels')
            report.update(status='CALIBRATED',counts_per_pixel=gains,
                field_of_view=start.field_of_view,width=start.width,height=start.height,
                measurements=measurements,restore_error_px=restore_error,
                calibration_mode='ADS',input_dispatched=True,
                limitation='Measured camera response; body target alignment and full aimbot remain unverified.')
    except Exception as exc:
        report.update(status='ERROR',error_type=type(exc).__name__,error=str(exc))
    finally:
        if ads:
            packet=movement_packet(0,0);packet.mi.dwFlags=16
            released=source.api.SendInput(1,C.byref(packet),C.sizeof(INPUT))==1
            report['ads_released']=released
            if not released:report.update(status='ERROR',error='ADS release failed')
        report['input_dispatched']=bool(report['events'])
        write_json(args.output,report)
    return report['status']!='CALIBRATED'


if __name__=='__main__':raise SystemExit(main())
