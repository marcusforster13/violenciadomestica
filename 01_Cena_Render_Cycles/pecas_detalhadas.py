"""
A Casa em Silencio - remodela as pecas pequenas "de revolucao" e os talheres com perfil detalhado.

- Garrafas de cerveja (600 ml): fundo concavo, ombro, gargalo, anel da boca, tampinha e rotulo (sem marca);
  vidro ambar com transmissao.
- Pratos com aba e fundo; arroz e feijao em montinhos; copo de vidro com parede grossa.
- Potes da prateleira com tampa; filtro de barro com reservatorio, pescoco e tampa; vaso de barro com borda e terra.
- Talheres: garfo de 4 dentes (curvado) e faca de mesa ao lado de cada prato.

Troca so a malha (mantem posicao, rotacao, pai e materiais). Marca as pecas com "detalhado" para os
outros scripts (suavizar_objetos.py) nao mexerem. Pode rodar de novo.

Uso:  blender -b casa_em_silencio.blend --python pecas_detalhadas.py
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

PI = math.pi

def lin(h):
    c = tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def material(nome, cor, rough=.5, metal=0., transm=0., ior=1.5):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*lin(cor), 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transm
    b.inputs["IOR"].default_value = ior
    m.diffuse_color = (*lin(cor), 1)
    return m

M_AMBAR = material("Vidro_Ambar", "#7a3d10", .04, transm=1.0)
M_COPO = material("Vidro_Copo", "#e8f0f2", .02, transm=1.0)
M_ROTULO = material("Rotulo_Garrafa", "#c49a2c", .55)
M_ROTULO2 = material("Rotulo_Garrafa_Faixa", "#9b1c1c", .5)
M_TAMPA = material("Tampinha_Metal", "#b9a46a", .3, 1.0)
M_TALHER = bpy.data.materials.get("Metal_Escovado") or material("Metal_Escovado", "#8a8c8e", .3, 1.0)

def malha_revolucao(nome, perfil, seg=48, z0=0.0):
    """perfil: lista (raio, altura). Fecha nas pontas com raio 0. z0 desloca (para objetos centrados)."""
    n = len(perfil); vs, fs = [], []
    for i in range(seg):
        a = 2 * PI * i / seg
        vs += [(r * math.cos(a), r * math.sin(a), h + z0) for r, h in perfil]
    for i in range(seg):
        i2 = (i + 1) % seg
        for j in range(n - 1):
            fs.append((i * n + j, i2 * n + j, i2 * n + j + 1, i * n + j + 1))
    me = bpy.data.meshes.new(nome); me.from_pydata(vs, [], fs)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(40))
    except Exception:
        pass
    return me

def trocar(ob, me):
    mats = list(ob.data.materials)
    for m in mats:
        me.materials.append(m)
    ob.data = me
    for md in list(ob.modifiers):
        if md.name in ("MM_Suave", "MM_Bevel"):
            ob.modifiers.remove(md)
    ob["detalhado"] = True

def limpar_filhos(ob):
    for c in list(ob.children):
        if c.name.startswith(ob.name + "_Det_"):
            bpy.data.objects.remove(c, do_unlink=True)

def filho(pai, sufixo, me, material):
    me.materials.clear(); me.materials.append(material)
    o = bpy.data.objects.new(pai.name + "_Det_" + sufixo, me)
    for c in pai.users_collection:
        c.objects.link(o)
    o.parent = pai; o["detalhado"] = True
    return o

def chapa(nome, contorno, espessura):
    """Contorno 2D (x, y) extrudado em Z -> talheres."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0)) for x, y in contorno]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    novos = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, espessura), verts=novos)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    for v in bm.verts:                                   # curvatura suave (pontas levantadas)
        v.co.z += .010 * (v.co.y / .1) ** 2 - espessura / 2
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    try:
        me.set_sharp_from_angle(angle=math.radians(35))
    except Exception:
        pass
    return me

feitos = []

