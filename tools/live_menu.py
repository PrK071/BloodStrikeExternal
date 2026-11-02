# Python / tools/live_menu.py / Python 3.12+ Tk Windows x64 / live Blood Strike controls
import argparse
import ctypes as C
import json
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import ttk

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ExternalCore.controls import LiveControls
from ExternalCore.live import watch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--hwnd',type=int,required=True)
    parser.add_argument('--sample',type=Path,required=True)
    args=parser.parse_args()
    calibration=json.loads((ROOT/'calibration.json').read_text(encoding='utf-8-sig'))
    if calibration['status']!='CALIBRATED':raise ValueError('calibration required')
    controls=LiveControls();stop=threading.Event();result={}
    output=ROOT/'menu-session.json'
    try:
        prior=json.loads(output.read_text(encoding='utf-8')).get('controls',{})
        for name,value in prior.items():
            if name in controls.snapshot() and type(value) is bool:controls.set(name,value)
    except (OSError,ValueError):pass
    root=tk.Tk();root.title('Rook | Blood Strike');root.geometry('420x520')
    root.resizable(False,False);root.configure(bg='#111827');root.attributes('-topmost',True)
    style=ttk.Style(root);style.theme_use('clam')
    style.configure('TFrame',background='#111827')
    style.configure('TLabel',background='#111827',foreground='#e5e7eb',font=('Segoe UI',10))
    style.configure('TCheckbutton',background='#111827',foreground='#e5e7eb',font=('Segoe UI',11))
    style.map('TCheckbutton',background=[('active','#1f2937')],foreground=[('disabled','#6b7280')])
    panel=ttk.Frame(root,padding=24);panel.pack(fill='both',expand=True)
    ttk.Label(panel,text='ROOK / CONTROLES',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=(0,16))
    variables={}
    for name,label in (('aim','Aimbot — botão direito'),('esp','ESP'),('boxes','Caixas / Box'),
                       ('tracers','Antenas / linhas até o personagem'),('labels','Identificação e HP'),
                       ('skeleton','Skeleton / ossos articulados')):
        variable=tk.BooleanVar(value=controls.snapshot()[name]);variables[name]=variable
        ttk.Checkbutton(panel,text=label,variable=variable,
            command=lambda key=name,value=variable:controls.set(key,bool(value.get()))).pack(anchor='w',pady=5)
    ttk.Label(panel,text='Insert mostra/oculta o menu. F8 encerra.').pack(anchor='w',pady=(16,6))
    status=tk.StringVar(value='Iniciando leitura…')
    ttk.Label(panel,textvariable=status,wraplength=365).pack(anchor='w',pady=5)
    ttk.Button(panel,text='Ocultar menu (Insert)',command=root.withdraw).pack(fill='x',pady=8)
    def close():
        controls.set('aim',False);controls.set('esp',False);stop.set();root.destroy()
    ttk.Button(panel,text='Encerrar',command=close).pack(fill='x')
    root.protocol('WM_DELETE_WINDOW',close)
    def worker():
        try:
            result['frames']=watch(args.pid,args.sample,args.hwnd,output,seconds=3600,fps=60,show=True,
                allow_motion=True,max_age_ms=250,aim=True,counts_per_pixel=tuple(calibration['counts_per_pixel']),
                calibration_fov=calibration['field_of_view'],require_visible=False,aim_radius=500,
                tau_ms=0,max_step_counts=300,target_local_y=1.55,runtime_controls=controls,stop_event=stop)
        except Exception as exc:result['error']=str(exc)
        finally:result['done']=True
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    user=C.WinDLL('user32');user.GetAsyncKeyState.argtypes=[C.c_int];user.GetAsyncKeyState.restype=C.c_short
    held=False
    def tick():
        nonlocal held
        pressed=bool(user.GetAsyncKeyState(0x2D)&0x8000)
        if pressed and not held:
            if root.state()=='withdrawn':root.deiconify();root.lift()
            else:root.withdraw()
        held=pressed
        if result.get('done'):
            status.set('Encerrado.' if not result.get('error') else result['error'])
        else:
            try:
                frame=json.loads(output.read_text(encoding='utf-8'))
                bones=sum(command.get('color')==[80,240,220] for command in frame.get('rendered_commands',[]))
                status.set(f"Quadros: {frame.get('frames',0)} | Ossos: {bones}\nMira: {frame.get('input_status',frame.get('status','…'))}")
            except (OSError,ValueError):pass
        root.after(100,tick)
    root.after(100,tick);root.mainloop();stop.set();thread.join(timeout=2)


if __name__=='__main__':main()
