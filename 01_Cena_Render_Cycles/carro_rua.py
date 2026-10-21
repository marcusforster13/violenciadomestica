"""
A Casa em Silencio - troca o carro vermelho da rua (procedural) pelo hatch do projeto da Lei Seca
(modelos/carros/hatch.glb, pacote "Generic passenger car pack" de Comrade1280, CC-BY-4.0 - ver modelos/CREDITOS.md).

Mesma vaga, mesma direcao. Vidros escuros e semitransparentes, texturas em 1024 px (leves para o Quest) e materiais com o
prefixo "Carro_UV_" (o pipeline VR mantem a UV do modelo nesses materiais). Idempotente.
Uso:  blender -b casa_em_silencio.blend --python carro_rua.py
"""
import bpy, os
from mathutils import Matrix

def say(m): print("[CARRO] " + m)
ARQ = os.path.join(os.path.dirname(bpy.data.filepath), "modelos", "carros", "hatch.glb")
NOME = "Carro_Rua"; POS = (15.5, -23.0, 0.0); RZ = .01          # vaga do antigo Carro_Rua_Vermelho

col = None
for nome in ("Carro_Rua_Vermelho", NOME):                          # tira o carro antigo (ou o hatch de uma rodada anterior)
    c = bpy.data.objects.get(nome)
    if c:
        col = col or c.users_collection[0]
        for o in list(c.children_recursive) + [c]: bpy.data.objects.remove(o, do_unlink=True)
col = col or bpy.data.collections.get("10b_Carros_Moradores") or bpy.context.scene.collection
for m in [m for m in bpy.data.materials if m.name.startswith("Carro_UV_") and not m.users]: bpy.data.materials.remove(m)

antes = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=ARQ)
novos = [o for o in bpy.data.objects if o not in antes]
raiz = next(o for o in novos if o.parent is None); raiz.name = NOME
for o in novos:
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o)
    if o is not raiz: o.name = NOME + "_" + o.name.split(".")[0]
feitos = {}
for o in novos:
    if o.type != "MESH": continue
    for s in o.material_slots:
        if not s.material: continue
        base = s.material.name.split(".")[0]
        if base not in feitos:
            m = s.material.copy(); m.name = "Carro_UV_" + base; feitos[base] = m
            b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image and max(n.image.size) > 1024:
                    n.image.scale(1024, 1024); n.image.pack()
            if "glass" in base.lower() and b:                         # vidro fume (como nos carros da Lei Seca)
                for l in list(b.inputs["Alpha"].links) + list(b.inputs["Base Color"].links): m.node_tree.links.remove(l)
                b.inputs["Base Color"].default_value = (.03, .045, .055, 1); b.inputs["Alpha"].default_value = .8
                b.inputs["Roughness"].default_value = .06; b.inputs["Metallic"].default_value = 0
                for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
                    try: setattr(m, attr, val)
                    except Exception: pass
        s.material = feitos[base]
raiz.location = POS; raiz.rotation_euler = (0, 0, RZ)
tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in novos if o.type == "MESH")
say("carro da rua: hatch da Lei Seca (~%d triangulos) no lugar do carro vermelho" % tri)
bpy.ops.wm.save_mainfile()
