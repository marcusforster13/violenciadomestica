import bpy
from mathutils import Vector
for o in bpy.data.objects:
    if o.type!="MESH": continue
    n=o.name.lower()
    if not any(k in n for k in ("parede","janela","porta","esquadria","vidro","piso","laje","calc","beiral")): continue
    bb=[o.matrix_world@Vector(c) for c in o.bound_box]
    xs=[v.x for v in bb]; ys=[v.y for v in bb]; zs=[v.z for v in bb]
    if max(xs)<5 or min(xs)>17 or min(ys)>12 or max(ys)<-6 or (max(xs)-min(xs))>30: continue
    # web: x=x, z=-y
    print("MAP %-34s webx[%.1f,%.1f] webz[%.1f,%.1f] y[%.2f,%.2f]"%(o.name[:34],min(xs),max(xs),-max(ys),-min(ys),min(zs),max(zs)))
