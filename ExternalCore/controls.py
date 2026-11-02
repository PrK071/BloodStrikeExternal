# Python / ExternalCore/controls.py / Python 3.12+ / live menu state and projected ESP primitives
from threading import Lock
from .scene import Category,observation_id
from .screenpoint import project_screenpoint


class LiveControls:
    def __init__(self):
        self._lock=Lock()
        self._values=dict(esp=True,aim=True,boxes=True,tracers=True,labels=True,skeleton=True)
    def snapshot(self):
        with self._lock:return dict(self._values)
    def set(self,name,value):
        if name not in self._values or type(value) is not bool:raise ValueError('invalid live control')
        with self._lock:self._values[name]=value


def render_controls(frame,options,*,reader=None):
    if not options['esp']:return ()
    if frame.render_status!='fresh':
        return (dict(kind='text',x=12,y=12,text='Aguardando quadro atual',color=[255,150,60]),)
    scene=frame.scene
    commands=[]
    records={observation_id(record):record for record in frame.capture.registry.records}
    color=[255,75,75]
    for actor in scene.actors:
        if actor.classification.category is not Category.OPPONENT or not actor.point.inside_viewport:continue
        record=records[actor.observation]
        foot=project_screenpoint(frame.capture.camera.camera,record.position.local_translation)
        if not foot.in_front:continue
        x,y=round(actor.point.x),round(actor.point.y)
        bottom=round(foot.y)
        height=abs(bottom-y)
        if abs(foot.x)>scene.width*3 or abs(foot.y)>scene.height*3 or height>scene.height*3:
            continue
        # A screen-space framing box from the projected model root and upper
        # point. It is not a recovered hitbox/AABB or a skeletal bone chain.
        top=round(min(y,bottom)-height*0.08)
        half=max(5,round(height*0.23))
        left,right=x-half,x+half
        bone_commands=()
        if reader is not None and (options['skeleton'] or options['boxes']):
            from .skeleton import skeleton_commands
            try:bone_commands=skeleton_commands(reader,record,frame.capture.camera.camera)
            except (OSError,ValueError):pass
        if bone_commands:
            xs=[command[key] for command in bone_commands for key in ('x1','x2')]
            ys=[command[key] for command in bone_commands for key in ('y1','y2')]
            pose_height=max(ys)-min(ys)
            if 2<=pose_height<=scene.height*3 and max(map(abs,xs))<=scene.width*3:
                padding=max(3,round(pose_height*0.05))
                left,right=min(xs)-padding,max(xs)+padding
                top,bottom=min(ys)-padding,max(ys)+padding
        if options['boxes']:
            for x1,y1,x2,y2 in ((left,top,right,top),(right,top,right,bottom),
                                  (right,bottom,left,bottom),(left,bottom,left,top)):
                commands.append(dict(kind='line',x1=x1,y1=y1,x2=x2,y2=y2,color=color,width=1))
        if options['tracers']:
            commands.append(dict(kind='line',x1=scene.width//2,y1=scene.height-1,
                x2=round(foot.x),y2=bottom,color=[210,210,210],width=1))
        commands.append(dict(kind='circle',x=x,y=y,radius=3,color=color,width=1))
        if options['skeleton']:commands.extend(bone_commands)
        if options['labels']:
            hp=next((fact.value for fact in actor.classification.facts.values if fact.name=='server_hp'),None) if actor.classification.facts else None
            text=f'#{actor.observation.key}' + (f'  HP {hp:g}' if hp is not None else '')
            commands.append(dict(kind='text',x=left,y=top-17,text=text,color=color))
    return tuple(commands)