# ---------------- garrafas (base na origem, altura 0,25 m)
GARRAFA = [(0, .004), (.010, .0055), (.022, .003), (.031, 0), (.0352, .003), (.0358, .010), (.0358, .150), (.0352, .163),
           (.0315, .182), (.0235, .198), (.0160, .209), (.0128, .222), (.0124, .236), (.0142, .239), (.0148, .244),
           (.0132, .248), (.0115, .249), (0, .249)]
for nome in ["V_Garrafa_1", "V_Garrafa_2", "V_Garrafa_3", "V_Garrafa_4", "V_Garrafa_Chao"]:
    ob = bpy.data.objects.get(nome)
    if not ob:
        continue
    limpar_filhos(ob)
    trocar(ob, malha_revolucao(nome, GARRAFA, 40))
    if nome != "V_Garrafa_Chao":
        filho(ob, "Tampinha", malha_revolucao(nome + "_tampa", [(0, .247), (.0152, .247), (.0156, .2475), (.0156, .253), (.014, .2545), (0, .2545)], 24), M_TAMPA)
    filho(ob, "Rotulo", malha_revolucao(nome + "_rot", [(.0362, .045), (.0362, .115)], 40), M_ROTULO)
    filho(ob, "Rotulo_Faixa", malha_revolucao(nome + "_rot2", [(.0363, .072), (.0363, .084)], 40), M_ROTULO2)
    ob.data.materials.clear(); ob.data.materials.append(M_AMBAR)
    feitos.append(nome)

# ---------------- pratos (objeto centrado, espessura ~1,5 cm)
PRATO = [(0, .0015), (.068, 0), (.072, .0005), (.076, .002), (.11, .006), (.124, .012), (.131, .0165), (.1325, .018),
         (.1305, .0185), (.121, .0145), (.104, .0098), (.076, .0072), (0, .0072)]
for nome in ["Prato_1", "Prato_2"]:
    ob = bpy.data.objects.get(nome)
    if ob:
        trocar(ob, malha_revolucao(nome, PRATO, 56, z0=-.0075)); feitos.append(nome)

# ---------------- arroz e feijao em montinhos
for nome, r, h, rug in [("Arroz_1", .062, .022, .0016), ("Arroz_2", .062, .022, .0016), ("Feijao_1", .05, .016, .0008), ("Feijao_2", .05, .016, .0008)]:
    ob = bpy.data.objects.get(nome)
    if not ob:
        continue
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=1)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    import random
    rr = random.Random(hash(nome) & 0xffff)
    for v in bm.verts:
        v.co.x *= r; v.co.y *= r; v.co.z = v.co.z * h - .0105      # assenta no fundo do prato
        if v.co.z > -.009:
            v.co += Vector((rr.uniform(-rug, rug), rr.uniform(-rug, rug), rr.uniform(-rug, rug)))
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    trocar(ob, me); feitos.append(nome)

# ---------------- copo de vidro (centrado, altura 0,11 m) com parede grossa
ob = bpy.data.objects.get("V_Copo_Tombado")
if ob:
    COPO = [(0, 0), (.029, 0), (.031, .002), (.032, .006), (.0355, .11), (.0335, .11), (.0302, .009), (.026, .007), (0, .007)]
    trocar(ob, malha_revolucao("V_Copo_Tombado", COPO, 40, z0=-.055))
    ob.data.materials.clear(); ob.data.materials.append(M_COPO); feitos.append(ob.name)

# ---------------- potes com tampa (centrados, ~0,15 m)
POTE = [(0, 0), (.044, 0), (.0485, .003), (.05, .01), (.05, .108), (.047, .111), (.047, .113), (.0515, .1145), (.0525, .118),
        (.0525, .132), (.05, .136), (.03, .1385), (.012, .139), (.0115, .146), (.0085, .149), (0, .149)]
for i in range(1, 6):
    ob = bpy.data.objects.get("Pote_%d" % i)
    if ob:
        trocar(ob, malha_revolucao(ob.name, POTE, 40, z0=-.075)); feitos.append(ob.name)

