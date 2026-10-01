import bpy, os, math
WEB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "04_ThreeJS", "web", "personagens"))
bpy.ops.wm.read_factory_settings(use_empty=True)
cena = bpy.context.scene
for i, (anim, quadro) in enumerate([("escondido", 20), ("rendido", 20), ("correndo", 6), ("correndo", 14), ("andando", 10)]):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(WEB, "agressor.glb"))
    novos = [o for o in bpy.data.objects if o not in antes]
    for o in [o for o in novos if o.name.startswith("Icosphere")]: bpy.data.objects.remove(o, do_unlink=True)
    novos = [o for o in bpy.data.objects if o not in antes]
    for o in [o for o in novos if o.parent is None]: o.location.x += (i - 2) * 1.2; o.rotation_euler.z += .6
    arm = next(o for o in novos if o.type == "ARMATURE"); ad = arm.animation_data
    st = next(t for t in ad.nla_tracks if t.name == anim).strips[0]
    # cada copia em um quadro diferente: acao copiada com deslocamento
    ac = st.action.copy(); ad.action = ac
    try: ad.action_slot = ac.slots[0]
    except Exception: pass
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    for lay in ac.layers:
        for s in lay.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    for k in fc.keyframe_points: k.co.x += 100 - quadro; k.handle_left.x += 100 - quadro; k.handle_right.x += 100 - quadro
    arm["pelvis0"] = 0
cena.frame_set(100)
bpy.ops.mesh.primitive_plane_add(size=30)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); cena.collection.objects.link(cam); cena.camera = cam
cam.location = (0, -7.5, 1.0); cam.rotation_euler = (math.radians(88), 0, 0); cam.data.lens = 32
for r, e in [((50, 0, 30), 3), ((60, 0, 200), 1.5)]:
    l = bpy.data.objects.new("l", bpy.data.lights.new("l", "SUN")); l.data.energy = e; l.rotation_euler = [math.radians(a) for a in r]; cena.collection.objects.link(l)
w = bpy.data.worlds.new("w"); w.color = (.3, .3, .32); cena.world = w
cena.render.engine = "BLENDER_EEVEE"; cena.render.resolution_x, cena.render.resolution_y = 1500, 600
cena.render.filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_previa2.png")
bpy.ops.render.render(write_still=True)
