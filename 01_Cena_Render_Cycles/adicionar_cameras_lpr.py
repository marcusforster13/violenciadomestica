"""
A Casa em Silencio - cameras de leitura de placas (LPR, estilo "Flock", sem marca) nos postes de LED.

Cada camera: abracadeira no poste, braco, caixa com quinas arredondadas, aba de sol, lente,
anel de LEDs infravermelhos e painel solar inclinado num mastro curto.
Mira na faixa de transito do lado do poste (le a placa dianteira de quem vem).

Pode rodar de novo: apaga as CamLPR_* existentes e recria.
Uso:  blender -b casa_em_silencio.blend --python adicionar_cameras_lpr.py
"""
import bpy, bmesh, math, re
from mathutils import Vector, Matrix

PI = math.pi
# Paineis solares se viram para o sol: no hemisferio sul, para o NORTE (~25 graus de inclinacao).
# A cena nao tem norte definido; aqui o norte = -Y (direcao da rua vista da casa). Todos ficam iguais.
NORTE_Y = -1
COL = bpy.data.collections.get("07_Rua_Condominio") or bpy.context.scene.collection

def mat(nome, cor, rough=.5, metal=0., emit=None, emit_str=0.):
    m = bpy.data.materials.get(nome)
    if m:
        return m
    m = bpy.data.materials.new(nome)
    b = m.node_tree.nodes.get("Principled BSDF")
    c = tuple(int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    c = tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)
    b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        e = tuple(int(emit[i:i + 2], 16) / 255 for i in (1, 3, 5))
        b.inputs["Emission Color"].default_value = (*e, 1); b.inputs["Emission Strength"].default_value = emit_str
    m.diffuse_color = (*c, 1)
    return m

M_CAIXA = mat("LPR_Caixa_Grafite", "#2b2d30", .45)
M_LENTE = mat("LPR_Lente_Vidro", "#050608", .03)
M_IR = mat("LPR_LED_Infravermelho", "#1a0606", .2, emit="#ff2a1a", emit_str=.12)
M_IR.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = .12   # se ja existia
M_SOLAR = mat("LPR_Painel_Solar", "#121a2e", .08, .2)
M_ALU = mat("LPR_Aluminio", "#a9adb2", .3, 1.)
M_FERRAGEM = mat("LPR_Ferragem", "#3b3d40", .5, .7)

def caixa(nome, sx, sy, sz, loc, material, pai, rot=(0, 0, 0), chanfro=0.0, seg=3):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(material)
    ob = bpy.data.objects.new(nome, me); COL.objects.link(ob)
    ob.parent = pai; ob.location = loc; ob.rotation_euler = rot
    if chanfro:
        bv = ob.modifiers.new("MM_Bevel", "BEVEL"); bv.width = chanfro; bv.segments = seg; bv.limit_method = "ANGLE"
    return ob

def cilindro(nome, r, prof, loc, material, pai, rot=(0, 0, 0), seg=24, tampa=True, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=tampa, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=prof)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(material)
    ob = bpy.data.objects.new(nome, me); COL.objects.link(ob)
    ob.parent = pai; ob.location = loc; ob.rotation_euler = rot
    return ob

# limpa versoes anteriores
for o in [o for o in bpy.data.objects if o.name.startswith("CamLPR_")]:
    bpy.data.objects.remove(o, do_unlink=True)