# ---------------- filtro de barro (base na origem)
ob = bpy.data.objects.get("Filtro_de_Barro")
if ob:
    FILTRO = [(0, 0), (.105, 0), (.118, .004), (.125, .012), (.138, .05), (.152, .11), (.158, .16), (.159, .19), (.156, .196),
              (.159, .202), (.158, .24), (.15, .275), (.138, .295), (.133, .30), (.140, .306), (.148, .312), (.152, .32),
              (.158, .37), (.161, .42), (.159, .46), (.152, .505), (.148, .525), (.152, .53), (.152, .538), (.141, .542),
              (.128, .556), (.104, .585), (.07, .608), (.035, .62), (.026, .626), (.028, .64), (.032, .65), (.025, .662), (0, .664)]
    trocar(ob, malha_revolucao("Filtro_de_Barro", FILTRO, 56)); feitos.append(ob.name)

# ---------------- vaso de barro da costela-de-adao (centrado, altura 0,42 m) + terra
ob = bpy.data.objects.get("Vaso_Barro")
if ob:
    limpar_filhos(ob)
    VASO = [(0, 0), (.128, 0), (.138, .006), (.146, .03), (.165, .14), (.182, .26), (.194, .36), (.2, .392), (.212, .398),
            (.214, .42), (.196, .42), (.19, .40), (.186, .375), (0, .375)]
    trocar(ob, malha_revolucao("Vaso_Barro", VASO, 48, z0=-.21)); feitos.append(ob.name)
    terra = bpy.data.materials.get("Terra_Canteiro") or material("Terra_Vaso", "#3b2e22", .95)
    filho(ob, "Terra", malha_revolucao("Vaso_Terra", [(0, .372), (.184, .372), (.184, .376), (0, .379)], 40, z0=-.21), terra)

# ---------------- talheres: garfo (substitui a peca antiga) e faca de mesa ao lado
def contorno_garfo():
    w, g = .004, (.024 - 4 * .004) / 3
    pts = [(-.006, -.1), (.006, -.1), (.0078, -.095), (.0078, -.005), (.0035, .02), (.003, .032), (.011, .045), (.012, .055)]
    for k in range(4):
        xr = .012 - k * (w + g); xl = xr - w
        pts += [(xr, .1), (xl, .1)]
        if k < 3:
            pts += [(xl, .062), (xl - g, .062)]
    pts += [(-.012, .055), (-.011, .045), (-.003, .032), (-.0035, .02), (-.0078, -.005), (-.0078, -.095)]
    return pts

FACA = [(-.006, -.1), (.006, -.1), (.0072, -.095), (.0072, -.006), (.0052, .0), (.0066, .07), (.0058, .095), (.003, .107),
        (0, .11), (-.0085, .104), (-.0092, .09), (-.0092, .002), (-.0072, -.006), (-.0072, -.095)]
for i in (1, 2):
    ob = bpy.data.objects.get("Garfo_%d" % i)
    if not ob:
        continue
    for c in list(ob.children):
        bpy.data.objects.remove(c, do_unlink=True)
    trocar(ob, chapa(ob.name, contorno_garfo(), .0028))
    ob.data.materials.clear(); ob.data.materials.append(M_TALHER)
    nome_faca = "Faca_Mesa_%d" % i
    velho = bpy.data.objects.get(nome_faca)
    if velho:
        bpy.data.objects.remove(velho, do_unlink=True)
    fme = chapa(nome_faca, FACA, .0024); fme.materials.append(M_TALHER)
    fo = bpy.data.objects.new(nome_faca, fme)
    for c in ob.users_collection:
        c.objects.link(fo)
    fo.parent = ob.parent; fo.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
    fo.location = ob.location.copy(); fo.location.x -= .34; fo.rotation_euler = ob.rotation_euler.copy()
    fo["detalhado"] = True
    feitos += [ob.name, nome_faca]

print("[DETALHE] %d pecas remodeladas: %s" % (len(feitos), ", ".join(feitos)))
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[DETALHE] cena principal salva")
