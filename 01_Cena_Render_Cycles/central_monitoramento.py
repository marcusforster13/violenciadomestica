"""
A Casa em Silencio - guarita da portaria vira central de monitoramento (CFTV).

- A guarita deixa de ser um bloco macico com uma janela branca: paredes com vao, vidro de correr de verdade,
  piso, teto, luminaria e porta lateral.
- Dentro: parede de 6 monitores (2 x 3), mesa do operador com 2 monitores, teclado, joystick de PTZ, radio,
  telefone, cadeira, rack com o gravador (NVR) e LEDs, relogio, extintor e quadro de avisos.
- 6 cameras de CFTV (modelo fisico nos postes e na guarita) + um objeto CAMERA "CFTV_Cam_N" para cada uma,
  exportado no cena.json; no three.js (web/cftv.js) as telas CFTV_Tela_*_cN mostram ao vivo o que cada camera ve.

Colecoes: 07e_Guarita (estrutura e moveis, com lightmap proprio) e 12_CFTV (telas e cameras: sem lightmap,
nao sao unidas - o three.js troca o material das telas).
Idempotente: apaga o que criou antes (GuaritaC_*, CFTV_*) e recria.
Uso:  blender -b casa_em_silencio.blend --python central_monitoramento.py
"""
import bpy, bmesh, math
from mathutils import Vector

PI = math.pi

def say(m):
    print("[CFTV] " + m)

def colecao(nome):
    c = bpy.data.collections.get(nome)
    if not c:
        c = bpy.data.collections.new(nome); bpy.context.scene.collection.children.link(c)
    return c

C_GUA = colecao("07e_Guarita")
C_CFTV = colecao("12_CFTV")
C_RUA = bpy.data.collections.get("07_Rua_Condominio") or bpy.context.scene.collection

def lin(h):
    c = tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def mat(nome, cor, rough=.5, metal=0., emit=None, emit_str=0.):
    m = bpy.data.materials.get(nome)
    if m:
        return m
    m = bpy.data.materials.new(nome)
    b = m.node_tree.nodes.get("Principled BSDF")
    c = lin(cor)
    b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(emit), 1); b.inputs["Emission Strength"].default_value = emit_str
    m.diffuse_color = (*c, 1)
    return m

M = {
    "parede": bpy.data.materials.get("Fachada_Branca") or mat("Fachada_Branca", "#eeebe4", .9),
    "vidro": bpy.data.materials.get("Vidro") or mat("Vidro", "#a9c6d6", .05),
    "piso": mat("Piso_Guarita", "#8e8a83", .55),
    "teto": mat("Teto_Guarita", "#efefeb", .9),
    "aluminio": mat("Aluminio_Guarita", "#b8bcc0", .3, 1.),
    "mesa": mat("Laminado_Grafite", "#3b3c40", .45),
    "preto": mat("Plastico_Preto", "#131416", .35),
    "tela": mat("CFTV_Tela", "#000000", .2, emit="#5d7891", emit_str=2.0),
    "tecido": mat("Tecido_Cadeira", "#1c1d21", .95),
    "cromo": mat("Metal_Cromado", "#cfd1d4", .2, 1.),
    "led_verde": mat("LED_Verde", "#0a2a12", .3, emit="#22ff66", emit_str=4.),
    "led_azul": mat("LED_Azul", "#0a1430", .3, emit="#3a7bff", emit_str=4.),
    "led_verm": mat("LED_Vermelho_CFTV", "#300a0a", .3, emit="#ff2a20", emit_str=4.),
    "extintor": mat("Extintor_Vermelho", "#b3170f", .35),
    "porta": mat("Porta_Aco_Guarita", "#5c6166", .45, .4),
    "luminaria": mat("Luminaria_Guarita", "#f4f7ff", .4, emit="#eef3ff", emit_str=3.),
    "cortica": mat("Cortica_Avisos", "#a87c4f", .9),
    "papel": mat("Papel_Avisos", "#f2efe6", .9),
    "caneca": mat("Caneca_Azul", "#2d4f86", .4),
    "cam_caixa": mat("CFTV_Caixa_Branca", "#e6e6e2", .4),
    "cam_lente": bpy.data.materials.get("LPR_Lente_Vidro") or mat("LPR_Lente_Vidro", "#050608", .03),
    "cam_ir": bpy.data.materials.get("LPR_LED_Infravermelho") or mat("LPR_LED_Infravermelho", "#1a0606", .2, emit="#ff2a1a", emit_str=.12),
    "ferragem": bpy.data.materials.get("LPR_Ferragem") or mat("LPR_Ferragem", "#3b3d40", .5, .7),
}

