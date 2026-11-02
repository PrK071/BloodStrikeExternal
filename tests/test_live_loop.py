# Python / tests/test_live_loop.py / Python 3.12+ unittest / observation-loop recovery with fake Win32 APIs
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch

from ExternalCore.entity_position import SAMPLE_SHA256
from ExternalCore.live import watch
from ExternalCore.registry import RegistryReadError


class ApiCall:
    def __init__(self,function): self.function=function
    def __call__(self,*args): return self.function(*args)


class LiveLoopTests(unittest.TestCase):
    def run_recovery(self,aim=False,dynamic_disable=False):
        calls,reports,windows,dispatches=[],[],[],[]
        controls=None
        if dynamic_disable:
            from ExternalCore.controls import LiveControls
            controls=LiveControls();controls.set('esp',False)
        def owner(hwnd,output):
            C.cast(output,C.POINTER(W.DWORD))[0]=999
            return 1
        def client(hwnd,output):
            rectangle=C.cast(output,C.POINTER(W.RECT)).contents
            rectangle.left=rectangle.top=0
            rectangle.right,rectangle.bottom=1920,1080
            return 1
        def corner(hwnd,output):
            point=C.cast(output,C.POINTER(W.POINT)).contents
            point.x=point.y=0
            return 1
        user=SimpleNamespace(**{name:ApiCall(function) for name,function in {
            'IsWindow':lambda hwnd:1,'GetWindowThreadProcessId':owner,
            'GetClientRect':client,'ClientToScreen':corner,'IsIconic':lambda hwnd:0,
            'GetForegroundWindow':lambda:1234,
            'GetAsyncKeyState':lambda key:0x8000 if (key==0x77 and len(calls)>=3) or (key==2 and aim) else 0,
            'SetThreadDpiAwarenessContext':lambda context:1}.items()})
        class Window:
            def __init__(self,*args,**kwargs):
                self.closed=False;self.draws=[];windows.append(self)
            def draw(self,commands):self.draws.append(commands)
            def pump(self):return True
            def close(self):self.closed=True
        decision=SimpleNamespace(target=None)
        frame=SimpleNamespace(scene=SimpleNamespace(width=1920,height=1080),commands=('current',),
                              aim=decision,render_status='fresh')
        def dispatch(decision,hwnd,*,expected_pid):
            dispatches.append((len(calls),decision,hwnd,expected_pid))
            return 'sent'
        input_source=SimpleNamespace(dispatch=dispatch)
        def acquire(*args,**kwargs):
            calls.append(kwargs)
            if dynamic_disable and len(calls)==1:controls.set('aim',False)
            if len(calls)==2:raise RegistryReadError('render camera source view copy differs')
            return frame
        sample_path=str(Path('fixture.exe').resolve())
        reader=MagicMock()
        reader.__enter__.return_value=reader
        reader.image_path=sample_path
        with patch('ExternalCore.live.C.WinDLL',return_value=user), \
             patch('ExternalCore.live.verify_sample',return_value=dict(path=sample_path,
                   image_size=0x9500000,sha256=SAMPLE_SHA256)), \
             patch('ExternalCore.win32_memory.WindowsProcessMemory',return_value=reader), \
             patch('ExternalCore.win32_memory.find_module',return_value=SimpleNamespace(base=0x180000000,size=0x9500000)), \
             patch('ExternalCore.win32_overlay.OverlayWindow',Window), \
             patch('ExternalCore.win32_input.WindowsInput',return_value=input_source), \
             patch('ExternalCore.live.process_frame',side_effect=acquire), \
             patch('ExternalCore.live.write_json',side_effect=lambda path,report:reports.append(report)), \
             patch('ExternalCore.live.time.sleep'):
            count=watch(999,Path(sample_path),1234,Path('unused.json'),seconds=10,show=True,
                allow_motion=True,aim=aim,counts_per_pixel=(1.0,1.0) if aim else None,
                runtime_controls=controls)
        self.assertEqual(count,2)
        self.assertEqual(len(windows),0 if dynamic_disable else 2)
        self.assertTrue(all(window.closed for window in windows))
        self.assertEqual(reports[1]['status'],'retrying_read')
        self.assertNotIn('frame',reports[1])
        self.assertEqual((reports[-1]['frames'],reports[-1]['attempts'],reports[-1]['read_failures']),(2,3,1))
        self.assertFalse(reports[1]['input_dispatched'])
        sends=aim and not dynamic_disable
        self.assertEqual(any(report['input_dispatched'] for report in reports),sends)
        self.assertEqual([call['active'] for call in calls],[True,False,False] if dynamic_disable else [aim]*3)
        self.assertEqual([item[0] for item in dispatches],[1,3] if sends else [])
        self.assertEqual(reports[-1]['packets_sent'],2 if sends else 0)

    def test_transient_read_closes_old_overlay_and_recovers_without_old_frame(self):
        self.run_recovery()

    def test_enabled_aim_dispatches_only_current_successful_frames(self):
        self.run_recovery(aim=True)

    def test_menu_disable_during_acquisition_prevents_pending_movement(self):
        self.run_recovery(aim=True,dynamic_disable=True)

    def test_aim_requires_calibration_before_any_sample_or_native_access(self):
        with patch('ExternalCore.live.verify_sample') as verify:
            with self.assertRaisesRegex(ValueError,'measured counts_per_pixel'):
                watch(999,Path('unused.exe'),1234,Path('unused.json'),aim=True)
        verify.assert_not_called()


if __name__=='__main__':unittest.main()
