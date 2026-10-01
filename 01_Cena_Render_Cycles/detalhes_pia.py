"""
A Casa em Silencio - pia da cozinha de verdade.

- Furo no tampo de granito e no gabinete (Boolean, nao destrutivo)
- Cuba de inox de embutir: aba sobre o granito, paredes com cantos arredondados, fundo inclinado
  para o ralo, ralo cromado
- Torneira gourmet de bica alta curvada, com alavanca
- Esponja (amarela/verde) e frasco de detergente (sem marca)
Remove as pecas antigas (Cuba_Inox, Torneira, Torneira_Bica). Pode rodar de novo.
Uso:  blender -b casa_em_silencio.blend --python detalhes_pia.py
"""
import bpy, bmesh, math
from mathutils import Vector

PI = math.pi
COL = bpy.data.collections.get("04_Cozinha") or bpy.context.scene.collection

def lin(h):
    c = tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def mat(nome, cor, rough=.5, metal=0., transm=0.):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*lin(cor), 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Transmission Weight" in b.inputs: b.inputs["Transmission Weight"].default_value = transm
    m.diffuse_color = (*lin(cor), 1)
    return m

INOX = mat("Inox_Escovado", "#b8bcc0", .28, 1.)
CROMO = bpy.data.materials.get("Cromado") or mat("Cromado", "#d0d2d4", .08, 1.)
ESC = mat("Ralo_Escuro", "#151515", .6)
ESP_A = mat("Esponja_Amarela", "#e8c23a", .9)
ESP_V = mat("Esponja_Verde", "#2e7d3a", .95)
DET = mat("Detergente_Frasco", "#f2c200", .25, transm=.35)
DET_T = mat("Detergente_Tampa", "#c0392b", .4)
CORT = bpy.data.materials.get("Cortador") or mat("Cortador", "#ff00ff", 1)

def apagar(nome):
    o = bpy.data.objects.get(nome)
    if o:
        for c in list(o.children):
            bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.objects.remove(o, do_unlink=True)

for o in [o for o in bpy.data.objects if o.name.startswith("Pia_")]:
    bpy.data.objects.remove(o, do_unlink=True)
for n in ("Cuba_Inox", "Torneira", "Torneira_Bica"):
    apagar(n)

def novo(nome, me, material=None, smooth=True):
    if material:
        me.materials.append(material)
    if smooth:
        for p in me.polygons: p.use_smooth = True
        try: me.set_sharp_from_angle(angle=math.radians(40))
        except Exception: pass
    o = bpy.data.objects.new(nome, me); COL.objects.link(o); o["detalhado"] = True
    return o

def ret_arred(cx, cy, w, l, r, n=6):
    """Retangulo de cantos arredondados (lista de (x, y)), mesmo numero de pontos para qualquer tamanho."""
    pts = []
    for k, (sx, sy, a0) in enumerate(((1, 1, 0), (-1, 1, PI / 2), (-1, -1, PI), (1, -1, 3 * PI / 2))):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (l / 2 - r)
        for i in range(n + 1):
            a = a0 + PI / 2 * i / n
            pts.append((ccx + math.cos(a) * r, ccy + math.sin(a) * r))
    return pts

CX, CY = 5.69, 1.40      # centro da cuba (tampo lateral: x 5,39-6,01 / topo z 0,92)

# ---------------- cuba (aneis de cima para baixo)
aneis = [(.9225, .46, .61, .05), (.9235, .40, .55, .04), (.915, .40, .55, .04), (.765, .375, .525, .035),
         (.752, .33, .48, .03), (.747, .09, .09, .045), (.733, .07, .07, .035)]
bm = bmesh.new(); rings = []
for z, w, l, r in aneis:
    rings.append([bm.verts.new((x, y, z)) for x, y in ret_arred(CX, CY, w, l, r)])
N = len(rings[0])
for a, b in zip(rings, rings[1:]):
    for i in range(N):
        bm.faces.new((a[i], a[(i + 1) % N], b[(i + 1) % N], b[i]))
c = bm.verts.new((CX, CY, .733))
for i in range(N):
    bm.faces.new((rings[-1][i], rings[-1][(i + 1) % N], c))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("Pia_Cuba"); bm.to_mesh(me); bm.free()
cuba = novo("Pia_Cuba", me, INOX)
so = cuba.modifiers.new("Espessura", "SOLIDIFY"); so.thickness = .0012; so.offset = 1