# ------------------------------------------------------------------ limpeza (idempotente)
for o in [o for o in bpy.data.objects if o.name.startswith(("GuaritaC_", "CFTV_")) or o.name in ("Guarita_Corpo", "Guarita_Janela")]:
    bpy.data.objects.remove(o, do_unlink=True)

GU = bpy.data.objects.get("Guarita_Portaria")
ORIG = GU.matrix_world.translation.copy() if GU else Vector((40.5, -14.6, .15))

def caixa(nome, tam, loc, material, col=C_GUA, rot=(0, 0, 0), local=True):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=tam, verts=bm.verts)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    me.materials.append(material)
    ob = bpy.data.objects.new(nome, me); col.objects.link(ob)
    ob.location = (ORIG + Vector(loc)) if local else Vector(loc); ob.rotation_euler = rot
    return ob

def cilindro(nome, r, prof, loc, material, col=C_GUA, rot=(0, 0, 0), seg=16, r2=None, local=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=prof)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(material)
    ob = bpy.data.objects.new(nome, me); col.objects.link(ob)
    ob.location = (ORIG + Vector(loc)) if local else Vector(loc); ob.rotation_euler = rot
    return ob

def tela(nome, larg, alt, loc, rot_z=0.0):
    """Plano virado para -Y (UV 0..1: u para a direita de quem olha, v para cima)."""
    me = bpy.data.meshes.new(nome)
    w, h = larg / 2, alt / 2
    me.from_pydata([(-w, 0, -h), (w, 0, -h), (w, 0, h), (-w, 0, h)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for l, c in zip(me.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[l].uv = c
    me.materials.append(M["tela"])
    ob = bpy.data.objects.new(nome, me); C_CFTV.objects.link(ob)
    ob.location = ORIG + Vector(loc); ob.rotation_euler = (0, 0, rot_z)
    return ob

# ------------------------------------------------------------------ 1. guarita oca (3,2 x 2,6 x 2,7 m)
L, P, H, E = 3.2, 2.6, 2.7, .12          # largura (x), profundidade (y), altura, espessura das paredes
YF = -P / 2 + E / 2                      # parede da frente (rua, -Y)
JX, JZ0, JZ1 = 1.3, 1.05, 2.15           # vao da janela: x -1,3..1,3 / z 1,05..2,15
caixa("GuaritaC_Frente_Baixo", (L, E, JZ0), (0, YF, JZ0 / 2), M["parede"])
caixa("GuaritaC_Frente_Cima", (L, E, H - JZ1), (0, YF, (JZ1 + H) / 2), M["parede"])
# porta na parede leste: vao entre o balcao da janela (y < -0,76) e a mesa do operador (y > 0,42), livre dos dois lados
PY0, PY1, PZ = -.72, .18, 2.08          # vao da porta: y -0,72..0,18 / z 0..2,08
for s in (-1, 1):
    caixa("GuaritaC_Frente_Lado", (L / 2 - JX, E, JZ1 - JZ0), (s * (JX + L / 2) / 2, YF, (JZ0 + JZ1) / 2), M["parede"])
caixa("GuaritaC_Lateral", (E, P - 2 * E, H), (-(L / 2 - E / 2), 0, H / 2), M["parede"])
y0, y1 = -P / 2 + E, P / 2 - E
xl_ = L / 2 - E / 2
caixa("GuaritaC_Lateral_Porta_Sul", (E, PY0 - y0, H), (xl_, (y0 + PY0) / 2, H / 2), M["parede"])
caixa("GuaritaC_Lateral_Porta_Norte", (E, y1 - PY1, H), (xl_, (PY1 + y1) / 2, H / 2), M["parede"])
caixa("GuaritaC_Lateral_Porta_Verga", (E, PY1 - PY0, H - PZ), (xl_, (PY0 + PY1) / 2, (PZ + H) / 2), M["parede"])
caixa("GuaritaC_Fundo", (L, E, H), (0, P / 2 - E / 2, H / 2), M["parede"])
caixa("GuaritaC_Piso", (L - 2 * E, P - 2 * E, .03), (0, 0, .015), M["piso"])
caixa("GuaritaC_Teto", (L - 2 * E, P - 2 * E, .02), (0, 0, H - .01), M["teto"])
caixa("GuaritaC_Luminaria", (.62, .62, .03), (0, .15, H - .035), M["luminaria"])

# janela de correr: caixilho de aluminio + 2 folhas de vidro
yj = YF
for z in (JZ0 + .02, JZ1 - .02):
    caixa("GuaritaC_Caixilho_H", (2 * JX, .1, .04), (0, yj, z), M["aluminio"])
for x in (-JX + .02, JX - .02):
    caixa("GuaritaC_Caixilho_V", (.04, .1, JZ1 - JZ0), (x, yj, (JZ0 + JZ1) / 2), M["aluminio"])
for i, (x, dy) in enumerate(((-JX / 2 + .05, -.02), (JX / 2 - .05, .02))):
    caixa("GuaritaC_Vidro_%d" % (i + 1), (JX + .1, .008, JZ1 - JZ0 - .06), (x, yj + dy, (JZ0 + JZ1) / 2), M["vidro"])
    caixa("GuaritaC_Folha_Montante", (.035, .03, JZ1 - JZ0 - .06), (x + (JX / 2 + .03) * (1 if i == 0 else -1), yj + dy, (JZ0 + JZ1) / 2), M["aluminio"])
caixa("GuaritaC_Balcao_Interno", (2.8, .42, .04), (0, YF + E / 2 + .21, JZ0 - .02), M["mesa"])
caixa("GuaritaC_Livro_Ocorrencias", (.32, .24, .03), (-.7, YF + .3, JZ0 + .015), M["caneca"])
caixa("GuaritaC_Interfone", (.12, .08, .2), (.95, YF + .2, JZ0 + .1), M["preto"])

# porta lateral de aco (lado leste): folha de verdade no vao, macaneta dos dois lados, batentes por dentro e por fora.
# A folha fica presa na dobradica (GuaritaC_Porta_Dobradica, no canto sul do vao) e abre PARA FORA (giro -90 graus):
# o site (web/porta_guarita.js) abre e fecha com um clique / gatilho e libera a passagem quando aberta.
xf = L / 2 - E / 2                       # meio da parede
dob = bpy.data.objects.new("GuaritaC_Porta_Dobradica", None); C_GUA.objects.link(dob)
dob.location = ORIG + Vector((L / 2 - .005, PY0 + .01, 0))     # eixo na face de fora, junto ao batente sul
def peca_porta(nome, tam, loc_mundo_local, mat_, forma=caixa, **kw):
    o = forma(nome, tam, loc_mundo_local, mat_, **kw) if forma is caixa else forma(nome, *tam, loc_mundo_local, mat_, **kw)
    o.parent = dob; o.location = o.location - dob.location           # a dobradica nao tem giro: so desloca
    return o
LF = PY1 - PY0 - .02                     # largura da folha
peca_porta("GuaritaC_Porta_Folha", (.04, LF, PZ - .02), (xf, (PY0 + PY1) / 2, (PZ - .02) / 2 + .005), M["porta"])
for lado, dx in (("Ext", .07), ("Int", -.07)):           # macanetas perto da borda livre (lado norte)
    peca_porta("GuaritaC_Porta_Macaneta_" + lado, (.018, .14), (xf + dx, PY1 - .12, 1.02), M["cromo"], forma=cilindro, rot=(PI / 2, 0, 0), seg=10)
    peca_porta("GuaritaC_Porta_Espelho_" + lado, (.012, .05, .18), (xf + dx * .45, PY1 - .1, 1.02), M["cromo"])
for lado, xb in (("Ext", L / 2 + .015), ("Int", L / 2 - E - .015)):   # batentes (guarnicoes) em volta do vao
    caixa("GuaritaC_Porta_Batente_Topo_" + lado, (.03, PY1 - PY0 + .12, .06), (xb, (PY0 + PY1) / 2, PZ + .03), M["aluminio"])
    for yb in (PY0 - .03, PY1 + .03):
        caixa("GuaritaC_Porta_Batente_Lado_" + lado, (.03, .06, PZ), (xb, yb, PZ / 2), M["aluminio"])

# ------------------------------------------------------------------ 2. parede de monitores (2 x 3) e mesa do operador
YM = P / 2 - E - .05                     # face da parede do fundo, por dentro
caixa("GuaritaC_Painel_Monitores", (2.56, .05, 1.06), (0, YM + .02, 1.76), M["preto"])
CAMS_TELA = [1, 2, 3, 4, 5, 6]           # tela (linha de cima da esquerda p/ direita, depois a de baixo) -> camera
k = 0
for linha, zc in enumerate((2.02, 1.5)):
    for coluna, xc in enumerate((-.83, 0, .83)):
        cam = CAMS_TELA[k]; k += 1
        caixa("GuaritaC_Monitor_Moldura", (.8, .05, .48), (xc, YM - .03, zc), M["preto"])
        tela("CFTV_Tela_%d_c%d" % (k, cam), .76, .43, (xc, YM - .056, zc))
caixa("GuaritaC_Mesa_Tampo", (2.7, .66, .04), (0, YM - .38, .76), M["mesa"])
for s in (-1, 1):
    caixa("GuaritaC_Mesa_Lateral", (.04, .62, .74), (s * 1.3, YM - .38, .37), M["mesa"])
caixa("GuaritaC_Mesa_Fundo", (2.56, .02, .5), (0, YM - .08, .5), M["mesa"])
# monitores da mesa (24"), virados para o operador; o da esquerda mostra a camera da casa 147 ampliada
for i, (xc, cam) in enumerate(((-.48, 3), (.48, 2))):
    caixa("GuaritaC_Monitor_Mesa", (.56, .04, .34), (xc, YM - .2, 1.06), M["preto"])
    caixa("GuaritaC_Monitor_Haste", (.04, .03, .2), (xc, YM - .18, .88), M["preto"])
    caixa("GuaritaC_Monitor_Pe", (.22, .16, .015), (xc, YM - .2, .787), M["preto"])
    tela("CFTV_Tela_%d_c%d" % (7 + i, cam), .52, .3, (xc, YM - .222, 1.06))
caixa("GuaritaC_Teclado", (.44, .15, .02), (0, YM - .5, .79), M["preto"])
caixa("GuaritaC_Mouse", (.06, .1, .025), (.32, YM - .5, .79), M["preto"])
caixa("GuaritaC_Joystick_Base", (.3, .18, .05), (-.48, YM - .52, .805), M["preto"])
cilindro("GuaritaC_Joystick_Haste", .015, .12, (-.4, YM - .52, .89), M["preto"], seg=10)
cilindro("GuaritaC_Joystick_Bola", .028, .05, (-.4, YM - .52, .96), M["preto"], seg=12, r2=.018)
for j in range(6):                       # botoes das cameras no joystick
    caixa("GuaritaC_Joystick_Botao", (.025, .025, .006), (-.6 + (j % 3) * .035, YM - .49 - (j // 3) * .04, .833), M["led_verde" if j == 2 else "cromo"])
caixa("GuaritaC_Radio_HT", (.06, .035, .14), (.85, YM - .45, .85), M["preto"])
cilindro("GuaritaC_Radio_Antena", .006, .16, (.865, YM - .45, 1.0), M["preto"], seg=8)
caixa("GuaritaC_Radio_LED", (.012, .004, .008), (.84, YM - .4685, .9), M["led_verde"])
caixa("GuaritaC_Telefone", (.18, .2, .06), (1.05, YM - .35, .81), M["preto"])
cilindro("GuaritaC_Caneca", .04, .1, (.62, YM - .62, .83), M["caneca"], seg=16)

# cadeira do operador (de costas para a janela)
cx, cy = .05, YM - 1.05
cilindro("GuaritaC_Cadeira_Coluna", .025, .38, (cx, cy, .24), M["cromo"], seg=12)
for j in range(5):
    a = j * 2 * PI / 5 + .3
    caixa("GuaritaC_Cadeira_Pe", (.3, .04, .03), (cx + math.cos(a) * .15, cy + math.sin(a) * .15, .06), M["preto"], rot=(0, 0, a))
    cilindro("GuaritaC_Cadeira_Rodinha", .025, .03, (cx + math.cos(a) * .29, cy + math.sin(a) * .29, .03), M["preto"], rot=(PI / 2, 0, a), seg=10)
caixa("GuaritaC_Cadeira_Assento", (.5, .48, .08), (cx, cy, .48), M["tecido"])
caixa("GuaritaC_Cadeira_Encosto", (.46, .07, .6), (cx, cy - .26, .86), M["tecido"], rot=(-.12, 0, 0))
for s in (-1, 1):
    caixa("GuaritaC_Cadeira_Braco", (.05, .3, .04), (cx + s * .27, cy - .02, .68), M["preto"])
    caixa("GuaritaC_Cadeira_Braco_Haste", (.03, .03, .18), (cx + s * .27, cy - .02, .58), M["preto"])

# rack com o gravador (NVR), no canto oeste
rx, ry = -L / 2 + E + .26, -.15
caixa("GuaritaC_Rack", (.48, .5, .95), (rx, ry, .475), M["preto"])
for j, z in enumerate((.82, .7, .58)):
    caixa("GuaritaC_Rack_Equip", (.44, .02, .08), (rx, ry - .255, z), M["mesa"])
    for n in range(4):
        caixa("GuaritaC_Rack_LED", (.012, .004, .012), (rx - .15 + n * .03, ry - .267, z), M["led_azul" if n == 0 else "led_verde"])
caixa("GuaritaC_Rack_Switch_LED", (.012, .004, .012), (rx + .17, ry - .267, .82), M["led_verm"])

# parede oeste: relogio; parede leste: extintor e quadro de avisos
xo, xl = -L / 2 + E + .01, L / 2 - E - .01
cilindro("GuaritaC_Relogio", .14, .03, (xo, .55, 2.25), M["papel"], rot=(0, PI / 2, 0), seg=24)
cilindro("GuaritaC_Relogio_Aro", .155, .025, (xo - .002, .55, 2.25), M["preto"], rot=(0, PI / 2, 0), seg=24)
caixa("GuaritaC_Relogio_Ponteiro", (.006, .01, .1), (xo + .02, .55, 2.29), M["preto"])
caixa("GuaritaC_Relogio_Ponteiro2", (.006, .075, .01), (xo + .02, .58, 2.25), M["preto"])
# quadro de avisos na parede oeste (a leste agora tem a porta), acima do rack e do balcao
caixa("GuaritaC_Quadro_Avisos", (.02, .7, .5), (xo, -.75, 1.75), M["cortica"])
for j, (dy, dz) in enumerate(((-.18, .08), (.05, .1), (.2, -.06), (-.05, -.12))):
    caixa("GuaritaC_Aviso_Papel", (.006, .16, .2), (xo + .013, -.75 + dy, 1.75 + dz), M["papel"])
# extintor na parede leste, entre a porta (ate y 0,18) e a mesa (a partir de y 0,42)
cilindro("GuaritaC_Extintor", .075, .5, (xl - .09, .3, .45), M["extintor"], seg=16)
cilindro("GuaritaC_Extintor_Valvula", .025, .08, (xl - .09, .3, .74), M["preto"], seg=10)

# luz interna fria e fraca (sala de monitoramento)
for o in [o for o in bpy.data.objects if o.name == "GuaritaC_Luz_Interna"]:
    bpy.data.objects.remove(o, do_unlink=True)
ld = bpy.data.lights.get("GuaritaC_Luz_Interna") or bpy.data.lights.new("GuaritaC_Luz_Interna", "AREA")
ld.energy = 30; ld.size = .6; ld.color = lin("#e2eaff")
lo = bpy.data.objects.new("GuaritaC_Luz_Interna", ld); C_GUA.objects.link(lo)
lo.location = ORIG + Vector((0, .15, H - .06))

# ------------------------------------------------------------------ 3. cameras de CFTV (modelo + CAMERA para o three.js)
CAMERAS = [   # n, nome no monitor, posicao, alvo, poste em que fica (ou None = laje da guarita)
    (1, "PORTARIA", ORIG + Vector((1.75, -1.55, 2.62)), Vector((36.5, -21.5, .3)), None),
    (2, "RUA - SENTIDO OESTE", ORIG + Vector((-1.75, -1.55, 2.62)), Vector((8, -20, 0)), None),
    (3, "CASA 147", Vector((-8, -16.25, 4.6)), Vector((3, -15.6, .4)), "Poste_2_Coluna"),
    (4, "RUA - TRECHO CENTRAL", Vector((20, -16.25, 4.6)), Vector((-6, -21, 0)), "Poste_4_Coluna"),
    (5, "CALCADA 150-160", Vector((6, -16.25, 4.2)), Vector((20, -14.6, .2)), "Poste_3_Coluna"),
    (6, "ENTRADA / CANCELA", Vector((29, -24.75, 4.6)), Vector((39, -17.5, .5)), "Poste_Oposto_3_Coluna"),
]
for n, rotulo, pos, alvo, poste in CAMERAS:
    d = (alvo - pos).normalized()
    horiz = Vector((d.x, d.y, 0)).normalized()
    p_cam = pos + horiz * .3 if poste else pos           # fica 30 cm para fora do poste, do lado para onde olha
    q = d.to_track_quat("Y", "Z")
    corpo = caixa("CFTV_Modelo_%d_Corpo" % n, (.1, .28, .1), p_cam, M["cam_caixa"], C_RUA, local=False)
    corpo.rotation_mode = "QUATERNION"; corpo.rotation_quaternion = q
    for nome, tam, off, mt in (("Aba", (.13, .32, .012), (0, .02, .062), M["cam_caixa"]),
                               ("Lente", (.07, .012, .07), (0, .145, 0), M["cam_lente"]),
                               ("IR", (.085, .008, .02), (0, .146, -.045), M["cam_ir"])):
        o = caixa("CFTV_Modelo_%d_%s" % (n, nome), tam, (0, 0, 0), mt, C_RUA, local=False)
        o.parent = corpo; o.location = off
    # suporte: do poste (ou da parede) ate a camera
    base = pos if poste else pos + Vector((0, .25, .05))
    meio = (base + p_cam) / 2; comp = (p_cam - base).length
    sup = caixa("CFTV_Modelo_%d_Suporte" % n, (.04, max(comp, .05), .04), meio + Vector((0, 0, .02)), M["ferragem"], C_RUA, local=False)
    sup.rotation_mode = "QUATERNION"; sup.rotation_quaternion = (p_cam - base).to_track_quat("Y", "Z") if comp > .01 else sup.rotation_quaternion
    if poste:
        cilindro("CFTV_Modelo_%d_Abracadeira" % n, .11, .08, pos + Vector((0, 0, .02)), M["ferragem"], C_RUA, seg=16, local=False)
    # camera que o three.js usa para renderizar a imagem do monitor
    cd = bpy.data.cameras.get("CFTV_Cam_%d" % n) or bpy.data.cameras.new("CFTV_Cam_%d" % n)
    cd.lens = 21; cd.sensor_width = 36
    co = bpy.data.objects.new("CFTV_Cam_%d" % n, cd); C_CFTV.objects.link(co)
    co.location = p_cam + d * .16
    co.rotation_mode = "QUATERNION"; co.rotation_quaternion = (-d).to_track_quat("Z", "Y")
    co["cftv_rotulo"] = rotulo

n_obj = sum(1 for o in bpy.data.objects if o.name.startswith(("GuaritaC_", "CFTV_")))
say("guarita oca com central de monitoramento: %d objetos, 8 telas, %d cameras" % (n_obj, len(CAMERAS)))
bpy.ops.wm.save_mainfile()