postes = sorted((o for o in bpy.data.objects if re.match(r"Poste(_Oposto)?_\d+_Coluna$", o.name)), key=lambda o: o.name)
n = 0
for col in postes:
    pref = col.name[:-len("_Coluna")]
    lum = bpy.data.objects.get(pref + "_Luminaria")
    lado = 1 if (lum and lum.location.y > col.location.y) else -1     # lado da rua em Y
    # faixa do lado do poste: na faixa da casa (Y maior) os carros vao para -X -> camera olha para +X
    mira = 1 if col.location.y > -20.5 else -1
    n += 1
    raiz = bpy.data.objects.new("CamLPR_%02d" % n, None); COL.objects.link(raiz)
    raiz.empty_display_size = .3
    raiz.location = (col.location.x, col.location.y, 3.5)
    # abracadeira + braco ate o lado da rua
    cilindro("CamLPR_%02d_Abracadeira" % n, .088, .09, (0, 0, 0), M_FERRAGEM, raiz, seg=20)
    cilindro("CamLPR_%02d_Abracadeira2" % n, .088, .06, (0, 0, -.22), M_FERRAGEM, raiz, seg=20)
    caixa("CamLPR_%02d_Braco" % n, .05, .26, .05, (0, lado * .2, 0), M_FERRAGEM, raiz, chanfro=.006)
    caixa("CamLPR_%02d_Mao_Francesa" % n, .03, .03, .26, (0, lado * .12, -.12), M_FERRAGEM, raiz, rot=(lado * .85, 0, 0), chanfro=.004)
    # cabeca da camera: gira para a mira e inclina ~14 graus para baixo
    cab = bpy.data.objects.new("CamLPR_%02d_Cabeca" % n, None); COL.objects.link(cab)
    cab.parent = raiz; cab.location = (0, lado * .33, -.04)
    cab.rotation_euler = (0, math.radians(14), 0 if mira > 0 else PI)   # inclina antes de girar (Euler XYZ)
    caixa("CamLPR_%02d_Corpo" % n, .34, .15, .15, (0, 0, 0), M_CAIXA, cab, chanfro=.03, seg=4)
    caixa("CamLPR_%02d_Aba_Sol" % n, .22, .17, .012, (.12, 0, .085), M_CAIXA, cab, rot=(0, math.radians(-6), 0), chanfro=.004)
    cilindro("CamLPR_%02d_Moldura_Lente" % n, .052, .03, (.18, 0, 0), M_CAIXA, cab, rot=(0, PI / 2, 0), seg=28)
    cilindro("CamLPR_%02d_Lente" % n, .036, .012, (.196, 0, 0), M_LENTE, cab, rot=(0, PI / 2, 0), seg=28)
    for k in range(8):
        a = 2 * PI * k / 8
        cilindro("CamLPR_%02d_IR_%d" % (n, k), .0055, .006, (.197, math.cos(a) * .044, math.sin(a) * .044),
                 M_IR, cab, rot=(0, PI / 2, 0), seg=8)
    cilindro("CamLPR_%02d_Junta" % n, .03, .05, (-.03, 0, .1), M_FERRAGEM, cab, seg=12)
    # painel solar num mastro curto acima da abracadeira, inclinado ~25 graus
    cilindro("CamLPR_%02d_Mastro" % n, .018, .5, (0, lado * .3, .25), M_FERRAGEM, raiz, seg=10)
    pnl = bpy.data.objects.new("CamLPR_%02d_Painel" % n, None); COL.objects.link(pnl)
    pnl.parent = raiz; pnl.location = (0, lado * .3, .52); pnl.rotation_euler = (math.radians(25) * -NORTE_Y, 0, 0)
    caixa("CamLPR_%02d_Solar" % n, .52, .36, .02, (0, 0, 0), M_SOLAR, pnl, chanfro=.003)
    for sy in (-1, 1):
        caixa("CamLPR_%02d_Moldura_Solar" % n, .54, .015, .03, (0, sy * .18, 0), M_ALU, pnl)
    for sx in (-1, 1):
        caixa("CamLPR_%02d_Moldura_Solar" % n, .015, .36, .03, (sx * .27, 0, 0), M_ALU, pnl)
    # cabo da camera ate o poste
    cu = bpy.data.curves.new("CamLPR_%02d_Cabo" % n, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = .005
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(1)
    p0, p1 = sp.bezier_points
    p0.co = (-.1 * mira, lado * .33, -.08); p1.co = (0, lado * .09, -.3)
    for p in (p0, p1):
        p.handle_left_type = p.handle_right_type = "AUTO"
    cu.materials.append(M_CAIXA)
    cabo = bpy.data.objects.new("CamLPR_%02d_Cabo" % n, cu); COL.objects.link(cabo); cabo.parent = raiz

print("[LPR] %d cameras de leitura de placas instaladas nos postes" % n)
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[LPR] cena principal salva")
