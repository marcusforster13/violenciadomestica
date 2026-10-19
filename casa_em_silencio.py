"""
A Casa em Silencio - cena base para Blender (4.2+ / 5.x)

Casa modernista brasileira (cobogo, azulejos, granilite, ladrilho hidraulico,
pilotis, forro ripado, brise) apos um episodio de violencia domestica.

Como usar: abra o Blender > aba Scripting > Open > este arquivo > Run Script.
Tudo e criado em colecoes separadas; os vestigios ficam em "08_Vestigios",
entao da para ligar/desligar a cena "antes" e "depois".
Unidades em metros. Frente da casa (varanda) voltada para -Y.
"""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, Euler

PI = math.pi
rnd = random.Random(1947)

# ------------------------------------------------------------------ limpeza
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
             bpy.data.curves, bpy.data.images):
    for d in list(coll):
        coll.remove(d)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)

scene = bpy.context.scene

def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

C_EST = collection("01_Estrutura")
C_SALA = collection("02_Sala")
C_JANT = collection("03_Jantar")
C_COZ = collection("04_Cozinha")
C_VAR = collection("05_Varanda")
C_JARD = collection("06_Jardim")
C_VEST = collection("08_Vestigios")
C_LUZ = collection("09_Luzes_Cameras")
C_CUT = collection("99_Cortadores")

# ------------------------------------------------------------------ cores
def hx(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))

def lin(c):
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

# ------------------------------------------------------------------ materiais
def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF") or nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
    if not out.inputs["Surface"].is_linked:
        nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m, nt, b

def si(b, name, val):
    if name in b.inputs:
        b.inputs[name].default_value = val

def mat(name, color, rough=.8, metal=0., emit=None, emit_str=0., alpha=None):
    m, nt, b = new_mat(name)
    c = lin(hx(color))
    si(b, "Base Color", (*c, 1))
    si(b, "Roughness", rough)
    si(b, "Metallic", metal)
    if emit:
        si(b, "Emission Color", (*lin(hx(emit)), 1))
        si(b, "Emission Strength", emit_str)
    if alpha is not None:
        si(b, "Alpha", alpha)
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    m.diffuse_color = (*c, 1 if alpha is None else alpha)
    return m

def np_image(name, arr):
    """arr: H x W x 3 (0..1, sRGB), linha 0 = topo"""
    h, w, _ = arr.shape
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = arr
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(np.flipud(rgba).ravel())
    img.pack()
    return img

def img_mat(name, img, tile_m, rough=.5, uv=False):
    """Textura projetada em caixa (coordenadas do objeto, em metros)."""
    m, nt, b = new_mat(name)
    n = nt.nodes
    tex = n.new("ShaderNodeTexImage"); tex.image = img
    si(b, "Roughness", rough)
    if uv:
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    else:
        tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / tile_m,) * 3
        tex.projection = "BOX"; tex.projection_blend = .15
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    m.diffuse_color = (*lin(tuple(np.array(img.pixels[:3]))), 1)
    return m

def wood_mat(name, c1, c2, rough=.55):
    m, nt, b = new_mat(name)
    n = nt.nodes
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1, 1, 1)
    wv = n.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 4
    wv.inputs["Distortion"].default_value = 9
    wv.inputs["Detail"].default_value = 3
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*lin(hx(c1)), 1)
    ramp.color_ramp.elements[1].color = (*lin(hx(c2)), 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    si(b, "Roughness", rough)
    m.diffuse_color = (*lin(hx(c1)), 1)
    return m

# --- texturas geradas (empacotadas no .blend)
def tex_granilite(S=1024):
    a = np.ones((S, S, 3)) * hx("#cfc8bb")
    cols = [hx(c) for c in ("#8a8378", "#f4f0e8", "#5b554d", "#b9a58a", "#9aa29a", "#e8dcc6", "#3f3b36")]
    r = np.random.default_rng(3)
    for i in range(26000):
        cx, cy = r.integers(0, S, 2); rad = r.uniform(1, 4)
        x0, x1 = max(cx - 4, 0), min(cx + 5, S); y0, y1 = max(cy - 4, 0), min(cy + 5, S)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mk = (xx - cx) ** 2 + ((yy - cy) * r.uniform(1, 1.6)) ** 2 < rad ** 2
        a[y0:y1, x0:x1][mk] = cols[i % len(cols)]
    brass = hx("#a8894a")
    a[:3, :] = brass; a[-3:, :] = brass; a[:, :3] = brass; a[:, -3:] = brass
    return a

def tex_ladrilho(S=512):
    y, x = np.mgrid[0:S, 0:S] / S
    cream, terra, ink = hx("#ece2cc"), hx("#a8492f"), hx("#262522")
    a = np.ones((S, S, 3)) * cream
    for cx, cy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        d = np.hypot(x - cx, y - cy)
        a[(d < .34) & (d >= .24)] = terra
        a[d < .1] = ink
    dm = np.abs(x - .5) + np.abs(y - .5)
    a[dm < .3] = ink; a[dm < .18] = cream
    a[np.hypot(x - .5, y - .5) < .07] = terra
    g = hx("#b7ab98"); a[:3] = g; a[-3:] = g; a[:, :3] = g; a[:, -3:] = g
    return a

def tex_azulejo(n=8, s=128):
    W = n * s
    a = np.zeros((W, W, 3))
    white, blue = np.array(hx("#f3f1ea")), np.array(hx("#1d4f9e"))
    v, u = np.mgrid[0:s, 0:s] / (s - 1)
    for i in range(n):
        for j in range(n):
            k, rot = rnd.randrange(4), rnd.randrange(4)
            uu, vv = u, v
            for _ in range(rot):
                uu, vv = vv, 1 - uu
            if k == 0: m = uu ** 2 + vv ** 2 < .25
            elif k == 1: m = vv < .24
            elif k == 2: m = (uu - .5) ** 2 + vv ** 2 < .09
            else: m = uu + vv < 1
            a[j * s:(j + 1) * s, i * s:(i + 1) * s] = np.where(m[..., None], blue, white)
    g = np.array(hx("#8a8a82"))
    for i in range(n + 1):
        p = min(i * s, W - 1)
        a[max(p - 1, 0):p + 2] = g; a[:, max(p - 1, 0):p + 2] = g
    return a

def tex_palhinha(S=256, s=32):
    y, x = np.mgrid[0:S, 0:S]
    a = np.ones((S, S, 3)) * hx("#c9a86b")
    a[((x + y) % s < 3) | ((x - y) % s < 3)] = hx("#7d6236")
    a[np.hypot((x % s) - s / 2, (y % s)) < 5] = hx("#3a2d18")
    return a

def tex_rede(W=64, H=512):
    cols = [hx(c) for c in ("#b8322a", "#e3a92b", "#2a6f97", "#f1e7d0", "#2f7a4a", "#f1e7d0")]
    a = np.zeros((H, W, 3)); b = H // 24
    for i in range(24):
        a[i * b:(i + 1) * b] = cols[i % len(cols)]
    return a

def tex_tapete(W=512, H=384):
    a = np.ones((H, W, 3)) * hx("#7e3a24")
    y, x = np.mgrid[0:H, 0:W]
    brd = ((np.abs(x - 24) < 5) | (np.abs(x - (W - 24)) < 5)) & (y > 20) & (y < H - 20)
    brd |= ((np.abs(y - 24) < 5) | (np.abs(y - (H - 24)) < 5)) & (x > 20) & (x < W - 20)
    a[brd] = hx("#d3a14a")
    a[(np.abs((x % 40) - 20) + np.abs(y - H / 2) * .5 < 20) & (x > 50) & (x < W - 50)] = hx("#e9dcc2")
    a[((np.abs(y - 74) < 4) | (np.abs(y - (H - 74)) < 4)) & (x > 40) & (x < W - 40)] = hx("#2e2a25")
    return a

M = {
    "reboco": mat("Reboco_Branco", "#e8e2d6", .92),
    "reboco_marca": mat("Reboco_MarcaQuadro", "#f3efe6", .92),
    "concreto": mat("Concreto_Aparente", "#a19d95", .95),
    "granilite": img_mat("Piso_Granilite", np_image("granilite", tex_granilite()), 1.0, .3),
    "ladrilho": img_mat("Piso_LadrilhoHidraulico", np_image("ladrilho", tex_ladrilho()), .5, .55),
    "azulejo": img_mat("Azulejo_AthosBulcao", np_image("azulejo", tex_azulejo()), 1.2, .2),
    "palhinha": img_mat("Palhinha", np_image("palhinha", tex_palhinha()), .12, .8),
    "rede": img_mat("Rede_Listrada", np_image("rede", tex_rede()), 1, 1, uv=True),
    "tapete": img_mat("Tapete", np_image("tapete", tex_tapete()), 3, 1, uv=True),
    "freijo": wood_mat("Madeira_Freijo", "#c28b5a", "#8f5f38"),
    "jacaranda": wood_mat("Madeira_Jacaranda", "#5a3622", "#2e1b10", .45),
    "forro": wood_mat("Madeira_Forro", "#a8744a", "#7a5030", .7),
    "couro": mat("Couro_Caramelo", "#6b3a22", .5),
    "tecido": mat("Tecido_Verde", "#50604f", .95),
    "tecido2": mat("Tecido_Areia", "#c9b58c", .95),
    "preto": mat("Preto_Fosco", "#1b1a19", .6),
    "metal": mat("Metal_Escovado", "#8a8c8e", .35, 1),
    "latao": mat("Latao", "#b08a45", .35, 1),
    "vidro": mat("Vidro", "#a9c6d6", .05, alpha=.15),
    "granito": mat("Granito_SaoGabriel", "#141519", .22),
    "barro": mat("Terracota", "#a4522f", .9),
    "ceramica": mat("Loucas_Brancas", "#f7f5f0", .25),
    "folha": mat("Folhagem", "#2f5a33", .7),
    "grama": mat("Grama", "#1b2e1f", 1),
    "garrafa": mat("Vidro_Ambar", "#3a200c", .15),
    "geladeira": mat("Geladeira_Verde", "#8fbfab", .35),
    "tronco": mat("Tronco_Palmeira", "#6b5b4a", 1),
    "arbusto": mat("Arbusto", "#243d26", 1),
    "corredor": mat("Corredor_Escuro", "#1a1816", 1),
    "arroz": mat("Arroz", "#ece6d6", .9),
    "feijao": mat("Feijao", "#3b2418", .6),
    "liquido": mat("Liquido_Derramado", "#6a3e14", .05, alpha=.75),
    "cupula": mat("Luminaria_Cupula", "#e9dfc9", .9),
    "pendente": mat("Pendente_Metal", "#2b2d2e", .4, .5),
    "lampada": mat("Lampada_Acesa", "#ffffff", .5, emit="#ffcf8a", emit_str=12),
    "tv": mat("Tela_TV", "#000000", .3, emit="#6f8fd8", emit_str=3),
    "celular_tela": mat("Tela_Celular", "#000000", .2, emit="#2a2140", emit_str=2),
    "texto_tela": mat("Texto_Tela", "#ffffff", .5, emit="#ffffff", emit_str=4),
    "papel": mat("Papel", "#fbf8f1", .9),
    "giz": mat("Giz_de_Cera", "#333333", .9),
    "foto": mat("Foto_Familia_(trocar_por_imagem)", "#c9a07a", .3),
    "mala": mat("Mala_Vermelha", "#7a2e2e", .5),
    "pelucia": mat("Pelucia", "#8a5a33", 1),
    "cortador": mat("Cortador", "#ff00ff", 1),
}
ROUPAS = [mat("Roupa_%d" % i, c, .95) for i, c in enumerate(("#d8cfbf", "#2e4a62", "#b0417a", "#e9e3d6", "#3d5a3a"))]
LIVROS = [mat("Livro_%d" % i, c, .8) for i, c in enumerate(("#7b2d26", "#2e4a62", "#c9a24b", "#3d5a3a", "#d8cfbf", "#5b3f63", "#9a5b2e"))]

# ------------------------------------------------------------------ geometria
# Coordenadas escritas como (x, altura, z_frente); V() converte para o Blender (Z para cima).
def V(x, y, z):
    return Vector((x, -z, y))

def finish(name, bm, loc, material, col, parent=None, rot=(0, 0, 0), smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if material:
        me.materials.append(material)
    col.objects.link(ob)
    if parent:
        ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    return ob

def _bm():
    bm = bmesh.new(); bm.loops.layers.uv.new(); return bm

def box(name, w, h, d, x, y, z, material, col, parent=None, rx=0, ry=0, rz=0):
    bm = _bm()
    bmesh.ops.create_cube(bm, size=1, calc_uvs=True)
    bmesh.ops.scale(bm, vec=(w, d, h), verts=bm.verts)
    return finish(name, bm, V(x, y, z), material, col, parent, (rx, -rz, ry))

def cyl(name, rt, rb, h, x, y, z, material, col, parent=None, seg=24, rx=0, ry=0, rz=0, caps=True):
    bm = _bm()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=rb, radius2=rt, depth=h, calc_uvs=True)
    return finish(name, bm, V(x, y, z), material, col, parent, (rx, -rz, ry), smooth=True)

def sphere(name, r, x, y, z, material, col, parent=None, scale=(1, 1, 1), seg=16):
    bm = _bm()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2 + 2, radius=r, calc_uvs=True)
    bmesh.ops.scale(bm, vec=(scale[0], scale[2], scale[1]), verts=bm.verts)
    return finish(name, bm, V(x, y, z), material, col, parent, smooth=True)