# ---------------- ralo cromado
def cil(nome, r, h, loc, material, seg=32, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    o = novo(nome, me, material); o.location = loc; o.rotation_euler = rot
    return o
cil("Pia_Ralo", .043, .004, (CX, CY, .749), CROMO)
cil("Pia_Ralo_Centro", .014, .005, (CX, CY, .7495), ESC, seg=20)
for k in range(10):
    a = 2 * PI * k / 10
    cil("Pia_Ralo_Furo", .0035, .005, (CX + math.cos(a) * .03, CY + math.sin(a) * .03, .7495), ESC, seg=10)

# ---------------- furos no tampo (cantos arredondados) e no gabinete
def prisma(nome, pts, z0, z1):
    bm = bmesh.new()
    b0 = [bm.verts.new((x, y, z0)) for x, y in pts]; b1 = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    for i in range(n):
        bm.faces.new((b0[i], b0[(i + 1) % n], b1[(i + 1) % n], b1[i]))
    bm.faces.new(b0[::-1]); bm.faces.new(b1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    o = novo(nome, me, CORT, smooth=False); o.display_type = "WIRE"; o.hide_render = True
    cut = bpy.data.collections.get("99_Cortadores")
    if cut:
        for c in list(o.users_collection): c.objects.unlink(o)
        cut.objects.link(o)
    return o

furo_tampo = prisma("Pia_Cortador_Tampo", ret_arred(CX, CY, .405, .555, .04), .85, .96)
furo_gab = prisma("Pia_Cortador_Gabinete", ret_arred(CX, CY, .43, .58, .03), .70, .93)
for nome_alvo, cortador in (("Tampo_Lateral_Granito", furo_tampo), ("Bancada_Lateral", furo_gab)):
    alvo = bpy.data.objects.get(nome_alvo)
    if alvo:
        md = alvo.modifiers.get("Furo_Pia") or alvo.modifiers.new("Furo_Pia", "BOOLEAN")
        md.operation = "DIFFERENCE"; md.object = cortador; md.solver = "EXACT"

# ---------------- torneira gourmet (bica alta curvada) no fundo da bancada
cil("Pia_Torneira_Base", .026, .03, (5.935, CY, .935), CROMO)
cu = bpy.data.curves.new("Pia_Torneira_Bica", "CURVE"); cu.dimensions = "3D"
cu.bevel_depth = .0115; cu.bevel_resolution = 4; cu.resolution_u = 24; cu.use_fill_caps = True
sp = cu.splines.new("BEZIER"); sp.bezier_points.add(2)
p0, p1, p2 = sp.bezier_points
p0.co = (5.935, CY, .95); p0.handle_left = (5.935, CY, .9); p0.handle_right = (5.935, CY, 1.12)
p1.co = (5.88, CY, 1.27); p1.handle_left = (5.935, CY, 1.25); p1.handle_right = (5.81, CY, 1.29)
p2.co = (5.745, CY, 1.16); p2.handle_left = (5.745, CY, 1.24); p2.handle_right = (5.745, CY, 1.12)
cu.materials.append(CROMO)
bica = bpy.data.objects.new("Pia_Torneira_Bica", cu); COL.objects.link(bica); bica["detalhado"] = True
cil("Pia_Torneira_Arejador", .014, .02, (5.745, CY, 1.152), CROMO, seg=24)
cil("Pia_Torneira_Corpo_Alavanca", .016, .05, (5.935, CY + .035, .985), CROMO, rot=(PI / 2, 0, 0))
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); bmesh.ops.scale(bm, vec=(.012, .09, .01), verts=bm.verts)
me = bpy.data.meshes.new("Pia_Torneira_Alavanca"); bm.to_mesh(me); bm.free()
alav = novo("Pia_Torneira_Alavanca", me, CROMO); alav.location = (5.935, CY + .095, 1.0); alav.rotation_euler = (.35, 0, 0)
bv = alav.modifiers.new("MM_Bevel", "BEVEL"); bv.width = .004; bv.segments = 3

# ---------------- esponja e detergente ao lado da cuba
def caixa(nome, sx, sy, sz, loc, material, chanfro=.006, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    o = novo(nome, me, material); o.location = loc; o.rotation_euler = rot
    b = o.modifiers.new("MM_Bevel", "BEVEL"); b.width = chanfro; b.segments = 3
    return o
caixa("Pia_Esponja", .1, .068, .024, (5.64, 1.80, .932), ESP_A, rot=(0, 0, .3))
caixa("Pia_Esponja_Fibra", .1, .068, .008, (5.64, 1.80, .948), ESP_V, chanfro=.003, rot=(0, 0, .3))
perfil = [(0, 0), (.028, 0), (.032, .006), (.033, .03), (.031, .12), (.026, .15), (.018, .165), (.012, .17), (.012, .185), (0, .185)]
seg = 32; vs, fs = [], []
for i in range(seg):
    a = 2 * PI * i / seg
    vs += [(r * math.cos(a) * 1.0, r * math.sin(a) * .62, h) for r, h in perfil]    # frasco achatado
for i in range(seg):
    i2 = (i + 1) % seg
    for j in range(len(perfil) - 1):
        n = len(perfil); fs.append((i * n + j, i2 * n + j, i2 * n + j + 1, i * n + j + 1))
me = bpy.data.meshes.new("Pia_Detergente"); me.from_pydata(vs, [], fs)
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
det = novo("Pia_Detergente", me, DET); det.location = (5.86, 1.86, .92); det.rotation_euler = (0, 0, .4)
cil("Pia_Detergente_Tampa", .013, .022, (5.86, 1.86, 1.115), DET_T, seg=20)

print("[PIA] cuba de embutir, ralo, torneira gourmet, esponja e detergente prontos")
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[PIA] cena principal salva")
