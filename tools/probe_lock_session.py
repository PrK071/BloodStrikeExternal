# Python / tools/probe_lock_session.py / Python 3.12+ Windows x64 / running Blood Strike training session
"""Hold ADS briefly and record the running application's own lock decisions."""
import ctypes as C
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ExternalCore.win32_input import WindowsInput,movement_packet,INPUT
from ExternalCore.snapshot import write_json


def main():
    session=Path(sys.argv[1]);output=Path(sys.argv[2])
    if output.exists():raise FileExistsError(output)
    initial=json.loads(session.read_text(encoding='utf-8'))
    pid=initial['pid'];hwnd=722308
    source=WindowsInput()
    report=dict(status='RUNNING',observations=[],baseline_packets=initial.get('packets_sent',0))
    pressed=False
    try:
        owner=C.c_uint32()
        if (source.api.GetForegroundWindow()!=hwnd or
            not source.api.GetWindowThreadProcessId(hwnd,C.byref(owner)) or owner.value!=pid):
            raise RuntimeError('selected training window is not foreground')
        if source.api.GetAsyncKeyState(2)&0x8000:raise RuntimeError('right mouse button already held')
        packet=movement_packet(0,0);packet.mi.dwFlags=8
        if source.api.SendInput(1,C.byref(packet),C.sizeof(INPUT))!=1:raise OSError('ADS press failed')
        pressed=True
        until=time.perf_counter()+5
        while time.perf_counter()<until:
            if source.api.GetForegroundWindow()!=hwnd:raise RuntimeError('game lost focus')
            current=json.loads(session.read_text(encoding='utf-8'))
            decision=current.get('frame',{}).get('aim',{})
            target=decision.get('target')
            report['observations'].append(dict(frame=current.get('frames'),input_status=current.get('input_status'),
                reason=decision.get('reason'),key=target.get('key') if target else None,
                packets_sent=current.get('packets_sent',0)))
            time.sleep(0.1)
        locks=[item for item in report['observations'] if item['key'] is not None and item['reason'] in ('planned','inside_deadzone')]
        report.update(status='LOCK_OBSERVED' if locks else 'NO_LOCK',
                      locked_keys=sorted({item['key'] for item in locks}),
                      movement_packets=max(item['packets_sent'] for item in report['observations'])-report['baseline_packets'])
    except Exception as exc:report.update(status='ERROR',error=str(exc))
    finally:
        if pressed:
            packet=movement_packet(0,0);packet.mi.dwFlags=16
            report['ads_released']=source.api.SendInput(1,C.byref(packet),C.sizeof(INPUT))==1
        write_json(output,report)
    return report['status']!='LOCK_OBSERVED'


if __name__=='__main__':raise SystemExit(main())