def lathe(name, prof, x, y, z, material, col, parent=None, seg=28):
    n = len(prof); verts, faces = [], []
    for i in range(seg):
        a = 2 * PI * i / seg
        verts += [(r * math.cos(a), r * math.sin(a), h) for r, h in prof]
    for i in range(seg):
        i2 = (i + 1) % seg
        for j in range(n - 1):
            faces.append((i * n + j, i2 * n + j, i2 * n + j + 1, i * n + j + 1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(name, bm, V(x, y, z), material, col, parent, smooth=True)

def pydata(name, verts, faces, loc, material, col, parent=None, uvs=None, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    if uvs:
        ul = me.uv_layers.new()
        for poly in me.polygons:
            for li in poly.loop_indices:
                ul.data[li].uv = uvs[me.loops[li].vertex_index]
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if material:
        me.materials.append(material)
    col.objects.link(ob)
    if parent:
        ob.parent = parent
    ob.location = loc
    return ob

def grp(name, x, y, z, col, ry=0, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"; e.empty_display_size = .3
    col.objects.link(e)
    if parent:
        e.parent = parent
    e.location = V(x, y, z); e.rotation_euler = (0, 0, ry)
    return e

def text(name, body, size, loc, rot, material, col, parent=None, align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body; cu.size = size; cu.align_x = align; cu.extrude = .0004
    cu.materials.append(material)
    ob = bpy.data.objects.new(name, cu); col.objects.link(ob)
    if parent:
        ob.parent = parent
    ob.location = loc; ob.rotation_euler = rot
    return ob

def as_cutter(ob):
    ob.display_type = "WIRE"; ob.hide_render = True
    return ob

def boolean(target, cutter, name="Corte"):
    md = target.modifiers.new(name, "BOOLEAN")
    md.operation = "DIFFERENCE"; md.object = cutter
    return md

def orient(ob, direction):
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())

# ================================================================== ESTRUTURA
box("Piso_Interno_Granilite", 12, .1, 8, 0, -.05, 0, M["granilite"], C_EST)
box("Piso_Varanda_Ladrilho", 13, .1, 3, 0, -.05, 5.5, M["ladrilho"], C_VAR)
box("Gramado", 90, .02, 90, 0, -.11, 0, M["grama"], C_JARD)
box("Laje_Cobertura", 13, .25, 11.4, 0, 3.125, 1.3, M["concreto"], C_EST)
for i, x in enumerate((-5.8, -2, 2, 5.8)):
    cyl("Piloti_%d" % (i + 1), .11, .11, 3, x, 1.5, 6.8, M["reboco"], C_VAR)

# forro ripado: uma ripa + Array (mude Count/Offset para ajustar)
ripa = box("Forro_Ripado", .08, .03, 8, -5.94, 2.965, 0, M["forro"], C_EST)
arr = ripa.modifiers.new("Ripas", "ARRAY")
arr.use_relative_offset = False; arr.use_constant_offset = True
arr.constant_offset_displace = (.14, 0, 0); arr.count = 85

box("Parede_Direita", .2, 3, 8.4, 6.1, 1.5, 0, M["reboco"], C_EST)
box("Parede_Fundo", 8.2, 3, .2, 2.1, 1.5, -4.1, M["reboco"], C_EST)
parede_esq = box("Parede_Esquerda_A", .2, 3, 5.6, -6.1, 1.5, -1.2, M["reboco"], C_EST)
box("Parede_Esquerda_B", .2, 3, 1.5, -6.1, 1.5, 3.25, M["reboco"], C_EST)
box("Verga_Porta_Quarto", .2, .9, .9, -6.1, 2.55, 2.05, M["reboco"], C_EST)

# parede de cobogo: um bloco com furos (Boolean) + dois Arrays
bloco = box("Cobogo_Bloco", .25, .25, .1, -6 + .125, .125, -4.1, M["reboco"], C_EST)
bm = _bm()
for dx in (-.05, .05):
    for dz in (-.05, .05):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=.0425, radius2=.0425, depth=.3,
                              matrix=Matrix.Translation((dx, 0, dz)) @ Matrix.Rotation(PI / 2, 4, "X"))
furos = as_cutter(finish("Cobogo_Furos", bm, Vector((0, 0, 0)), M["cortador"], C_CUT, parent=bloco))
boolean(bloco, furos, "Furos")
for nm, off, cnt in (("Colunas", (.25, 0, 0), 16), ("Fiadas", (0, 0, .25), 12)):
    md = bloco.modifiers.new(nm, "ARRAY")
    md.use_relative_offset = False; md.use_constant_offset = True
    md.constant_offset_displace = off; md.count = cnt
box("Cobogo_Base", 4, .1, .24, -4, .05, -4.1, M["reboco"], C_EST)

corredor = box("Corredor_Escuro", 2, 3, 2.4, -7.2, 1.5, 2.05, M["corredor"], C_EST)
bm = bmesh.new(); bm.from_mesh(corredor.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(corredor.data); bm.free()

box("Painel_Azulejos", 3.8, 3, .01, 0, 1.5, -3.995, M["azulejo"], C_EST)
box("Revestimento_Cozinha", 3.6, .95, .01, 4.2, 1.415, -3.995, M["azulejo"], C_COZ)

# fachada de vidro
for i, x in enumerate((-6, -4.25, -2.5, -1, 1, 2.5, 4.25, 6)):
    box("Caixilho_V%d" % (i + 1), .06, 3, .08, x, 1.5, 4, M["jacaranda"], C_EST)
box("Caixilho_Base", 12, .08, .1, 0, .04, 4, M["jacaranda"], C_EST)
box("Caixilho_Topo", 12, .08, .1, 0, 2.96, 4, M["jacaranda"], C_EST)
for i, (a, b) in enumerate(((-6, -4.25), (-4.25, -2.5), (-2.5, -1), (1, 2.5), (2.5, 4.25), (4.25, 6))):
    box("Vidro_%d" % (i + 1), b - a - .06, 2.84, .01, (a + b) / 2, 1.5, 4, M["vidro"], C_EST)
box("Vidro_Porta_Correr", 1.5, 2.84, .01, -1.75, 1.5, 4.1, M["vidro"], C_EST)
box("Caixilho_Porta_Correr", .05, 2.9, .05, -1.02, 1.5, 4.1, M["jacaranda"], C_EST)

# brise-soleil
z = 4.25; i = 0
while z < 7:
    box("Brise_%02d" % i, .03, 2.9, .26, 6.25, 1.5, z, M["freijo"], C_VAR, ry=.55)
    z += .28; i += 1

# porta do quarto entreaberta (gire o empty "Porta_Quarto_Dobradica" no Z)
box("Batente_1", .24, 2.1, .06, -6.1, 1.05, 1.6, M["jacaranda"], C_EST)
box("Batente_2", .24, 2.1, .06, -6.1, 1.05, 2.5, M["jacaranda"], C_EST)
box("Batente_Topo", .24, .06, .96, -6.1, 2.1, 2.05, M["jacaranda"], C_EST)
dob = grp("Porta_Quarto_Dobradica", -6.0, 0, 2.47, C_EST, ry=-.95)
box("Porta_Quarto", .04, 2.06, .86, 0, 1.03, -.43, M["freijo"], C_EST, dob)
box("Macaneta", .06, .03, .12, .04, 1.02, -.78, M["latao"], C_EST, dob)

# ================================================================== SALA
box("Tapete", 2.4, .008, 3, -3.6, .004, -1.1, M["tapete"], C_SALA)

sofa = grp("Sofa", -2.2, 0, -1.1, C_SALA, ry=-PI / 2)
L, D = 2.2, .9
for sx in (-1, 1):
    for sz in (-1, 1):
        box("Sofa_Pe", .05, .18, .05, sx * (L / 2 - .12), .09, sz * (D / 2 - .12), M["jacaranda"], C_SALA, sofa)
box("Sofa_Base", L, .08, D, 0, .22, 0, M["jacaranda"], C_SALA, sofa)
for sx in (-1, 1):
    box("Sofa_Assento", L / 2 - .03, .16, D - .2, sx * L / 4, .34, .08, M["tecido"], C_SALA, sofa)
    box("Sofa_Braco", .07, .18, D, sx * (L / 2 - .035), .35, 0, M["jacaranda"], C_SALA, sofa)
box("Sofa_Encosto", L, .42, .16, 0, .5, -D / 2 + .08, M["tecido"], C_SALA, sofa)
box("Sofa_Almofada", L / 2 - .06, .34, .14, -L / 4, .62, -D / 2 + .24, M["tecido2"], C_SALA, sofa)

mc = grp("Mesa_Centro", -3.45, 0, -.95, C_SALA, ry=.28)
box("Mesa_Centro_Tampo", 1.1, .04, .6, 0, .36, 0, M["freijo"], C_SALA, mc)
for sx in (-1, 1):
    for sz in (-1, 1):
        box("Mesa_Centro_Pe", .04, .34, .04, sx * .48, .17, sz * .24, M["jacaranda"], C_SALA, mc)

# poltrona (referencia a Poltrona Mole, Sergio Rodrigues)
pol = grp("Poltrona", -4.3, 0, 1.35, C_SALA, ry=math.atan2(.8, -2.4))
for sx in (-1, 1):
    box("Poltrona_Lateral", .08, .34, .95, sx * .46, .22, 0, M["jacaranda"], C_SALA, pol)
    box("Poltrona_Braco", .14, .13, .82, sx * .44, .46, 0, M["couro"], C_SALA, pol)
box("Poltrona_Travessa", .9, .06, .06, 0, .12, .45, M["jacaranda"], C_SALA, pol)
box("Poltrona_Assento", .84, .18, .8, 0, .32, .05, M["couro"], C_SALA, pol)
cyl("Poltrona_Rolo", .09, .09, .84, 0, .4, .42, M["couro"], C_SALA, pol, 16, rz=PI / 2)
box("Poltrona_Encosto", .84, .6, .18, 0, .66, -.34, M["couro"], C_SALA, pol, rx=-.32)

rack = grp("Rack_TV", -5.72, 0, -1.1, C_SALA, ry=PI / 2)
box("Rack", 1.6, .42, .45, 0, .27, 0, M["freijo"], C_SALA, rack)
for sx in (-1, 1):
    box("Rack_Pe", .04, .06, .4, sx * .7, .03, 0, M["jacaranda"], C_SALA, rack)
box("TV", 1.1, .64, .05, 0, .86, -.08, M["preto"], C_SALA, rack)
box("TV_Tela", 1.04, .58, .005, 0, .86, -.052, M["tv"], C_SALA, rack)

est = grp("Estante", -5.82, 0, -3.2, C_SALA, ry=PI / 2)
for sx in (-1, 1):
    box("Estante_Lateral", .03, 2, .35, sx * .6, 1, 0, M["freijo"], C_SALA, est)
for k in range(5):
    y = .05 + k * .47
    box("Estante_Prateleira", 1.2, .03, .35, 0, y, 0, M["freijo"], C_SALA, est)
    if k < 4:
        x = -.55
        while x < .5:
            bw, bh = .03 + rnd.random() * .04, .24 + rnd.random() * .12
            box("Livro", bw, bh, .24, x + bw / 2, y + .015 + bh / 2, .02, rnd.choice(LIVROS), C_SALA, est)
            x += bw + .004
            if k == 1 and x > .1:
                break

vaso = grp("Costela_de_Adao", -.6, 0, 3.35, C_SALA)
cyl("Vaso_Barro", .2, .15, .42, 0, .21, 0, M["barro"], C_SALA, vaso, 20)
lv, lf = [], []
for i in range(8):
    a = i / 8 * 2 * PI + rnd.random() * .3
    h, r = .7 + rnd.random() * .5, .28 + rnd.random() * .18
    end = V(math.cos(a) * r, h + .2, math.sin(a) * r)
    stem = cyl("Caule", .008, .008, (end - V(0, .4, 0)).length, 0, 0, 0, M["folha"], C_SALA, vaso, 6)
    stem.location = (end + V(0, .4, 0)) / 2; orient(stem, end - V(0, .4, 0))
    out = Vector((end.x, end.y, 0)).normalized()
    side = out.cross(Vector((0, 0, 1)))
    mtx = Matrix.Translation(end)
    base = len(lv); pts = 12
    for t in range(pts + 1):
        s = t / pts
        w = .27 * math.sin(PI * s) ** .8
        axis = out * (.5 * s) + Vector((0, 0, .18 * math.sin(PI * s) - .12 * s))
        lv.append(tuple(end + axis + side * w)); lv.append(tuple(end + axis - side * w))
    for t in range(pts):
        a0 = base + t * 2
        lf.append((a0, a0 + 2, a0 + 3, a0 + 1))
folhas = pydata("Costela_de_Adao_Folhas", lv, lf, Vector((0, 0, 0)), M["folha"], C_SALA, vaso, smooth=True)
sol = folhas.modifiers.new("Espessura", "SOLIDIFY"); sol.thickness = .004

# ================================================================== JANTAR
mesa = grp("Mesa_Jantar", 1.2, 0, .8, C_JANT)
box("Mesa_Jantar_Tampo", 1.8, .05, .9, 0, .75, 0, M["jacaranda"], C_JANT, mesa)
for sx in (-1, 1):
    for sz in (-1, 1):
        box("Mesa_Jantar_Pe", .05, .73, .05, sx * .82, .365, sz * .37, M["jacaranda"], C_JANT, mesa)
for i, (x, z) in enumerate(((-.45, -.22), (.45, .22))):
    cyl("Prato_%d" % (i + 1), .13, .12, .015, x, .785, z, M["ceramica"], C_JANT, mesa, 32)
    cyl("Arroz_%d" % (i + 1), .065, .065, .01, x - .03, .795, z, M["arroz"], C_JANT, mesa, 16)
    cyl("Feijao_%d" % (i + 1), .05, .05, .012, x + .05, .796, z + .02, M["feijao"], C_JANT, mesa, 16)
    box("Garfo_%d" % (i + 1), .02, .005, .2, x + .17, .78, z, M["metal"], C_JANT, mesa)

def cadeira(name, parent_col, parent=None, x=0, y=0, z=0, ry=0):
    g = grp(name, x, y, z, parent_col, ry, parent)
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(name + "_Pe", .035, .45, .035, sx * .19, .225, sz * .19, M["jacaranda"], parent_col, g)
        box(name + "_Montante", .035, .45, .035, sx * .19, .69, -.19, M["jacaranda"], parent_col, g)
    box(name + "_Assento", .44, .04, .44, 0, .46, 0, M["palhinha"], parent_col, g)
    box(name + "_Encosto", .42, .14, .025, 0, .82, -.19, M["palhinha"], parent_col, g)
    return g

cadeira("Cadeira_1", C_JANT, x=.75, z=.05)
cadeira("Cadeira_2", C_JANT, x=1.65, z=.05)
cadeira("Cadeira_3", C_JANT, x=.75, z=1.55, ry=PI)

pend = grp("Pendente_Jantar", 1.2, 2.95, .8, C_JANT)
cyl("Pendente_Fio", .004, .004, 1.15, 0, -.575, 0, M["preto"], C_JANT, pend, 6)
bm = _bm()
bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=.26, calc_uvs=True)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
cup = finish("Pendente_Cupula", bm, V(0, -1.15, 0), M["pendente"], C_JANT, pend, smooth=True)
sol = cup.modifiers.new("Espessura", "SOLIDIFY"); sol.thickness = .006
sphere("Pendente_Lampada", .05, 0, -1.17, 0, M["lampada"], C_JANT, pend)

# ================================================================== COZINHA
box("Bancada_Fundo", 3.6, .88, .6, 4.2, .44, -3.7, M["freijo"], C_COZ)
box("Tampo_Fundo_Granito", 3.62, .04, .62, 4.2, .9, -3.7, M["granito"], C_COZ)
box("Bancada_Lateral", .6, .88, 4.8, 5.7, .44, -1.0, M["freijo"], C_COZ)
box("Tampo_Lateral_Granito", .62, .04, 4.82, 5.7, .9, -1.0, M["granito"], C_COZ)
box("Cuba_Inox", .44, .02, .6, 5.7, .915, -1.4, M["metal"], C_COZ)
cyl("Torneira", .012, .012, .3, 5.92, 1.07, -1.4, M["metal"], C_COZ, seg=8)
cyl("Torneira_Bica", .01, .01, .18, 5.84, 1.21, -1.4, M["metal"], C_COZ, seg=8, rz=PI / 2)
box("Prateleira_Cozinha", 3.2, .04, .3, 4.3, 2.1, -3.85, M["freijo"], C_COZ)
for i, c in enumerate(("#c79a4a", "#e8e1d2", "#7a8f5a", "#b85d3c", "#e8e1d2")):
    cyl("Pote_%d" % (i + 1), .05, .05, .14, 3.0 + i * .35, 2.19, -3.85, mat("Pote_%d" % i, c, .6), C_COZ, seg=14)
lathe("Filtro_de_Barro", [(0, 0), (.12, 0), (.15, .1), (.16, .22), (.13, .3), (.14, .32), (.15, .44), (.13, .55), (.06, .6), (.02, .64), (0, .64)],
      3.0, .92, -3.7, M["barro"], C_COZ)
cyl("Filtro_Torneirinha", .01, .01, .06, 3.0, 1.0, -3.54, M["metal"], C_COZ, seg=8, rx=PI / 2)
box("Geladeira", .7, 1.8, .7, 5.6, .9, 2.4, M["geladeira"], C_COZ)
box("Geladeira_Puxador", .02, .5, .04, 5.24, 1.2, 2.08, M["metal"], C_COZ)

# ================================================================== VARANDA: rede
a, b = V(-5.7, 1.9, 6.8), V(-2.1, 1.9, 6.8)
segT, segS = 40, 10; rv, rf, ruv = [], [], []
for i in range(segT + 1):
    t = i / segT; sag = math.sin(PI * t); w = .05 + .55 * sag ** .6
    for j in range(segS + 1):
        s = j / segS * 2 - 1
        rv.append((a.x + (b.x - a.x) * t, a.y - s * w, a.z - 1.0 * sag - .16 * (1 - s * s) * sag))
        ruv.append((t, (s + 1) / 2))
for i in range(segT):
    for j in range(segS):
        p = i * (segS + 1) + j; q = p + segS + 1
        rf.append((p, q, q + 1, p + 1))
rede = pydata("Rede", rv, rf, Vector((0, 0, 0)), M["rede"], C_VAR, uvs=ruv, smooth=True)
sol = rede.modifiers.new("Espessura", "SOLIDIFY"); sol.thickness = .008

# ================================================================== JARDIM
def palmeira(name, x, z, h):
    g = grp(name, x, 0, z, C_JARD, ry=rnd.random() * 2 * PI)
    cyl(name + "_Tronco", .1, .17, h, 0, h / 2, 0, M["tronco"], C_JARD, g, 10)
    fv, ff = [], []
    for k in range(10):
        m = Matrix.Translation((0, 0, h)) @ Matrix.Rotation(k / 10 * 2 * PI, 4, "Z") @ Matrix.Rotation(-(1.05 + rnd.random() * .35), 4, "X")
        base = len(fv)
        for sgi in range(7):
            L = sgi / 6 * 2.4
            for sx in (-.22, .22):
                fv.append(tuple(m @ Vector((sx * (1 - sgi / 7), L, -(L * L) * .12))))
        for sgi in range(6):
            p = base + sgi * 2
            ff.append((p, p + 1, p + 3, p + 2))
    pydata(name + "_Folhas", fv, ff, Vector((0, 0, 0)), M["folha"], C_JARD, g, smooth=True)

for i, (x, z) in enumerate(((-8, -7), (-4.5, -8.5), (3, -7.5), (8.5, 9.5), (-9.5, 9), (9.5, -3))):
    palmeira("Palmeira_%d" % (i + 1), x, z, 4.6 + rnd.random() * 1.5)
box("Muro_Frente_Esq", 14.7, 1.0, .25, -9.65, .5, 13.5, M["reboco"], C_JARD)
box("Muro_Frente_Dir", 14.7, 1.0, .25, 9.65, .5, 13.5, M["reboco"], C_JARD)
for sx in (-1, 1):
    box("Muro_Lateral", .2, 2.2, 25, sx * 17, 1.1, 1, M["reboco"], C_JARD)
box("Caminho_Entrada", 1.4, .02, 6.5, 0, .0, 10.25, M["concreto"], C_JARD)
box("Muro_Fundo", 34, 2.2, .2, 0, 1.1, -11.5, M["reboco"], C_JARD)
for i in range(14):
    side = 1 if i % 2 else -1
    r = .4 + rnd.random() * .4
    sphere("Arbusto_%02d" % i, r, side * (7 + rnd.random() * 4), .25, -9 + rnd.random() * 20, M["arbusto"], C_JARD, seg=12)

# ================================================================== VESTIGIOS
# cadeira tombada para tras
tomb = grp("V_Cadeira_Tombada", 1.95, 0, 2.25, C_VEST, ry=PI - .5)
c4 = cadeira("V_Cadeira_4", C_VEST, tomb, y=.24)
c4.rotation_euler = (-PI / 2, 0, 0)

# cacos do prato em leque (arremesso)
sv, sf = [], []
for i in range(16):
    r = .02 + rnd.random() * .05
    a = -.4 + rnd.random() * 1.6; d = rnd.random() * .8
    c = V(.05 + math.cos(a) * d, .004, 1.7 + math.sin(a) * d)
    m = Matrix.Translation(c) @ Matrix.Rotation(rnd.random() * 2 * PI, 4, "Z")
    base = len(sv)
    for p in ((0, 0), (r, rnd.random() * r * .4), (r * .3, r * (.6 + rnd.random() * .6))):
        sv.append(tuple(m @ Vector((p[0], p[1], 0))))
    sf.append((base, base + 1, base + 2))
cacos = pydata("V_Cacos_Prato", sv, sf, Vector((0, 0, 0)), M["ceramica"], C_VEST)
sol = cacos.modifiers.new("Espessura", "SOLIDIFY"); sol.thickness = .006

# copo derramado + bebida na mesa
cyl("V_Copo_Tombado", .035, .03, .11, 1.1, .81, 1.1, M["vidro"], C_VEST, seg=16, rz=PI / 2)
cyl("V_Bebida_Derramada", .18, .18, .002, 1.25, .776, 1.08, M["liquido"], C_VEST, seg=24).scale = (1, .6, 1)

# buraco de soco na parede (Boolean real na Parede_Esquerda_A)
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
for v in bm.verts:
    v.co *= .8 + rnd.random() * .4
bmesh.ops.scale(bm, vec=(.1, .2, .18), verts=bm.verts)
furo = as_cutter(finish("Cortador_Buraco_Parede", bm, V(-6.0, 1.5, .85), M["cortador"], C_CUT))
boolean(parede_esq, furo, "Buraco_Soco")
bm = _bm()
for i in range(16):
    s = .01 + rnd.random() * .03
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation(V(-5.9 + rnd.random() * .3, s * .3, .6 + rnd.random() * .5)) @ Matrix.Diagonal((s, s, s * .6, 1)))
finish("V_Reboco_Caido", bm, Vector((0, 0, 0)), M["reboco_marca"], C_VEST)

# marca do quadro arrancado + prego + porta-retrato quebrado no chao
box("V_Marca_Quadro_Parede", .002, .44, .34, -5.999, 1.7, .15, M["reboco_marca"], C_VEST)
cyl("V_Prego", .003, .003, .03, -5.99, 1.9, .15, M["metal"], C_VEST, seg=6, rz=PI / 2)
pr = grp("V_Porta_Retrato", -5.45, 0, .45, C_VEST, ry=.6)
box("V_Moldura", .34, .02, .42, 0, .01, 0, M["jacaranda"], C_VEST, pr)
box("V_Foto", .28, .002, .36, 0, .021, 0, M["foto"], C_VEST, pr)
gv, gf = [], []
for i in range(8):
    r = .02 + rnd.random() * .04
    c = V(-.3 + rnd.random() * .6, .003, -.3 + rnd.random() * .6); base = len(gv)
    for p in ((0, 0), (r, 0), (rnd.random() * r, r)):
        gv.append((c.x + p[0], c.y + p[1], c.z))
    gf.append((base, base + 1, base + 2))
pydata("V_Cacos_Vidro", gv, gf, Vector((0, 0, 0)), M["vidro"], C_VEST, pr)

# celular no chao, tela acesa com chamadas perdidas
cel = grp("V_Celular", -2.85, 0, .62, C_VEST, ry=2.3)
box("V_Celular_Corpo", .078, .009, .158, 0, .0045, 0, M["preto"], C_VEST, cel)
box("V_Celular_Tela", .07, .001, .148, 0, .0095, 0, M["celular_tela"], C_VEST, cel)
text("V_Celular_Hora", "23:47", .018, V(0, .0102, -.045), (0, 0, 0), M["texto_tela"], C_VEST, cel)
text("V_Celular_Aviso", "3 chamadas perdidas\nMãe", .0065, V(0, .0102, .0), (0, 0, 0), M["texto_tela"], C_VEST, cel)

# luminaria de piso derrubada em direcao ao corredor
base_l = V(-4.55, .015, 1.95)
cyl("V_Luminaria_Base", .16, .18, .03, -4.55, .015, 1.95, M["preto"], C_VEST)
d = V(-.6, 0, .8).normalized(); Lp = 1.35
haste = cyl("V_Luminaria_Haste", .013, .013, Lp, 0, 0, 0, M["latao"], C_VEST, seg=8)
haste.location = base_l + Vector((0, 0, .035)) + d * (Lp / 2); orient(haste, d)
ponta = base_l + Vector((0, 0, .19)) + d * Lp
cup = cyl("V_Luminaria_Cupula", .07, .2, .28, 0, 0, 0, M["cupula"], C_VEST, seg=24, caps=False)
cup.location = ponta; orient(cup, -d)
sol = cup.modifiers.new("Espessura", "SOLIDIFY"); sol.thickness = .004
bulbo = sphere("V_Luminaria_Lampada", .04, 0, 0, 0, M["lampada"], C_VEST); bulbo.location = ponta

box("V_Almofada_Jogada", .5, .14, .5, -3.0, .07, .35, M["tecido2"], C_VEST, rx=.1, ry=.7, rz=.15)
box("V_Controle_Remoto", .16, .02, .05, -4.1, .01, .6, M["preto"], C_VEST, ry=.4)
for i in range(4):
    box("V_Livro_Caido_%d" % (i + 1), .25, .04, .18, -5.3 + rnd.random() * .5, .02, -2.6 + rnd.random() * .6, LIVROS[i], C_VEST, ry=rnd.random() * PI)

# garrafas vazias
garrafa = [(0, 0), (.033, 0), (.034, .15), (.03, .18), (.013, .21), (.012, .25), (0, .25)]
for i in range(4):
    lathe("V_Garrafa_%d" % (i + 1), garrafa, 4.5 + i * .12, .92, -3.62 + (i % 2) * .08, M["garrafa"], C_VEST, seg=16)
g5 = lathe("V_Garrafa_Chao", garrafa, .9, .035, 2.8, M["garrafa"], C_VEST, seg=16)
g5.rotation_euler = (PI / 2, 0, .8)

# desenho de crianca na geladeira
box("V_Desenho_Crianca", .002, .33, .26, 5.245, 1.35, 2.45, M["papel"], C_VEST)
text("V_Desenho_Texto", "MINHA FAMÍLIA", .028, V(5.243, 1.215, 2.45), (PI / 2, 0, -PI / 2), M["giz"], C_VEST)
for i, (y, z, c) in enumerate(((1.51, 2.34, "#e74c3c"), (1.51, 2.56, "#f1c40f"))):
    cyl("V_Ima_%d" % (i + 1), .018, .018, .012, 5.24, y, z, mat("Ima_%d" % i, c, .4), C_VEST, seg=12, rz=PI / 2)

# mala feita as pressas
mala = grp("V_Mala", -4.6, 0, 3.3, C_VEST, ry=.35)
box("V_Mala_Base", .72, .1, .46, 0, .05, 0, M["mala"], C_VEST, mala)
tampa = grp("V_Mala_Tampa_Dobradica", 0, .1, -.23, C_VEST, parent=mala)
tampa.rotation_euler = (-1.9, 0, 0)
box("V_Mala_Tampa", .72, .08, .46, 0, .04, .23, M["mala"], C_VEST, tampa)
for i in range(7):
    box("V_Roupa_%d" % (i + 1), .28 + rnd.random() * .2, .035, .22 + rnd.random() * .12, -.18 + rnd.random() * .36, .11 + i * .018,
        -.08 + rnd.random() * .16, ROUPAS[i % 5], C_VEST, mala, ry=rnd.random() * .8 - .4)
box("V_Roupa_Chao", .5, .02, .3, .55, .01, .25, ROUPAS[2], C_VEST, mala, ry=.9)

# ursinho largado
urso = grp("V_Ursinho", -5.45, 0, 3.05, C_VEST, ry=1.2)
urso.rotation_euler[0] = 1.2
sphere("V_Urso_Corpo", .11, 0, .09, 0, M["pelucia"], C_VEST, urso, scale=(1, .8, 1.15))
sphere("V_Urso_Cabeca", .075, 0, .08, .17, M["pelucia"], C_VEST, urso)
for sx in (-1, 1):
    sphere("V_Urso_Orelha", .028, sx * .05, .14, .2, M["pelucia"], C_VEST, urso, seg=10)
    sphere("V_Urso_Pata", .04, sx * .1, .04, -.1, M["pelucia"], C_VEST, urso, seg=10)

# ================================================================== LUZES E CAMERAS
def light(name, kind, energy, color, loc, parent=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = hx(color)
    for k, v in kw.items():
        setattr(ld, k, v)
    ob = bpy.data.objects.new(name, ld); C_LUZ.objects.link(ob)
    if parent:
        ob.parent = parent
    ob.location = loc
    return ob

lua = light("Lua", "SUN", .9, "#aec4ff", V(-8, 10, -12), angle=.02)
lua.rotation_euler = (-V(-8, 10, -12)).to_track_quat("-Z", "Y").to_euler()
light("Luz_Pendente", "SPOT", 90, "#ffc98a", V(0, -1.18, 0), pend, spot_size=math.radians(110), spot_blend=.5)
light("Luz_Luminaria_Caida", "POINT", 35, "#ffb870", ponta + Vector((.03, .03, .02)), shadow_soft_size=.05)
tvl = light("Luz_TV", "AREA", 18, "#7a9fff", V(-5.6, .86, -1.1), size=1.0)
tvl.rotation_euler = (0, -PI / 2, 0)
light("Luz_Cozinha", "POINT", 20, "#fff0d0", V(4.2, 1.95, -3.5))

# ================================================================== RUA DO CONDOMINIO
# Daqui em diante as coordenadas estao no padrao do Blender (X, Y, Z-cima).
# A rua corre ao longo de X, na frente do muro da casa (Y negativo).
C_RUA = collection("07_Rua_Condominio")
C_VIZ = collection("07b_Casas_Vizinhas")
C_VEG = collection("07c_Grama_Vegetacao")
C_VIA = collection("10_Viatura_PMERJ")
C_CAR = collection("10b_Carros_Moradores")
C_NEB = collection("11_Neblina")

def bbox(name, sx, sy, sz, loc, material, col, parent=None, rot=(0, 0, 0), bevel=0.0):
    bm = _bm()
    bmesh.ops.create_cube(bm, size=1, calc_uvs=True)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    ob = finish(name, bm, Vector(loc), material, col, parent, rot)
    if bevel:
        md = ob.modifiers.new("Bevel", "BEVEL"); md.width = bevel; md.segments = 3
    return ob

def bcyl(name, r1, r2, depth, loc, material, col, parent=None, rot=(0, 0, 0), seg=24, caps=True):
    bm = _bm()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=depth, calc_uvs=True)
    return finish(name, bm, Vector(loc), material, col, parent, rot, smooth=True)

def revolve(name, prof, material, col, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), seg=48):
    ob = lathe(name, prof, 0, 0, 0, material, col, parent, seg)
    ob.location = Vector(loc); ob.rotation_euler = rot
    return ob

def array(ob, name, off, count):
    md = ob.modifiers.new(name, "ARRAY")
    md.use_relative_offset = False; md.use_constant_offset = True
    md.constant_offset_displace = off; md.count = max(1, int(count))
    return md

def empty(name, loc, rz, col, parent=None):
    e = bpy.data.objects.new(name, None); e.empty_display_size = .6; col.objects.link(e)
    if parent:
        e.parent = parent
    e.location = loc; e.rotation_euler = (0, 0, rz)
    return e

def plight(name, kind, energy, color, loc, col, parent=None, rot=(0, 0, 0), **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = hx(color)
    for k, v in kw.items():
        setattr(ld, k, v)
    o = bpy.data.objects.new(name, ld); col.objects.link(o)
    if parent:
        o.parent = parent
    o.location = loc; o.rotation_euler = rot
    return o

def sock(node, name, typ=None, out=False):
    for s in (node.outputs if out else node.inputs):
        if s.name == name and (typ is None or s.type == typ):
            return s

# ------------------------------------------------------------------ materiais da rua
def asfalto_mat():
    """Asfalto seco: graos, manchas de desgaste e relevo fino."""
    m, nt, b = new_mat("Asfalto"); n = nt.nodes; L = nt.links.new
    tc = n.new("ShaderNodeTexCoord")
    grao = n.new("ShaderNodeTexNoise"); grao.inputs["Scale"].default_value = 420; grao.inputs["Detail"].default_value = 3
    mancha = n.new("ShaderNodeTexNoise"); mancha.inputs["Scale"].default_value = .18; mancha.inputs["Detail"].default_value = 5
    for t in (grao, mancha):
        L(tc.outputs["Object"], t.inputs["Vector"])
    cg = n.new("ShaderNodeValToRGB"); e = cg.color_ramp.elements
    e[0].color = (*lin(hx("#2a2a2c")), 1); e[1].color = (*lin(hx("#4a4946")), 1)
    L(grao.outputs["Fac"], cg.inputs["Fac"])
    cm = n.new("ShaderNodeValToRGB"); e = cm.color_ramp.elements
    e[0].position, e[0].color = .35, (.55, .55, .55, 1); e[1].position, e[1].color = .7, (1, 1, 1, 1)
    L(mancha.outputs["Fac"], cm.inputs["Fac"])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    sock(mix, "Factor", "VALUE").default_value = 1
    L(cg.outputs["Color"], sock(mix, "A", "RGBA")); L(cm.outputs["Color"], sock(mix, "B", "RGBA"))
    L(sock(mix, "Result", "RGBA", out=True), b.inputs["Base Color"])
    rg = n.new("ShaderNodeMapRange"); rg.inputs["To Min"].default_value = .8; rg.inputs["To Max"].default_value = .95
    L(mancha.outputs["Fac"], rg.inputs["Value"]); L(rg.outputs["Result"], b.inputs["Roughness"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = .45
    L(grao.outputs["Fac"], bump.inputs["Height"]); L(bump.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = (*lin(hx("#333333")), 1)
    return m

def brick_mat(name, c1, c2, cm, bw, rh, mortar, rough=.85, vertical=False, bump=.3):
    m, nt, b = new_mat(name); n = nt.nodes; L = nt.links.new
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
    if vertical:
        mp.inputs["Rotation"].default_value = (PI / 2, 0, 0)
    br = n.new("ShaderNodeTexBrick"); br.offset = .5
    L(tc.outputs["Object"], mp.inputs["Vector"]); L(mp.outputs["Vector"], br.inputs["Vector"])
    br.inputs["Color1"].default_value = (*lin(hx(c1)), 1)
    br.inputs["Color2"].default_value = (*lin(hx(c2)), 1)
    br.inputs["Mortar"].default_value = (*lin(hx(cm)), 1)
    br.inputs["Scale"].default_value = 1
    br.inputs["Mortar Size"].default_value = mortar
    br.inputs["Brick Width"].default_value = bw
    br.inputs["Row Height"].default_value = rh
    L(br.outputs["Color"], b.inputs["Base Color"]); si(b, "Roughness", rough)
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.invert = True
    L(br.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = (*lin(hx(c1)), 1)
    return m

def janela_mat(name, color, strength):
    """Janela acesa vista de fora: cortina com pregas iluminada por dentro."""
    m, nt, b = new_mat(name); n = nt.nodes; L = nt.links.new
    tc = n.new("ShaderNodeTexCoord"); wv = n.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 18; wv.inputs["Distortion"].default_value = 1.5
    L(tc.outputs["Object"], wv.inputs["Vector"])
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = strength * .45; mr.inputs["To Max"].default_value = strength
    L(wv.outputs["Fac"], mr.inputs["Value"]); L(mr.outputs["Result"], b.inputs["Emission Strength"])
    si(b, "Emission Color", (*lin(hx(color)), 1)); si(b, "Base Color", (0, 0, 0, 1)); si(b, "Roughness", .15)
    m.diffuse_color = (*lin(hx(color)), 1)
    return m

def folhagem_mat(name, c1, c2):
    m, nt, b = new_mat(name); n = nt.nodes; L = nt.links.new
    tc = n.new("ShaderNodeTexCoord"); nz = n.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3; nz.inputs["Detail"].default_value = 6
    L(tc.outputs["Object"], nz.inputs["Vector"])
    rp = n.new("ShaderNodeValToRGB"); e = rp.color_ramp.elements
    e[0].color = (*lin(hx(c1)), 1); e[1].color = (*lin(hx(c2)), 1)
    L(nz.outputs["Fac"], rp.inputs["Fac"]); L(rp.outputs["Color"], b.inputs["Base Color"])
    fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 60
    L(tc.outputs["Object"], fine.inputs["Vector"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .6
    L(fine.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    si(b, "Roughness", .75)
    m.diffuse_color = (*lin(hx(c1)), 1)
    return m

def grama_mat():
    m, nt, b = new_mat("Grama_Folhas"); n = nt.nodes; L = nt.links.new
    oi = n.new("ShaderNodeObjectInfo"); rp = n.new("ShaderNodeValToRGB")
    e = rp.color_ramp.elements
    e[0].color = (*lin(hx("#2f5a24")), 1); e[1].color = (*lin(hx("#7d8a3e")), 1)
    mid = e.new(.55); mid.color = (*lin(hx("#4d7a2c")), 1)
    L(oi.outputs["Random"], rp.inputs["Fac"]); L(rp.outputs["Color"], b.inputs["Base Color"])
    si(b, "Roughness", .5)
    m.diffuse_color = (*lin(hx("#4d7a2c")), 1)
    return m

def tex_calcada(S=1024):
    """Calcada portuguesa em ondas (padrao Copacabana), 1 tile = 2 m."""
    y, x = np.mgrid[0:S, 0:S] / S
    onda = ((y * 3 + .22 * np.sin(2 * PI * x * 2)) % 1) < .5
    a = np.where(onda[..., None], np.array(hx("#1f1f1f")), np.array(hx("#e6e1d6")))
    px, py = x * S, y * S
    pedra = ((px % 12) < 1.6) | (((py + (np.floor(px / 12) % 2) * 6) % 12) < 1.6)
    a = np.where(pedra[..., None], a * .55 + .12, a)
    a = a + np.random.default_rng(5).normal(0, .035, (S, S, 1))
    return np.clip(a, 0, 1)

def tex_zebrado(S=256):
    y, x = np.mgrid[0:S, 0:S] / S
    return np.where((((x + y) * 4) % 1 < .5)[..., None], np.array(hx("#e8b400")), np.array(hx("#151515")))

MR = {
    "asfalto": asfalto_mat(),
    "remendo": mat("Asfalto_Remendo", "#1f1f21", .9),
    "calcada": img_mat("Calcada_Portuguesa", np_image("calcada", tex_calcada()), 2.0, .6),
    "zebrado": img_mat("Zebrado_Amarelo_Preto", np_image("zebrado", tex_zebrado()), .8, .5),
    "meiofio": mat("Meio_Fio_Concreto", "#a19c93", .9),
    "sarjeta": mat("Sarjeta_Concreto", "#7d7a74", .92),
    "faixa": mat("Pintura_Faixa", "#e9e6dc", .5),
    "poste": mat("Poste_Metal", "#3b3d40", .45, .7),
    "led": mat("LED_Poste", "#ffffff", .3, emit="#ffd9a8", emit_str=40),
    "janela_quente": janela_mat("Janela_Acesa_Quente", "#ffc98a", 5),
    "janela_fria": janela_mat("Janela_Acesa_Fria", "#dfe8ff", 3.5),
    "janela_tv": janela_mat("Janela_Luz_TV", "#8fb0ff", 2.5),
    "janela_apagada": mat("Vidro_Janela_Apagada", "#0d1216", .04),
    "caixilho": mat("Caixilho_Aluminio_Preto", "#1c1d1f", .35, .6),
    "portao": mat("Portao_Ferro", "#23262a", .5, .6),
    "fach_branca": mat("Fachada_Branca", "#e9e4da", .9),
    "fach_cinza": mat("Fachada_Cimento_Queimado", "#8f8b84", .7),
    "fach_terra": mat("Fachada_Terracota", "#b0674a", .9),
    "fach_areia": mat("Fachada_Areia", "#d7c7a8", .9),
    "pedra_escura": mat("Pedra_Escura_Rodape", "#3a3835", .6),
    "pedra_clara": mat("Pedra_Sao_Tome", "#d8c9a6", .8),
    "filete": brick_mat("Filete_de_Pedra", "#c2b29a", "#8a7d6b", "#5b5247", .32, .055, .004, .9, vertical=True, bump=.8),
    "intertravado": brick_mat("Piso_Intertravado", "#8e8880", "#6f6962", "#4a4642", .2, .1, .006, .85),
    "vidro_guarda": mat("Vidro_Guarda_Corpo", "#9fc0c8", .03, alpha=.25),
    "caixa_dagua": mat("Caixa_dAgua_Fibra_Azul", "#2f6fb2", .45),
    "solar": mat("Coletor_Solar", "#18223a", .1, .3),
    "branco_ac": mat("Ar_Condicionado_Branco", "#e8e8e6", .45),
    "folhagem": folhagem_mat("Folhagem", "#1f3a1e", "#3f6b2e"),
    "folhagem_escura": folhagem_mat("Folhagem_Escura", "#132614", "#2a4a22"),
    "ipe": folhagem_mat("Flores_Ipe_Amarelo", "#d9a90c", "#f5d423"),
    "solo": mat("Solo_Grama", "#2c351d", 1),
    "terra": mat("Terra_Canteiro", "#3b2e22", 1),
    "numero": mat("Numero_Latao", "#b08a45", .3, 1),
    "arandela": mat("Arandela_Acesa", "#ffffff", .3, emit="#ffcf8a", emit_str=15),
    "placa_branca": mat("Placa_Branca", "#f2f2f0", .4),
    "placa_vermelha": mat("Placa_Vermelha", "#c01818", .4),
    "placa_preta": mat("Placa_Texto_Preto", "#111111", .5),
    "hidrante": mat("Hidrante_Vermelho", "#b3161b", .35),
    "amarelo": mat("Placa_Amarela", "#f2c200", .4),
}
TEX_FOLHA = bpy.data.textures.new("Folhagem_Ruido", "CLOUDS"); TEX_FOLHA.noise_scale = .22

# ------------------------------------------------------------------ grama (Geometry Nodes)
bv, bf = [], []
for k in range(7):
    a = rnd.random() * 2 * PI; lean = .02 + rnd.random() * .05; h = .07 + rnd.random() * .07
    ox, oy = rnd.uniform(-.03, .03), rnd.uniform(-.03, .03)
    px, py = -math.sin(a), math.cos(a); base = len(bv); segs = 4
    for t in range(segs + 1):
        s = t / segs; w = .0045 * (1 - s) + .0004
        cx, cy, cz = ox + lean * s * s * math.cos(a), oy + lean * s * s * math.sin(a), h * s
        bv.append((cx - px * w, cy - py * w, cz)); bv.append((cx + px * w, cy + py * w, cz))
    for t in range(segs):
        p = base + t * 2
        bf.append((p, p + 1, p + 3, p + 2))
tufo = pydata("Fonte_Tufo_Grama", bv, bf, Vector((0, 0, 0)), grama_mat(), C_CUT, smooth=True)

GRAMA_NG = bpy.data.node_groups.new("Grama_Instancias", "GeometryNodeTree")
GRAMA_NG.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
sd = GRAMA_NG.interface.new_socket(name="Densidade", in_out="INPUT", socket_type="NodeSocketFloat"); sd.default_value = 250
GRAMA_NG.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
GRAMA_ID = sd.identifier
_n = GRAMA_NG.nodes; _l = GRAMA_NG.links.new
gi = _n.new("NodeGroupInput"); go = _n.new("NodeGroupOutput")
isv = _n.new("GeometryNodeIsViewport")
mulv = _n.new("ShaderNodeMath"); mulv.operation = "MULTIPLY"; mulv.inputs[1].default_value = .03
_l(gi.outputs["Densidade"], mulv.inputs[0])
sw = _n.new("GeometryNodeSwitch"); sw.input_type = "FLOAT"
_l(isv.outputs[0], sw.inputs["Switch"]); _l(gi.outputs["Densidade"], sw.inputs["False"]); _l(mulv.outputs[0], sw.inputs["True"])
dist = _n.new("GeometryNodeDistributePointsOnFaces")
_l(gi.outputs["Geometry"], dist.inputs["Mesh"]); _l(sw.outputs[0], dist.inputs["Density"])
oi = _n.new("GeometryNodeObjectInfo"); oi.inputs["Object"].default_value = tufo; oi.transform_space = "ORIGINAL"
inst = _n.new("GeometryNodeInstanceOnPoints")
_l(dist.outputs["Points"], inst.inputs["Points"]); _l(oi.outputs["Geometry"], inst.inputs["Instance"])
rv = _n.new("FunctionNodeRandomValue"); rv.data_type = "FLOAT_VECTOR"
sock(rv, "Min", "VECTOR").default_value = (-.15, -.15, 0); sock(rv, "Max", "VECTOR").default_value = (.15, .15, 2 * PI)
rs = _n.new("FunctionNodeRandomValue"); rs.data_type = "FLOAT"
sock(rs, "Min", "VALUE").default_value = .55; sock(rs, "Max", "VALUE").default_value = 1.4; sock(rs, "Seed", "INT").default_value = 7
_l(sock(rv, "Value", "VECTOR", out=True), inst.inputs["Rotation"]); _l(sock(rs, "Value", "VALUE", out=True), inst.inputs["Scale"])
join = _n.new("GeometryNodeJoinGeometry")
_l(inst.outputs["Instances"], join.inputs[0]); _l(gi.outputs["Geometry"], join.inputs[0])
_l(join.outputs[0], go.inputs["Geometry"])

_GRAMA_CACHE = {}
def grama_ng(dens):
    """Uma copia do node group por densidade (tufos por m2 no render; 3% no viewport)."""
    key = int(dens)
    if key not in _GRAMA_CACHE:
        ng = GRAMA_NG.copy(); ng.name = "Grama_Instancias_%d" % key
        for it in ng.interface.items_tree:
            if getattr(it, "name", "") == "Densidade":
                it.default_value = float(key)
        _GRAMA_CACHE[key] = ng
    return _GRAMA_CACHE[key]

def lawn(name, x0, x1, y0, y1, z, col, parent=None, holes=(), cell=.5, dens=260):
    nx = max(1, int(round((x1 - x0) / cell))); ny = max(1, int(round((y1 - y0) / cell)))
    vs = [(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, z) for j in range(ny + 1) for i in range(nx + 1)]
    fs = []
    for j in range(ny):
        for i in range(nx):
            cx = x0 + (x1 - x0) * (i + .5) / nx; cy = y0 + (y1 - y0) * (j + .5) / ny
            if any(a <= cx <= b and c <= cy <= d for a, b, c, d in holes):
                continue
            p = j * (nx + 1) + i
            fs.append((p, p + 1, p + nx + 2, p + nx + 1))
    ob = pydata(name, vs, fs, Vector((0, 0, 0)), MR["solo"], col, parent)
    md = ob.modifiers.new("Grama", "NODES"); md.node_group = grama_ng(dens)
    return ob

# ------------------------------------------------------------------ vegetacao
def shrub(name, loc, r, col, parent=None, material=None, squash=.8):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    ob = finish(name, bm, Vector(loc), material or MR["folhagem"], col, parent, smooth=True)
    ob.scale = (1, 1, squash)
    d = ob.modifiers.new("Folhas", "DISPLACE"); d.texture = TEX_FOLHA; d.strength = r * .45; d.texture_coords = "GLOBAL"
    return ob

def hedge(name, sx, sy, sz, loc, col, parent=None):
    ob = bbox(name, sx, sy, sz, loc, MR["folhagem_escura"], col, parent)
    rm = ob.modifiers.new("Volume", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = .07; rm.use_smooth_shade = True
    d = ob.modifiers.new("Folhas", "DISPLACE"); d.texture = TEX_FOLHA; d.strength = .14; d.texture_coords = "GLOBAL"
    return ob

def palm_b(name, loc, h, col, parent=None):
    g = empty(name, loc, rnd.random() * 2 * PI, col, parent)
    bcyl(name + "_Tronco", .12, .19, h, (0, 0, h / 2), M["tronco"], col, g, seg=14)
    bcyl(name + "_Palmito", .15, .14, 1.0, (0, 0, h + .45), MR["folhagem"], col, g, seg=14)
    fv, ff = [], []
    for k in range(12):
        m = Matrix.Translation((0, 0, h + .9)) @ Matrix.Rotation(k / 12 * 2 * PI, 4, "Z") @ Matrix.Rotation(.25 + rnd.random() * .55, 4, "X")
        base = len(fv)
        for s in range(9):
            Lf = s / 8 * 2.8; wdt = .32 * math.sin(PI * min(1, s / 8 + .08))
            for sx in (-1, 1):
                fv.append(tuple(m @ Vector((sx * wdt, Lf, -(Lf * Lf) * .11 - abs(sx) * .03))))
        for s in range(8):
            p = base + s * 2
            ff.append((p, p + 1, p + 3, p + 2))
    pydata(name + "_Folhas", fv, ff, Vector((0, 0, 0)), M["folha"], col, g, smooth=True)
    return g

def arvore(name, loc, col, parent=None, flor=False):
    """Arvore procedural: galhos ramificados (tronco afinando) + folhas individuais."""
    rr = random.Random(sum(map(ord, name)) * 7919)
    larga = "Amendoeira" in name          # amendoeira: galhos em camadas horizontais
    g = empty(name, loc, rr.random() * 2 * PI, col, parent)
    wood, leaf = bmesh.new(), bmesh.new()
    def galho(p, d, L, r, depth):
        end = p + d * L
        m = Matrix.Translation((p + end) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(wood, cap_ends=False, segments=10 if depth > 2 else 6, radius1=r, radius2=r * .7, depth=L, matrix=m)
        if depth == 0:
            for k in range(34 if flor else 30):
                c = end + Vector((rr.gauss(0, .5), rr.gauss(0, .5), rr.gauss(.1, .3)))
                sz = rr.uniform(.07, .12) if flor else rr.uniform(.1, .17)
                q = Euler((rr.random() * PI, rr.random() * PI, rr.random() * PI)).to_matrix()
                vs = [leaf.verts.new(c + q @ (Vector(v) * sz)) for v in ((-1, -.45, 0), (0, -.6, .05), (1, 0, 0), (0, .6, .05), (-1, .45, 0))]
                leaf.faces.new(vs)
            return
        n = 3 if depth > 1 else rr.choice((2, 3))
        for i in range(n):
            ax = Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), 0))
            if ax.length < .1:
                ax = Vector((1, 0, 0))
            ang = rr.uniform(.7, 1.1) if larga else rr.uniform(.35, .75)
            nd = Matrix.Rotation(ang, 3, ax.normalized()) @ d
            nd.z = max(nd.z, .05 if larga else .2); nd.normalize()
            galho(end, nd, L * rr.uniform(.62, .8), r * .62, depth - 1)
    galho(Vector((0, 0, 0)), Vector((rr.uniform(-.08, .08), rr.uniform(-.08, .08), 1)).normalized(), 2.6 if larga else 2.3, .17, 4)
    finish(name + "_Galhos", wood, Vector((0, 0, 0)), M["tronco"], col, g, smooth=True)
    finish(name + "_Folhas", leaf, Vector((0, 0, 0)), MR["ipe"] if flor else MR["folhagem"], col, g)
    return g

# ------------------------------------------------------------------ pista, sarjeta, calcadas e canteiros
bbox("Asfalto", 90, 7.25, .1, (0, -20.5, -.05), MR["asfalto"], C_RUA)
for i in range(7):
    r = bbox("Asfalto_Remendo_%d" % (i + 1), rnd.uniform(.8, 2.4), rnd.uniform(.5, 1.4), .004,
             (rnd.uniform(-30, 30), rnd.uniform(-23.5, -17.5), .002), MR["remendo"], C_RUA)
    r.rotation_euler[2] = rnd.uniform(-.1, .1)
for i in range(-11, 12):
    bbox("Faixa_Central", 1.6, .1, .004, (i * 4.0, -20.5, .002), MR["faixa"], C_RUA)
bbox("Lombada", .9, 7.2, .09, (-15, -20.5, 0), MR["zebrado"], C_RUA, bevel=.04)
for side, yc, yc_s, y_can, y_walk, w_walk in ((1, -16.8, -17.05, -16.2625, -14.7125, 2.175), (-1, -24.2, -23.95, -24.7375, -26.25, 2.1)):
    bbox("Meio_Fio", 90, .15, .25, (0, yc, .025), MR["meiofio"], C_RUA, bevel=.02)
    bbox("Sarjeta", 90, .35, .012, (0, yc_s, .002), MR["sarjeta"], C_RUA)
    bbox("Canteiro_Terra", 90, .925, .22, (0, y_can, .01), MR["terra"], C_RUA)
    lawn("Canteiro_Grama", -45, 45, y_can - .46, y_can + .46, .121, C_VEG, cell=1.0, dens=230)
    bbox("Calcada", 90, w_walk, .25, (0, y_walk, -.025), MR["calcada"], C_RUA)
    for x in (-30, -12, 10, 27):   # bueiros de grelha
        g = bbox("Bueiro_Grelha", .9, .32, .015, (x, yc_s, .01), MR["portao"], C_RUA)
        s = bbox("Bueiro_Fenda", .8, .025, .02, (x, yc_s - .12, .012), MR["preto"] if "preto" in MR else M["preto"], C_RUA)
        array(s, "Fendas", (0, .06, 0), 5)
bcyl("Tampa_Esgoto", .34, .34, .02, (6, -21.3, .005), MR["portao"], C_RUA, seg=32)
bcyl("Tampa_Esgoto_Anel", .38, .38, .012, (6, -21.3, .003), MR["sarjeta"], C_RUA, seg=32)

# ------------------------------------------------------------------ postes LED
def poste(name, x, y, dir_y):
    bcyl(name + "_Base", .16, .18, .35, (x, y, .3), MR["sarjeta"], C_RUA, seg=16)
    bcyl(name + "_Coluna", .09, .065, 7.2, (x, y, 3.75), MR["poste"], C_RUA, seg=16)
    bcyl(name + "_Braco", .04, .04, 1.6, (x, y + dir_y * .8, 7.2), MR["poste"], C_RUA, rot=(PI / 2, 0, 0), seg=10)
    bbox(name + "_Luminaria", .38, .8, .1, (x, y + dir_y * 1.7, 7.17), MR["poste"], C_RUA, bevel=.035)
    bbox(name + "_LED", .3, .64, .01, (x, y + dir_y * 1.7, 7.115), MR["led"], C_RUA)
    plight(name + "_Luz", "SPOT", 2200, "#ffd6a0", (x, y + dir_y * 1.7, 7.09), C_RUA,
           spot_size=math.radians(135), spot_blend=.8, shadow_soft_size=.2)
for i, x in enumerate((-22, -8, 6, 20, 34)):
    poste("Poste_%d" % (i + 1), x, -16.25, -1)
for i, x in enumerate((-15, 13, 29)):
    poste("Poste_Oposto_%d" % (i + 1), x, -24.75, 1)

# ------------------------------------------------------------------ mobiliario urbano
def lixeira(name, x, y):
    bcyl(name + "_Poste", .03, .03, 1.15, (x, y, .7), MR["portao"], C_RUA, seg=10)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=18, radius1=.24, radius2=.27, depth=.42)
    vert = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > .1]
    bmesh.ops.subdivide_edges(bm, edges=vert, cuts=4)
    ob = finish(name + "_Cesto", bm, Vector((x, y - .3, 1.28)), MR["portao"], C_RUA)
    w = ob.modifiers.new("Grade", "WIREFRAME"); w.thickness = .008
    bcyl(name + "_Suporte", .015, .015, .3, (x, y - .15, 1.28), MR["portao"], C_RUA, rot=(PI / 2, 0, 0), seg=8)
for x in (-9.5, 14, 26):
    lixeira("Lixeira_Suspensa", x, -14.0)
lixeira("Lixeira_Suspensa_Oposta", -12.5, -26.9)

def placa_velocidade(name, x, y, rz):
    g = empty(name, (x, y, 0), rz, C_RUA)
    bcyl(name + "_Poste", .03, .03, 2.6, (0, 0, 1.3), MR["poste"], C_RUA, g, seg=10)
    bcyl(name + "_Aro", .3, .3, .02, (0, -.04, 2.35), MR["placa_vermelha"], C_RUA, g, rot=(PI / 2, 0, 0), seg=40)
    bcyl(name + "_Fundo", .24, .24, .022, (0, -.045, 2.35), MR["placa_branca"], C_RUA, g, rot=(PI / 2, 0, 0), seg=40)
    text(name + "_Texto", "20", .22, Vector((0, -.058, 2.3)), (PI / 2, 0, 0), MR["placa_preta"], C_RUA, g)
    text(name + "_km", "km/h", .06, Vector((0, -.058, 2.2)), (PI / 2, 0, 0), MR["placa_preta"], C_RUA, g)
placa_velocidade("Placa_20kmh", -26, -16.3, 0)
placa_velocidade("Placa_20kmh_Oposta", 22, -24.7, PI)
revolve("Hidrante", [(0, 0), (.14, 0), (.14, .06), (.1, .08), (.1, .55), (.12, .6), (.1, .68), (.06, .74), (0, .76)],
        MR["hidrante"], C_RUA, loc=(16, -16.3, .12), seg=24)

# guarita e cancela na entrada do condominio
gu = empty("Guarita_Portaria", (40.5, -14.6, .15), 0, C_RUA)
bbox("Guarita_Corpo", 3.2, 2.6, 2.7, (0, 0, 1.35), MR["fach_branca"], C_RUA, gu)
bbox("Guarita_Laje", 4.0, 3.4, .2, (0, 0, 2.8), M["concreto"], C_RUA, gu)
bbox("Guarita_Janela", 2.6, .02, 1.1, (0, -1.31, 1.6), MR["janela_fria"], C_RUA, gu)
bbox("Guarita_Peitoril", 2.8, .2, .05, (0, -1.38, 1.02), MR["pedra_clara"], C_RUA, gu)
text("Guarita_Letreiro", "PORTARIA", .22, Vector((0, -1.72, 2.72)), (PI / 2, 0, 0), MR["numero"], C_RUA, gu)
plight("Guarita_Luz", "SPOT", 150, "#ffe2b8", (0, -1.4, 2.65), C_RUA, gu, spot_size=math.radians(120), spot_blend=.7)
bbox("Cancela_Base", .35, .35, 1.0, (38.3, -16.6, .5), MR["zebrado"], C_RUA)
bbox("Cancela_Braco", .08, 6.6, .08, (38.3, -20.0, 1.0), MR["zebrado"], C_RUA)

# arvores dos canteiros
arvore("Amendoeira_1", (-11, -24.74, .12), C_VEG)
arvore("Ipe_Amarelo", (9, -24.74, .12), C_VEG, flor=True)
arvore("Amendoeira_2", (25, -16.26, .12), C_VEG)
palm_b("Palmeira_Canteiro", (-14, -16.26, .12), 6.5, C_VEG)

# ------------------------------------------------------------------ frente da nossa casa
for sx in (-1, 1):
    bbox("Pilar_Portao", .3, .3, 2.4, (sx * 2.15, -13.5, 1.2), M["reboco"], C_RUA)
    bbox("Pilar_Portao_Chapim", .36, .36, .05, (sx * 2.15, -13.5, 2.42), M["concreto"], C_RUA)
text("Numero_147", "147", .16, Vector((2.15, -13.66, 1.55)), (PI / 2, 0, 0), MR["numero"], C_RUA)
bbox("Caixa_Correio", .3, .1, .22, (2.15, -13.71, 1.1), MR["portao"], C_RUA, bevel=.01)
bbox("Interfone", .1, .03, .16, (-2.15, -13.665, 1.45), MR["caixilho"], C_RUA, bevel=.005)
bbox("Arandela_Portao", .14, .08, .2, (-2.15, -13.7, 2.0), MR["arandela"], C_RUA)
plight("Luz_Arandela", "POINT", 25, "#ffc98a", (-2.15, -13.85, 2.0), C_RUA, shadow_soft_size=.05)

def folha_portao(name, x_hinge, sign, ang):
    g = empty(name, (x_hinge, -13.5, 0), ang, C_RUA)
    w = 1.98
    for z in (.1, 1.0, 1.95):
        bbox(name + "_Travessa", w, .05, .05, (sign * w / 2, 0, z), MR["portao"], C_RUA, g)
    for xx in (.03, w - .03):
        bbox(name + "_Montante", .05, .05, 1.95, (sign * xx, 0, 1.0), MR["portao"], C_RUA, g)
    barra = bcyl(name + "_Barras", .012, .012, 1.85, (sign * .12, 0, 1.03), MR["portao"], C_RUA, g, seg=8)
    array(barra, "Barras", (sign * .11, 0, 0), 17)
folha_portao("Portao_Folha_Esq", -2.0, 1, .9)   # entreaberta
folha_portao("Portao_Folha_Dir", 2.0, -1, 0)
for sx in (-1, 1):   # gradil sobre o muro baixo
    bbox("Gradil_Travessa", 14.6, .04, .04, (sx * 9.7, -13.5, 2.15), MR["portao"], C_RUA)
    grd = bcyl("Gradil_Barras", .011, .011, 1.15, (sx * 2.4, -13.5, 1.575), MR["portao"], C_RUA, seg=8)
    array(grd, "Barras", (sx * .12, 0, 0), 121)
    hedge("Cerca_Viva", 14.2, .6, 1.0, (sx * 9.7, -12.95, .45), C_VEG)
for y in (-12.6, -11.0, -9.4, -7.8):
    for sx in (-1, 1):
        bcyl("Balizador", .045, .045, .45, (sx * .95, y, .225), MR["caixilho"], C_RUA, seg=12)
        bcyl("Balizador_Luz", .047, .047, .04, (sx * .95, y, .47), MR["arandela"], C_RUA, seg=12)
    plight("Balizador_Luz", "POINT", 6, "#ffc98a", (.95, y, .5), C_RUA, shadow_soft_size=.02)
lawn("Grama_Lote", -16.85, 16.85, -13.3, 11.35, -.095, C_VEG,
     holes=((-6.7, 6.7, -7.15, 4.5), (-.8, .8, -13.4, -7.0)), cell=.5, dens=260)
for sx in (-1, 1):
    for k in range(3):
        shrub("Arbusto_Canteiro", (sx * (3.2 + k * 1.1), -7.7, .25), .45 + rnd.random() * .2, C_VEG)
for ob in list(C_JARD.objects):
    if ob.name.startswith("Arbusto_"):
        ob.data.materials.clear(); ob.data.materials.append(MR["folhagem"])
        d = ob.modifiers.new("Folhas", "DISPLACE"); d.texture = TEX_FOLHA; d.strength = .3; d.texture_coords = "GLOBAL"
# caixa d'agua e ar-condicionado da nossa casa
bcyl("Caixa_dAgua", .65, .6, .85, (4.2, 2.3, 3.68), MR["caixa_dagua"], C_EST, seg=32)
bcyl("Caixa_dAgua_Tampa", .66, .2, .22, (4.2, 2.3, 4.2), MR["caixa_dagua"], C_EST, seg=32)
bbox("Ar_Condicionado", .32, .85, .6, (6.37, 1.5, 2.3), MR["branco_ac"], C_EST, bevel=.02)
bcyl("Ar_Condicionado_Ventilador", .22, .22, .02, (6.54, 1.5, 2.3), MR["caixilho"], C_EST, rot=(0, PI / 2, 0), seg=28)
for dy in (-.3, .3):
    bbox("Ar_Condicionado_Suporte", .4, .04, .04, (6.4, 1.5 + dy, 1.98), MR["portao"], C_EST)

# ================================================================== CARROS (viatura e moradores)
COR_FAIXA = "#16275c"
COR_TEXTO = "#16275c"

def pintura(name, color, rough=.28):
    m, nt, b = new_mat(name)
    si(b, "Base Color", (*lin(hx(color)), 1)); si(b, "Roughness", rough)
    si(b, "Coat Weight", 1.0); si(b, "Coat Roughness", .03)
    m.diffuse_color = (*lin(hx(color)), 1)
    return m

def vidro_carro():
    m, nt, b = new_mat("Vidro_Carro_Fume")
    si(b, "Base Color", (*lin(hx("#1a2228")), 1)); si(b, "Roughness", .01)
    si(b, "Transmission Weight", .85); si(b, "IOR", 1.5)
    m.diffuse_color = (.02, .03, .04, 1)
    return m

MV = {
    "faixa": pintura("Pintura_Faixa_Azul", COR_FAIXA),
    "plastico": mat("Plastico_Preto_Texturizado", "#18191a", .65),
    "vidro": vidro_carro(),
    "black": mat("Preto_Brilhante", "#0b0b0c", .08),
    "cromo": mat("Cromado", "#d0d2d4", .08, 1),
    "pneu": mat("Borracha_Pneu", "#141414", .85),
    "roda": mat("Roda_Liga_Leve", "#a7abb0", .25, 1),
    "disco": mat("Disco_Freio", "#5a5c5e", .4, 1),
    "farol": mat("Farol_Aceso", "#ffffff", .1, emit="#eef3ff", emit_str=35),
    "farol_off": mat("Farol_Apagado", "#b9bec4", .04, .4),
    "lanterna": mat("Lanterna_Acesa", "#400000", .2, emit="#ff1a0f", emit_str=6),
    "lanterna_off": mat("Lanterna_Apagada", "#5a0a08", .12),
    "interior": mat("Interior_Carro", "#0e0e0f", .8),
    "texto": pintura("Adesivo_Texto", COR_TEXTO),
    "placa": mat("Placa_Mercosul", "#f4f4f2", .4),
    "placa_azul": mat("Placa_Faixa_Azul", "#1a3c8c", .4),
    "placa_txt": mat("Placa_Texto", "#111111", .5),
    "brasao": mat("Brasao_(inserir_imagem_oficial)", "#e9e3cf", .5),
    "dourado": mat("Dourado", "#c49a3a", .3, 1),
    "giro_verm": mat("Giroflex_Vermelho", "#300000", .1, emit="#ff1010", emit_str=0),
    "giro_azul": mat("Giroflex_Azul", "#000830", .1, emit="#1040ff", emit_str=0),
}

# carroceria tipo SUV compacto (proporcoes de Renault Duster, 4,34 x 1,82 m)
ST = [(2.17, .40, .70, .76, .78, .66), (2.08, .30, .80, .88, .87, .76), (1.75, .28, .88, .95, .90, .79),
      (1.10, .28, .98, 1.06, .91, .80), (.50, .28, 1.00, 1.62, .91, .72), (-.35, .28, 1.01, 1.66, .91, .72),
      (-.50, .28, 1.01, 1.66, .91, .72), (-1.55, .28, 1.02, 1.64, .91, .72), (-1.95, .30, 1.00, 1.56, .90, .70),
      (-2.12, .34, .96, 1.12, .86, .68), (-2.17, .42, .88, 1.00, .80, .62)]

def matidx(seg, band):
    if band <= 1: return 2
    if band == 2: return 1
    if band == 3: return 0
    if band == 4:
        if seg in (4, 6, 7): return 3
        if seg in (3, 5, 8): return 4
        return 0
    return 3 if seg in (3, 8) else 0

def half(s):
    x, zb, zbelt, ztop, hw, hwt = s
    zl = zb + (zbelt - zb) * .45
    return [(0, zb), (hw * .88, zb), (hw, zb + .10), (hw, zl), (hw * .99, zbelt), (hwt, ztop - .07), (hwt * .8, ztop), (0, ztop)]

PNEU = [(.205, -.1), (.29, -.108), (.33, -.1), (.345, -.07), (.349, 0), (.345, .07), (.33, .1), (.29, .108), (.205, .1)]
ARO = [(0, .09), (.05, .09), (.06, .075), (.19, .075), (.207, .09), (.207, -.08), (.19, -.09)]

def carro(name, loc, rz, cor, policia=False, farois=False, parent=None, placa="BRA2E19"):
    col = C_VIA if policia else C_CAR
    car = empty(name, loc, rz, col, parent); car.empty_display_type = "ARROWS"
    pint = pintura(name + "_Pintura", cor)
    mats = [pint, MV["faixa"] if policia else pintura(name + "_Pintura_Faixa", cor), MV["plastico"], MV["vidro"], MV["black"]]
    bm = bmesh.new(); rings = []; N = 14
    for s in ST:
        h = half(s)
        pts = h + [(-y, z) for (y, z) in reversed(h[1:7])]
        rings.append([bm.verts.new((s[0], y, z)) for (y, z) in pts])
    for i in range(len(ST) - 1):
        for k in range(N):
            k2 = (k + 1) % N
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            f.material_index = matidx(i, k if k < 7 else 13 - k)
    for ring in (rings[0], rings[-1]):
        c = bm.verts.new((ring[0].co.x, 0, (ring[0].co.z + ring[7].co.z) / 2))
        for k in range(N):
            bm.faces.new((ring[k], ring[(k + 1) % N], c)).material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cl = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    for i in range(len(ST) - 1):
        for k in (2, 4, 5, 12, 10, 9):
            e = bm.edges.get((rings[i][k], rings[i + 1][k]))
            if e: e[cl] = .85
    for si_ in (0, 3, 4, 8, len(ST) - 1):
        for k in range(N):
            e = bm.edges.get((rings[si_][k], rings[si_][(k + 1) % N]))
            if e and (si_ in (0, len(ST) - 1) or 4 <= k <= 9):
                e[cl] = .7
    me = bpy.data.meshes.new(name + "_Carroceria"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    for mt in mats: me.materials.append(mt)
    body = bpy.data.objects.new(name + "_Carroceria", me); col.objects.link(body); body.parent = car
    sub = body.modifiers.new("Suavizar", "SUBSURF"); sub.levels = 2; sub.render_levels = 3
    bm = _bm()
    for x in (1.33, -1.34):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=.41, radius2=.41, depth=2.4,
                              matrix=Matrix.Translation((x, 0, .36)) @ Matrix.Rotation(PI / 2, 4, "X"))
    arcos = as_cutter(finish(name + "_Cortador_Caixas_Roda", bm, Vector((0, 0, 0)), M["cortador"], C_CUT, parent=car))
    boolean(body, arcos, "Caixas_de_Roda")
    for x in (1.33, -1.34):
        bcyl(name + "_Forro_Caixa_Roda", .405, .405, 1.6, (x, 0, .36), MV["plastico"], col, car, rot=(PI / 2, 0, 0), seg=40, caps=False)
    bbox(name + "_Interior", 2.6, 1.6, 1.0, (-.4, 0, 1.0), MV["interior"], col, car)
    for sx in (-1, 1):
        bbox(name + "_Banco", .5, .5, .7, (0, sx * .38, .95), MV["interior"], col, car)
    bcyl(name + "_Volante", .19, .19, .03, (.75, -.38, 1.05), MV["black"], col, car, rot=(0, -1.1, 0), seg=24)

    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    def surf(x, z, side):
        ok, lc, nrm, _ = ev.ray_cast(Vector((x, side * 2.0, z)), Vector((0, -side, 0)))
        return lc.y if ok else side * .9
    def surf_x(y, z, end):
        ok, lc, nrm, _ = ev.ray_cast(Vector((end * 3.0, y, z)), Vector((-end, 0, 0)))
        return lc.x if ok else end * 2.17

    for x in (1.33, -1.34):   # arcos de plastico
        for side in (1, -1):
            vs, fs = [], []; A, T = 26, 8
            for i in range(A + 1):
                a = math.radians(-12 + 204 * i / A)
                for j in range(T):
                    b = 2 * PI * j / T; r = .43 + .035 * math.cos(b)
                    vs.append((x + r * math.cos(a), side * (.86 + .04 * math.sin(b)), .36 + r * math.sin(a)))
            for i in range(A):
                for j in range(T):
                    p, q = i * T + j, i * T + (j + 1) % T
                    fs.append((p, q, q + T, p + T))
            pydata(name + "_Arco_Roda", vs, fs, Vector((0, 0, 0)), MV["plastico"], col, car, smooth=True)
            g = empty(name + "_Roda", (x, side * .79, .349), 0, col, car)
            g.rotation_euler = (-side * PI / 2, 0, 0)
            revolve(name + "_Pneu", PNEU, MV["pneu"], col, g, seg=64)
            revolve(name + "_Aro", ARO, MV["roda"], col, g, seg=48)
            for k in range(5):
                a = 2 * PI * k / 5
                bbox(name + "_Raio", .15, .04, .025, (math.cos(a) * .12, math.sin(a) * .12, .085), MV["roda"], col, g, rot=(0, 0, a), bevel=.008)
            bcyl(name + "_Cubo", .045, .045, .03, (0, 0, .095), MV["cromo"], col, g, seg=20)
            bcyl(name + "_Disco", .15, .15, .02, (0, 0, -.02), MV["disco"], col, g, seg=32)

    bbox(name + "_Parachoque_Diant", .2, 1.72, .26, (2.12, 0, .45), MV["plastico"], col, car, bevel=.05)
    bbox(name + "_Protetor_Carter", .06, 1.0, .1, (2.22, 0, .35), MV["cromo"], col, car, bevel=.02)
    bbox(name + "_Grade", .05, 1.0, .19, (2.17, 0, .66), MV["black"], col, car, bevel=.03)
    bbox(name + "_Grade_Friso", .052, 1.0, .02, (2.19, 0, .66), MV["cromo"], col, car)
    bcyl(name + "_Emblema", .045, .045, .012, (2.2, 0, .66), MV["cromo"], col, car, rot=(0, PI / 2, 0), seg=24)
    for sy in (-.35, .3):
        bbox(name + "_Limpador", .02, .55, .015, (1.1, sy, 1.075), MV["black"], col, car, rot=(0, -.6, .12))
    bbox(name + "_Parachoque_Tras", .2, 1.7, .26, (-2.12, 0, .5), MV["plastico"], col, car, bevel=.05)
    for side in (1, -1):
        bbox(name + "_Farol", .08, .34, .13, (2.1, side * .6, .74), MV["farol"] if farois else MV["farol_off"], col, car, bevel=.03)
        bcyl(name + "_Farol_Milha", .045, .045, .03, (2.21, side * .64, .42), MV["farol"] if farois else MV["farol_off"], col, car, rot=(0, PI / 2, 0), seg=20)
        bbox(name + "_Lanterna", .06, .2, .28, (-2.14, side * .7, .9), MV["lanterna"] if farois else MV["lanterna_off"], col, car, bevel=.02)
        if farois:
            plight(name + "_Farol_Luz", "SPOT", 300, "#eef3ff", (2.2, side * .6, .74), col, car, rot=(0, -1.40, 0),
                   spot_size=math.radians(50), spot_blend=.6, shadow_soft_size=.06)
        bbox(name + "_Retrovisor", .16, .2, .12, (.5, side * 1.0, 1.08), pint, col, car, bevel=.03)
        bbox(name + "_Retrovisor_Base", .1, .12, .05, (.52, side * .9, 1.03), MV["plastico"], col, car)
        for xl in (.52, -.42, -1.5):
            y = surf(xl, .7, side)
            bbox(name + "_Friso_Porta", .005, .006, .62, (xl, y + side * .001, .7), MV["black"], col, car)
        for xh in (.05, -.95):
            y = surf(xh, .93, side)
            bbox(name + "_Macaneta", .13, .025, .03, (xh, y + side * .01, .93), MV["plastico"], col, car, bevel=.008)
        bcyl(name + "_Rack_Teto", .018, .018, 1.9, (-.55, side * .6, 1.655), MV["black"], col, car, rot=(0, PI / 2, 0), seg=10)
    for end, x0, z0 in ((1, 2.23, .47), (-1, -2.2, .56)):
        bbox(name + "_Placa", .01, .4, .13, (x0, 0, z0), MV["placa"], col, car)
        bbox(name + "_Placa_Faixa", .012, .4, .03, (x0 + end * .001, 0, z0 + .05), MV["placa_azul"], col, car)
        text(name + "_Placa_Texto", placa, .065, Vector((x0 + end * .007, 0, z0 - .035)), (PI / 2, 0, end * PI / 2), MV["placa_txt"], col, car)
    if not policia:
        return car

    # --- equipamentos da viatura
    bbox("Giroflex_Base", .34, 1.3, .06, (-.1, 0, 1.69), MV["black"], col, car, bevel=.02)
    for k in range(6):
        y = -.54 + k * .216
        bbox("Giroflex_Lente_%d" % (k + 1), .3, .2, .09, (-.1, y, 1.76), MV["giro_verm"] if y < 0 else MV["giro_azul"], col, car, bevel=.025)
    bcyl("Viatura_Antena", .004, .006, .45, (-1.7, 0, 1.85), MV["black"], col, car, seg=6)
    for side in (1, -1):   # adesivos (padrao aproximado; confira com fotos atuais da PMERJ)
        rot = (PI / 2, 0, PI) if side > 0 else (PI / 2, 0, 0)
        y = surf(-.97, .8, side)
        text("Adesivo_Policia_Militar", "POLÍCIA\nMILITAR", .1, Vector((-.97, y + side * .004, .86)), rot, MV["texto"], col, car)
        y = surf(-1.8, .8, side)
        text("Adesivo_190", "190", .17, Vector((-1.8, y + side * .004, .74)), rot, MV["texto"], col, car)
        y = surf(1.6, .78, side)
        text("Adesivo_PMERJ", "PMERJ", .07, Vector((1.62, y + side * .004, .76)), rot, MV["texto"], col, car)
        y = surf(.05, .8, side)
        bcyl("Brasao_Moldura", .115, .115, .004, (.05, y + side * .003, .8), MV["dourado"], col, car, rot=(PI / 2, 0, 0), seg=40)
        bcyl("Brasao_Imagem", .1, .1, .004, (.05, y + side * .005, .8), MV["brasao"], col, car, rot=(PI / 2, 0, 0), seg=40)
    xr = surf_x(0, 1.0, -1)
    text("Adesivo_Traseira", "POLÍCIA MILITAR · 190", .07, Vector((xr - .004, 0, 1.0)), (PI / 2, 0, -PI / 2), MV["texto"], col, car)
    lv_r = plight("Giroflex_Luz_Vermelha", "POINT", 0, "#ff1a10", (-.1, -.35, 1.9), col, car, shadow_soft_size=.08).data
    lv_b = plight("Giroflex_Luz_Azul", "POINT", 0, "#2050ff", (-.1, .35, 1.9), col, car, shadow_soft_size=.08).data
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
    except Exception:
        pass
    sr = MV["giro_verm"].node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"]
    sb = MV["giro_azul"].node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"]
    prev = None
    for f in range(1, 241):
        o = (f - 1) % 24
        red = o in (0, 1, 2, 6, 7, 8, 10, 11, 12)
        blue = o in (10, 11, 12, 14, 15, 16, 20, 21, 22)
        if (red, blue) != prev:
            for sk, ld, on in ((sr, lv_r, red), (sb, lv_b, blue)):
                sk.default_value = 18 if on else 0; sk.keyframe_insert("default_value", frame=f)
                ld.energy = 1800 if on else 0; ld.keyframe_insert("energy", frame=f)
            prev = (red, blue)
    return car

carro("Viatura_PMERJ", (3.4, -18.05, 0), PI + .07, "#f2f2ef", policia=True, farois=True, placa="RJP0M19")
carro("Carro_Rua_Vermelho", (15.5, -23.0, 0), .01, "#7d1414", placa="KXT4B21")

# ================================================================== CASAS VIZINHAS
# Cada casa e montada em coordenadas locais: rua em -Y, muro em y=0, lote para +Y.
def janela(nm, P, col, x0, x1, zc, h, yface, lit):
    w = x1 - x0; cx = (x0 + x1) / 2
    bbox(nm + "_Vidro", w - .08, .02, h - .08, (cx, yface - .01, zc), lit, col, P)
    for zz in (zc - h / 2, zc + h / 2):
        bbox(nm + "_Caixilho_H", w, .06, .05, (cx, yface - .03, zz), MR["caixilho"], col, P)
    n = max(1, int(round(w / 1.3)))
    for k in range(n + 1):
        bbox(nm + "_Caixilho_V", .05, .06, h, (x0 + w * k / n, yface - .03, zc), MR["caixilho"], col, P)
    bbox(nm + "_Peitoril", w + .12, .16, .04, (cx, yface - .08, zc - h / 2 - .03), MR["pedra_clara"], col, P)

def muro_trecho(nm, P, col, a, b, alto, fach):
    w = b - a; cx = (a + b) / 2
    if alto:
        bbox(nm, w, .2, 2.3, (cx, 0, 1.15), fach, col, P)
        bbox(nm + "_Chapim", w + .04, .28, .05, (cx, 0, 2.325), MR["pedra_clara"], col, P)
        n = max(2, int(w / 2.2) + 1)
        for k in range(n):
            bcyl(nm + "_Haste_Cerca", .008, .008, .55, (a + .1 + (w - .2) * k / (n - 1), 0, 2.62), MR["portao"], col, P, seg=6)
        for z in (2.45, 2.57, 2.69, 2.81):
            bcyl(nm + "_Fio_Cerca", .0025, .0025, w - .2, (cx, 0, z), MR["cromo"] if "cromo" in MR else MV["cromo"], col, P, rot=(0, PI / 2, 0), seg=4)
    else:
        bbox(nm, w, .25, .9, (cx, 0, .45), fach, col, P)
        bbox(nm + "_Chapim", w + .04, .32, .05, (cx, 0, .925), MR["pedra_clara"], col, P)
        grd = bcyl(nm + "_Gradil", .011, .011, 1.15, (a + .08, 0, 1.52), MR["portao"], col, P, seg=8)
        array(grd, "Barras", (.12, 0, 0), int((w - .1) / .12))
        bbox(nm + "_Gradil_Topo", w, .04, .04, (cx, 0, 2.1), MR["portao"], col, P)

def sala_interior(name, P, col, x0, x1, Y0, terreo, tv):
    """Recorta a fachada e monta uma sala mobiliada visivel da rua."""
    w = x1 - x0; cx = (x0 + x1) / 2; rw = w + .8; rd = 3.6; rh = 2.75
    yb = Y0 + .15 + rd            # parede do fundo
    bm = _bm()
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((cx, Y0 + .15 + rd / 2, .1 + rh / 2)) @ Matrix.Diagonal((rw, rd, rh, 1)))
    bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((cx, Y0, 1.45)) @ Matrix.Diagonal((w - .06, .5, 1.58, 1)))
    cut = as_cutter(finish(name + "_Cortador_Sala", bm, Vector((0, 0, 0)), M["cortador"], C_CUT, parent=P))
    md = boolean(terreo, cut, "Sala"); md.use_self = True
    tinta = mat(name + "_Tinta_Sala", rnd.choice(("#d9cfc0", "#b9c6bf", "#cdb9a2", "#c7c2d6")), .9)
    bbox(name + "_Sala_Piso", rw, rd, .02, (cx, Y0 + .15 + rd / 2, .11), M["jacaranda"], col, P)
    bbox(name + "_Sala_Parede_Fundo", rw, .02, rh, (cx, yb - .011, .1 + rh / 2), tinta, col, P)
    for sx in (-1, 1):
        bbox(name + "_Sala_Parede_Lat", .02, rd, rh, (cx + sx * (rw / 2 - .011), Y0 + .15 + rd / 2, .1 + rh / 2), tinta, col, P)
    bbox(name + "_Sala_Teto", rw, rd, .02, (cx, Y0 + .15 + rd / 2, .1 + rh - .011), M["reboco"], col, P)
    bbox(name + "_Sala_Tapete", 2.2, 1.5, .01, (cx, yb - 1.5, .125), M["tapete"], col, P)
    sw = min(2.4, rw - .8); tec = mat(name + "_Tecido_Sofa", rnd.choice(("#6b6f5a", "#8a5a44", "#3f4a5a", "#b8a88a")), .95)
    bbox(name + "_Sala_Sofa_Base", sw, .85, .4, (cx, yb - .5, .32), tec, col, P, bevel=.04)
    bbox(name + "_Sala_Sofa_Encosto", sw, .2, .45, (cx, yb - .12, .72), tec, col, P, bevel=.05)
    for sx in (-1, 1):
        bbox(name + "_Sala_Sofa_Braco", .18, .85, .55, (cx + sx * (sw / 2 - .09), yb - .5, .45), tec, col, P, bevel=.04)
    bbox(name + "_Sala_Mesa_Centro", 1.0, .55, .35, (cx, yb - 1.55, .3), M["freijo"], col, P, bevel=.01)
    arte = mat(name + "_Quadro", rnd.choice(("#c0492b", "#2a6f97", "#e3a92b", "#3d5a3a")), .6)
    bbox(name + "_Sala_Quadro_Moldura", 1.3, .03, .85, (cx, yb - .03, 1.75), M["preto"], col, P)
    bbox(name + "_Sala_Quadro", 1.2, .035, .75, (cx, yb - .035, 1.75), arte, col, P)
    lx = cx + rw / 2 - .45
    bcyl(name + "_Sala_Abajur_Haste", .015, .015, 1.4, (lx, yb - .45, .8), MR["caixilho"], col, P, seg=8)
    bcyl(name + "_Sala_Abajur_Cupula", .16, .2, .3, (lx, yb - .45, 1.55), MR["arandela"], col, P, seg=20)
    plight(name + "_Sala_Luz_Abajur", "POINT", 35, "#ffc98a", (lx, yb - .45, 1.5), col, P, shadow_soft_size=.1)
    plight(name + "_Sala_Luz_Teto", "POINT", 25 if tv else 70, "#ffd2a0", (cx, Y0 + 1.8, 2.5), col, P, shadow_soft_size=.25)
    bcyl(name + "_Sala_Vaso", .16, .12, .35, (cx - rw / 2 + .45, yb - .45, .28), M["barro"], col, P, seg=16)
    shrub(name + "_Sala_Planta", (cx - rw / 2 + .45, yb - .45, .75), .32, col, P, squash=1.2)
    if tv:
        bbox(name + "_Sala_TV", .05, 1.3, .75, (cx - rw / 2 + .07, Y0 + 1.9, 1.3), M["preto"], col, P)
        bbox(name + "_Sala_TV_Tela", .01, 1.24, .69, (cx - rw / 2 + .1, Y0 + 1.9, 1.3), M["tv"], col, P)
        plight(name + "_Sala_Luz_TV", "AREA", 40, "#7a9fff", (cx - rw / 2 + .2, Y0 + 1.9, 1.3), col, P, rot=(0, PI / 2, 0), size=1.1)
    cort = mat(name + "_Cortina", "#ece5d6", .9)
    for xa, xb in ((x0 - .1, x0 + w * .22), (x1 - w * .22, x1 + .1)):
        vs, fs = [], []; nx = 24
        for i in range(nx + 1):
            x = xa + (xb - xa) * i / nx; yy = Y0 + .25 + .045 * math.sin(i * PI / 2)
            vs += [(x, yy, .15), (x, yy, 2.7)]
        for i in range(nx):
            fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
        pydata(name + "_Sala_Cortina", vs, fs, Vector((0, 0, 0)), cort, col, P, smooth=True)
    janela(name + "_Janela_Sala", P, col, x0, x1, 1.45, 1.6, Y0, M["vidro"])

def casa_vizinha(name, loc, rz, w, d, st):
    col = C_VIZ
    P = empty(name, loc, rz, col)
    hw = w / 2; setback = 5.0
    g0, g1 = -hw + 1.0, -hw + 4.4          # portao da garagem
    p0, p1 = hw - 2.5, hw - 1.3            # portao social
    door_x = (p0 + p1) / 2
    fach = st["fach"]
    # muro, pilares, portoes
    for i, (a, b) in enumerate(((-hw, g0), (g1, p0), (p1, hw))):
        muro_trecho("%s_Muro_%d" % (name, i + 1), P, col, a, b, st["muro_alto"], fach)
    for x in (g0, g1, p0, p1):
        bbox(name + "_Pilar", .35, .35, 2.5, (x, 0, 1.25), fach, col, P)
        bbox(name + "_Pilar_Chapim", .41, .41, .05, (x, 0, 2.52), MR["pedra_clara"], col, P)
    if st["portao"] == "madeira":
        rip = bbox(name + "_Portao_Garagem_Ripa", g1 - g0 - .36, .05, .09, ((g0 + g1) / 2, 0, .2), M["freijo"], col, P)
        array(rip, "Ripas", (0, 0, .12), 17)
    else:
        bbox(name + "_Portao_Garagem", g1 - g0 - .36, .05, 2.2, ((g0 + g1) / 2, 0, 1.15), MR["portao"], col, P)
        ln = bbox(name + "_Portao_Friso", g1 - g0 - .36, .055, .012, ((g0 + g1) / 2, 0, .3), M["preto"], col, P)
        array(ln, "Frisos", (0, 0, .2), 10)
    bbox(name + "_Portao_Social", p1 - p0 - .36, .05, 2.1, (door_x, 0, 1.1), MR["portao"], col, P)
    text(name + "_Numero", st["numero"], .15, Vector((p1, -.185, 1.75)), (PI / 2, 0, 0), MR["numero"], col, P)
    bbox(name + "_Interfone", .1, .03, .16, (p0, -.19, 1.4), MR["caixilho"], col, P, bevel=.005)
    bbox(name + "_Caixa_Correio", .3, .1, .22, (p1, -.21, 1.15), MR["portao"], col, P, bevel=.01)
    bbox(name + "_Arandela", .12, .07, .18, (g1, -.2, 2.1), MR["arandela"], col, P)
    plight(name + "_Luz_Arandela", "POINT", 25, "#ffc98a", (g1, -.4, 2.1), col, P, shadow_soft_size=.05)
    if st["muro_alto"]:
        bbox(name + "_Placa_Cerca", .3, .01, .16, ((g1 + p0) / 2, -.11, 1.7), MR["amarelo"], col, P)
        text(name + "_Placa_Cerca_Txt", "CERCA\nELÉTRICA", .045, Vector(((g1 + p0) / 2, -.117, 1.72)), (PI / 2, 0, 0), MR["placa_preta"], col, P)
    # jardim frontal, piso e caminho
    bbox(name + "_Piso_Garagem", g1 - g0, setback, .03, ((g0 + g1) / 2, setback / 2, .0), MR["intertravado"], col, P)
    for k in range(6):
        bbox(name + "_Pisante", .7, .4, .03, (door_x, .6 + k * .75, .0), MR["pedra_clara"], col, P)
    lawn(name + "_Grama", -hw + .2, hw - .2, .2, setback - .1, -.095, C_VEG, P,
         holes=((g0 - .1, g1 + .1, -1, setback + 1), (door_x - .45, door_x + .45, -1, setback + 1)), cell=.5, dens=240)
    if not st["muro_alto"]:
        hedge(name + "_Cerca_Viva", p0 - g1 - .6, .5, .9, ((g1 + p0) / 2, .55, .45), C_VEG, P)
    for k in range(4):
        x = rnd.uniform(g1 + .6, p0 - .6)
        shrub(name + "_Arbusto", (x, setback - .55, .25), .35 + rnd.random() * .2, C_VEG, P)
    palm_b(name + "_Palmeira", ((g1 + p0) / 2 + rnd.uniform(-1, 1), 2.0, 0), 5 + rnd.random() * 2, C_VEG, P)
    for k in range(3):
        bcyl(name + "_Balizador", .04, .04, .4, (door_x + .6, 1.0 + k * 1.3, .2), MR["caixilho"], col, P, seg=10)
        bcyl(name + "_Balizador_Luz", .042, .042, .04, (door_x + .6, 1.0 + k * 1.3, .42), MR["arandela"], col, P, seg=10)
    # terreo
    hx0, hx1 = -hw + 1.0, hw - 1.0; W = hx1 - hx0; Y0 = setback
    terreo = bbox(name + "_Terreo", W, d, 3.0, (0, Y0 + d / 2, 1.5), fach, col, P)
    bbox(name + "_Rodape", W + .02, .03, .35, (0, Y0 - .015, .175), MR["pedra_escura"], col, P)
    bbox(name + "_Laje_Terreo", W + .1, d + .1, .14, (0, Y0 + d / 2, 3.07), M["concreto"], col, P)
    gw = g1 - g0 - .4
    bbox(name + "_Garagem_Porta", gw, .05, 2.4, ((g0 + g1) / 2, Y0 - .025, 1.2), MR["portao"] if st["portao"] != "madeira" else M["freijo"], col, P)
    ln = bbox(name + "_Garagem_Seccao", gw, .055, .012, ((g0 + g1) / 2, Y0 - .03, .4), M["preto"], col, P)
    array(ln, "Seccoes", (0, 0, .5), 4)
    bbox(name + "_Garagem_Moldura", gw + .3, .12, .2, ((g0 + g1) / 2, Y0 - .06, 2.5), M["concreto"], col, P)
    bbox(name + "_Porta_Pivotante", 1.25, .06, 2.7, (door_x, Y0 - .03, 1.35), M["freijo"], col, P)
    bcyl(name + "_Puxador", .015, .015, 1.3, (door_x + .45, Y0 - .1, 1.25), MR["caixilho"], col, P, seg=10)
    bbox(name + "_Marquise", 2.6, 1.5, .12, (door_x, Y0 - .75, 2.95), M["concreto"], col, P)
    bcyl(name + "_Spot_Marquise", .05, .05, .01, (door_x, Y0 - .75, 2.885), MR["arandela"], col, P, seg=16)
    plight(name + "_Luz_Marquise", "SPOT", 70, "#ffcf99", (door_x, Y0 - .75, 2.87), col, P,
           spot_size=math.radians(80), spot_blend=.6, shadow_soft_size=.03)
    if st["pedra"]:
        bbox(name + "_Painel_Filete", 1.7, .04, 3.0, (door_x - 1.55, Y0 - .02, 1.5), MR["filete"], col, P)
    wx0 = g1 + .4; wx1 = door_x - (2.5 if st["pedra"] else .9)
    if wx1 - wx0 > 1.0:
        if st["luz_sala"] is MR["janela_apagada"]:
            janela(name + "_Janela_Sala", P, col, wx0, wx1, 1.45, 1.6, Y0, st["luz_sala"])
        else:
            sala_interior(name, P, col, wx0, wx1, Y0, terreo, st["luz_sala"] is MR["janela_tv"])
    bbox(name + "_Ar_Condicionado", .3, .8, .55, (hx1 + .15, Y0 + 2.2, 2.2), MR["branco_ac"], col, P, bevel=.02)
    bcyl(name + "_Ar_Ventilador", .2, .2, .02, (hx1 + .31, Y0 + 2.2, 2.2), MR["caixilho"], col, P, rot=(0, PI / 2, 0), seg=24)
    # pavimento superior em balanco
    uw = W * .8; ux = W * .08; ud = d * .75; Y1 = Y0 - 1.2
    ux0, ux1 = ux - uw / 2, ux + uw / 2
    bbox(name + "_Superior", uw, ud, 2.9, (ux, Y1 + ud / 2, 4.55), st["fach2"], col, P)
    bbox(name + "_Laje_Superior", uw + .12, ud + .12, .22, (ux, Y1 + ud / 2, 3.1), M["concreto"], col, P)
    plight(name + "_Luz_Balanco", "SPOT", 40, "#ffcf99", ((g0 + g1) / 2, Y0 - .6, 2.95), col, P,
           spot_size=math.radians(90), spot_blend=.7)
    rw = uw * .4
    bbox(name + "_Ripado_Fundo", rw, .02, 2.8, (ux0 + rw / 2, Y1 - .01, 4.55), M["preto"], col, P)
    rp = bbox(name + "_Ripado", .045, .05, 2.8, (ux0 + .05, Y1 - .045, 4.55), M["freijo"], col, P)
    array(rp, "Ripas", (.09, 0, 0), int((rw - .05) / .09))
    bx0, bx1 = ux0 + rw + .25, ux1 - .3
    janela(name + "_Janela_Suite", P, col, bx0, bx1, 4.45, 2.0, Y1, st["luz_suite"])
    bbox(name + "_Sacada_Piso", bx1 - bx0 + .2, 1.0, .12, ((bx0 + bx1) / 2, Y1 - .5, 3.2), M["concreto"], col, P)
    bbox(name + "_Sacada_Vidro", bx1 - bx0 + .2, .015, 1.05, ((bx0 + bx1) / 2, Y1 - 1.0, 3.78), MR["vidro_guarda"], col, P)
    bcyl(name + "_Sacada_Corrimao", .02, .02, bx1 - bx0 + .2, ((bx0 + bx1) / 2, Y1 - 1.0, 4.32), MR["caixilho"], col, P, rot=(0, PI / 2, 0), seg=10)
    # cobertura: platibanda, caixa d'agua, aquecimento solar
    for (sx, sy, cx, cy) in ((uw, .15, ux, Y1), (uw, .15, ux, Y1 + ud), (.15, ud, ux0, Y1 + ud / 2), (.15, ud, ux1, Y1 + ud / 2)):
        bbox(name + "_Platibanda", sx, sy, .7, (cx, cy, 6.35), st["fach2"], col, P)
    bbox(name + "_Rufo", uw + .1, .2, .04, (ux, Y1, 6.72), MR["caixilho"], col, P)
    bcyl(name + "_Caixa_dAgua", .6, .55, .8, (ux1 - 1.1, Y1 + ud * .6, 6.4), MR["caixa_dagua"], col, P, seg=32)
    bcyl(name + "_Caixa_dAgua_Tampa", .61, .18, .2, (ux1 - 1.1, Y1 + ud * .6, 6.9), MR["caixa_dagua"], col, P, seg=32)
    if st["solar"]:
        for k in range(2):
            bbox(name + "_Coletor_Solar", 1.0, 2.0, .06, (ux0 + 1.2 + k * 1.15, Y1 + ud * .45, 6.55), MR["solar"], col, P, rot=(-.45, 0, 0))
    if st.get("carro"):
        carro(name + "_Carro", ((g0 + g1) / 2, 2.6, 0), -PI / 2, st["carro"], parent=P, placa=st.get("placa", "LTR5C18"))
    return P

VIZ = [
    ("Vizinho_A", (-17, -27.35, 0), PI, 14, 11, dict(fach=MR["fach_cinza"], fach2=MR["fach_branca"], muro_alto=True, portao="madeira",
        pedra=True, solar=True, numero="152", luz_sala=MR["janela_quente"], luz_suite=MR["janela_apagada"], carro="#23262b", placa="LRB7D40")),
    ("Vizinho_B", (0, -27.35, 0), PI, 15, 12, dict(fach=MR["fach_terra"], fach2=MR["fach_areia"], muro_alto=False, portao="metal",
        pedra=False, solar=False, numero="150", luz_sala=MR["janela_tv"], luz_suite=MR["janela_quente"], carro=None)),
    ("Vizinho_C", (17, -27.35, 0), PI, 14, 11, dict(fach=MR["fach_branca"], fach2=MR["fach_cinza"], muro_alto=True, portao="metal",
        pedra=True, solar=True, numero="148", luz_sala=MR["janela_apagada"], luz_suite=MR["janela_fria"], carro="#c9ccd1", placa="RIO3F12")),
    ("Vizinho_Esq", (-26, -13.5, 0), 0, 17, 12, dict(fach=MR["fach_areia"], fach2=MR["fach_branca"], muro_alto=True, portao="madeira",
        pedra=True, solar=False, numero="145", luz_sala=MR["janela_quente"], luz_suite=MR["janela_quente"], carro="#5c6b78", placa="KZD1A77")),
    ("Vizinho_Dir", (26, -13.5, 0), 0, 17, 12, dict(fach=MR["fach_branca"], fach2=MR["fach_terra"], muro_alto=False, portao="madeira",
        pedra=False, solar=True, numero="149", luz_sala=MR["janela_apagada"], luz_suite=MR["janela_tv"], carro=None)),
]
for nm, loc, rz, w, d, st in VIZ:
    casa_vizinha(nm, loc, rz, w, d, st)

# ------------------------------------------------------------------ postes de concreto e fiacao aerea
C_FIO = collection("07d_Postes_Fiacao")
MR["poste_conc"] = mat("Concreto_Poste", "#aaa69d", .9)
MR["isolador"] = mat("Isolador_Porcelana", "#7a3f22", .25)
MR["fio"] = mat("Fio_Aluminio", "#9a9ea3", .4, .8)
MR["cabo"] = mat("Cabo_Telecom", "#0e0e0e", .6)
MR["trafo"] = mat("Transformador", "#7e8488", .5, .4)

def curva(name, pts, r, material, col):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = 2
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, pt in enumerate(pts):
        sp.points[i].co = (pt[0], pt[1], pt[2], 1)
    cu.materials.append(material)
    ob = bpy.data.objects.new(name, cu); col.objects.link(ob)
    return ob

def catenaria(a, b, sag, n=18):
    return [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t - sag * 4 * t * (1 - t))
            for t in (i / n for i in range(n + 1))]

def poste_concreto(name, x, y, trafo=False):
    bm = _bm(); bmesh.ops.create_cube(bm, size=1, calc_uvs=True)
    bmesh.ops.scale(bm, vec=(.26, .17, 10.5), verts=bm.verts)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.x *= .55; v.co.y *= .6
    finish(name + "_Coluna", bm, Vector((x, y, 5.25)), MR["poste_conc"], C_FIO)
    bbox(name + "_Cruzeta", .1, 2.0, .1, (x, y, 10.05), MR["poste_conc"], C_FIO)
    mt = []
    for dy in (-.85, 0, .85):
        bcyl(name + "_Isolador", .035, .05, .14, (x, y + dy, 10.17), MR["isolador"], C_FIO, seg=10)
        mt.append((x, y + dy, 10.22))
    bbox(name + "_Caixa_Telecom", .18, .32, .5, (x, y + .2, 6.6), MR["cabo"], C_FIO)
    bbox(name + "_Suporte_Cabos", .06, .5, .06, (x, y, 7.2), MR["portao"], C_FIO)
    if trafo:
        bcyl(name + "_Transformador", .33, .33, .95, (x, y - .45, 8.7), MR["trafo"], C_FIO, seg=24)
        bcyl(name + "_Transformador_Tampa", .35, .3, .08, (x, y - .45, 9.2), MR["trafo"], C_FIO, seg=24)
        for k in range(3):
            bcyl(name + "_Bucha", .03, .04, .18, (x - .12 + k * .12, y - .45, 9.33), MR["isolador"], C_FIO, seg=8)
    return mt, (x, y, 7.2)

PX = (-35, -21, -7, 7, 21, 35); PY = -24.95
postes = [poste_concreto("Poste_Concreto_%d" % (i + 1), x, PY, trafo=(x == -7)) for i, x in enumerate(PX)]
for i in range(len(postes) - 1):
    (mt_a, tel_a), (mt_b, tel_b) = postes[i], postes[i + 1]
    for k in range(3):
        curva("Fio_Media_Tensao", catenaria(mt_a[k], mt_b[k], .32), .006, MR["fio"], C_FIO)
    for k, (dz, sag, r) in enumerate(((0, .55, .012), (-.12, .7, .009), (-.22, .85, .007))):
        a = (tel_a[0], tel_a[1] + .1 * k, tel_a[2] + dz); b = (tel_b[0], tel_b[1] + .1 * k, tel_b[2] + dz)
        curva("Cabo_Telecom", catenaria(a, b, sag), r, MR["cabo"], C_FIO)
for cx, px in ((-17, -21), (0, -7), (17, 21)):     # ramais descendo ate as casas do outro lado
    tel = (px, PY, 7.1)
    curva("Ramal_Casa", catenaria(tel, (cx + 1.2, -31.1, 5.8), .9), .006, MR["cabo"], C_FIO)
    curva("Ramal_Energia", catenaria((px, PY + .85, 10.2), (cx + 1.6, -31.1, 6.2), 1.2), .005, MR["fio"], C_FIO)
# fios cruzando a rua ate o lado da nossa casa
curva("Travessia_Energia", catenaria((7, PY + .85, 10.2), (9.5, -16.4, 10.2), 1.4), .005, MR["fio"], C_FIO)
curva("Travessia_Telecom", catenaria((7, PY, 7.1), (9.5, -16.4, 7.1), 1.0), .007, MR["cabo"], C_FIO)
poste_concreto("Poste_Concreto_Casa", 9.5, -16.4)

# neblina leve: deixa os fachos de luz visiveis (desligue a colecao para render mais rapido)
neb = bbox("Neblina_Volume", 90, 60, 14, (0, -12, 7), None, C_NEB)
mn, nt_, b_ = new_mat("Neblina")
out = nt_.nodes.get("Material Output"); nt_.nodes.remove(b_)
vol = nt_.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Density"].default_value = .0025; vol.inputs["Anisotropy"].default_value = .45
nt_.links.new(vol.outputs[0], out.inputs["Volume"])
neb.data.materials.append(mn); neb.display_type = "BOUNDS"

scene.frame_start, scene.frame_end = 1, 240
scene.frame_set(11)   # quadro com vermelho e azul acesos juntos


def camera(name, pos, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    ob = bpy.data.objects.new(name, cd); C_LUZ.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    return ob

camera("Camera_Entrada", V(0, 1.6, 6.4), V(0, 1.3, 0), 18)
cam_int = camera("Camera_Interior", V(3.2, 1.6, 3.5), V(-3.2, .7, -.2), 18)
camera("Camera_Rua", Vector((-12.0, -22.3, 1.65)), Vector((4.0, -13.0, 1.8)), 20)
camera("Camera_Viatura", Vector((-2.2, -21.6, 1.05)), Vector((2.6, -18.0, .8)), 32)
camera("Camera_Vizinhos", Vector((4.0, -15.0, 1.65)), Vector((-2.0, -33.0, 3.0)), 18)
scene.camera = bpy.data.objects["Camera_Rua"]

world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (*lin(hx("#1b2640")), 1)
    bg.inputs["Strength"].default_value = .25

scene.unit_settings.system = "METRIC"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.engine = "CYCLES"
scene.cycles.samples = 256
scene.cycles.use_denoising = True
for attr, val in (("view_transform", "AgX"), ("look", "AgX - Medium High Contrast")):
    try:
        setattr(scene.view_settings, attr, val)
    except Exception:
        pass
scene.view_settings.exposure = .6

# esconde os cortadores no viewport (continuam funcionando)
for ob in C_CUT.objects:
    ob.hide_render = True
C_CUT.hide_render = True
lc = bpy.context.view_layer.layer_collection.children.get("99_Cortadores")
if lc:
    lc.hide_viewport = True

print("Casa em Silencio: %d objetos criados" % len(bpy.data.objects))
