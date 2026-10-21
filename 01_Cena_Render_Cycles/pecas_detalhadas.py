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
# talheres modelados pelo usuario: se existirem modelos/talher_garfo.glb e modelos/talher_faca.glb, entram no lugar
# dos de contorno (deitados, mesma posicao, ~20 cm, aco escovado, simplificados para o Quest)
import os
PASTA_MOD = os.path.join(os.path.dirname(bpy.data.filepath), "modelos")
MAX_TRIS_TALHER = 2500

def malha_glb(arquivo, nome, comprimento, ponta):
    """Importa o .glb e devolve a malha: eixo maior -> Y (cabo em -Y), mais fino -> Z (deitado), centrada.
    ponta="larga": a ponta mais larga vai para +Y (dentes do garfo); "fina": a ponta mais fina vai para +Y (lamina)."""
    caminho = os.path.join(PASTA_MOD, arquivo)
    if not os.path.exists(caminho):
        return None
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=caminho)
    novos = [o for o in bpy.data.objects if o not in antes]
    bpy.context.view_layer.update()
    fonte = next(o for o in novos if o.type == "MESH")
    vs = [fonte.matrix_world @ v.co for v in fonte.data.vertices]
    ext = [max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3)]
    eixo_y, eixo_x, eixo_z = sorted(range(3), key=lambda i: -ext[i])          # maior, medio, menor
    R = Matrix.Identity(3)
    for linha, eixo in enumerate((eixo_x, eixo_y, eixo_z)):
        R[linha] = Vector([1.0 if j == eixo else 0.0 for j in range(3)])
    p = [R @ v for v in vs]
    y0, y1 = min(v.y for v in p), max(v.y for v in p)
    def faixa(a, b, idx):                 # extensao no eixo idx dos vertices com y entre a e b
        sel = [v[idx] for v in p if a <= v.y <= b]
        return max(sel) - min(sel) if sel else 0
    L = y1 - y0
    topo_x, base_x = faixa(y1 - .15 * L, y1, 0), faixa(y0, y0 + .15 * L, 0)
    topo_z, base_z = faixa(y1 - .15 * L, y1, 2), faixa(y0, y0 + .15 * L, 2)
    virar = (topo_x < base_x) if ponta == "larga" else (topo_z > base_z)
    if virar:
        R = Matrix.Rotation(math.pi, 3, "X") @ R                         # gira 180 graus (nao espelha)
    if R.determinant() < 0:
        R = Matrix.Diagonal((-1, 1, 1)) @ R
    s = comprimento / L
    M4 = Matrix.Scale(s, 4) @ R.to_4x4() @ fonte.matrix_world
    me = fonte.data.copy(); me.name = nome
    me.transform(M4)
    c = [(min(v.co[i] for v in me.vertices) + max(v.co[i] for v in me.vertices)) / 2 for i in range(3)]
    me.transform(Matrix.Translation((-c[0], -c[1] - .005, -c[2])))      # mesmo centro do talher antigo (y -0,10..0,11)
    tris = sum(len(pl.vertices) - 2 for pl in me.polygons)
    if tris > MAX_TRIS_TALHER:                                           # simplifica para o Quest
        tmp = bpy.data.objects.new("_tmp_talher", me); bpy.context.scene.collection.objects.link(tmp)
        d = tmp.modifiers.new("Simplificar", "DECIMATE"); d.ratio = MAX_TRIS_TALHER / tris
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg)); me2.name = nome
        bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(me)
        me = me2
    me.materials.clear()
    for pl in me.polygons:
        pl.use_smooth = True
    for o in novos:
        bpy.data.objects.remove(o, do_unlink=True)
    return me

for i in (1, 2):
    ob = bpy.data.objects.get("Garfo_%d" % i)
    if not ob:
        continue
    for c in list(ob.children):
        bpy.data.objects.remove(c, do_unlink=True)
    trocar(ob, malha_glb("talher_garfo.glb", ob.name, .20, "larga") or chapa(ob.name, contorno_garfo(), .0028))
    ob.data.materials.clear(); ob.data.materials.append(M_TALHER)
    nome_faca = "Faca_Mesa_%d" % i
    velho = bpy.data.objects.get(nome_faca)
    if velho:
        bpy.data.objects.remove(velho, do_unlink=True)
    fme = malha_glb("talher_faca.glb", nome_faca, .21, "fina") or chapa(nome_faca, FACA, .0024)
    fme.materials.append(M_TALHER)
    fo = bpy.data.objects.new(nome_faca, fme)
    for c in ob.users_collection:
        c.objects.link(fo)
    fo.parent = ob.parent; fo.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
    fo.location = ob.location.copy(); fo.location.x -= .34; fo.rotation_euler = ob.rotation_euler.copy()
    fo["detalhado"] = True
    feitos += [ob.name, nome_faca]

# ---------------- prato feito: bife e batata frita (modelos/comida.glb do usuario)
# comida.glb traz o bife (malha achatada) e uma batata (palito). O bife recebe a textura da vista de cima de
# modelos/bife_referencia.png; a batata, uma textura dourada gerada aqui. Em cada prato: arroz e feijao atras,
# bife na frente a esquerda e ~10 batatas espalhadas na frente a direita (de quem esta sentado, em -Y).
import random
import numpy as np
COMIDA = os.path.join(PASTA_MOD, "comida.glb")

def alinhar(me, comprimento):
    """Eixo principal (PCA) -> X, eixo mais fino -> Z; escala pelo comprimento; centrado em XY com a base em z=0."""
    co = np.array([v.co[:] for v in me.vertices]); co -= co.mean(0)
    w, V = np.linalg.eigh(np.cov(co.T))
    R = V[:, ::-1].T                                     # linhas: maior, medio, menor variancia
    if np.linalg.det(R) < 0:
        R[1] *= -1
    me.transform(Matrix.Translation(-Vector(np.array([v.co[:] for v in me.vertices]).mean(0))))
    me.transform(Matrix([list(R[0]) + [0], list(R[1]) + [0], list(R[2]) + [0], [0, 0, 0, 1]]))
    xs = [v.co.x for v in me.vertices]
    me.transform(Matrix.Scale(comprimento / (max(xs) - min(xs)), 4))
    c = [(min(v.co[i] for v in me.vertices) + max(v.co[i] for v in me.vertices)) / 2 for i in range(2)]
    me.transform(Matrix.Translation((-c[0], -c[1], -min(v.co.z for v in me.vertices))))
    return me

F_LADO = .22                                             # faixa de baixo do atlas do bife = vista lateral

def textura_bife():
    """Atlas do bife a partir da referencia: em cima (v de F_LADO a 1) a vista de cima (metade esquerda da imagem),
    embaixo (v de 0 a F_LADO) a vista lateral (metade direita). Devolve (imagem, mascara da carne na vista de cima)."""
    img = bpy.data.images.get("Bife_Grelhado_Cor")
    if img:
        bpy.data.images.remove(img)
    ref = bpy.data.images.load(os.path.join(PASTA_MOD, "bife_referencia.png"))
    W, H = ref.size
    px4 = np.array(ref.pixels[:], np.float32).reshape(H, W, 4)
    def recorte(x0, x1):                                  # fundo branco ou transparente fora; borda = cor media
        p = px4[:, x0:x1]
        carne = (p[..., :3].min(-1) < .82) & (p[..., 3] > .5)
        ys, xs = np.where(carne)
        rec = p[ys.min():ys.max() + 1, xs.min():xs.max() + 1, :3].copy()
        mk = carne[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        rec[~mk] = rec[mk].mean(0)
        return rec, mk
    def redim(a, h, w):                                   # vizinho mais proximo
        return a[(np.arange(h) * a.shape[0] // h)[:, None], (np.arange(w) * a.shape[1] // w)[None, :]]
    cima, mk = recorte(0, W // 2)
    lado, mk_lado = recorte(W // 2, W)
    lado = lado[mk_lado.any(1)]                           # so as linhas com carne
    S = 1024; hl = int(S * F_LADO)
    atlas = np.ones((S, S, 4), np.float32)
    atlas[:hl, :, :3] = redim(lado, hl, S)
    atlas[hl:, :, :3] = redim(cima, S - hl, S)
    img = bpy.data.images.new("Bife_Grelhado_Cor", S, S, alpha=False)
    img.pixels.foreach_set(atlas.ravel()); img.scale(512, 512); img.pack()
    bpy.data.images.remove(ref)
    return img, mk

def uv_como_modelado(me, mk):
    """O bife foi modelado sobre a vista de cima da referencia: a silhueta da malha no plano dos 2 eixos maiores
    e a mesma da imagem. Faces de cima/baixo: projecao nesse plano (bbox da malha -> recorte da vista de cima), com o
    espelhamento/troca de eixos em que os vertices caem dentro da carne. Faces da borda: vista lateral (u = mesma
    posicao horizontal, v = altura no eixo fino)."""
    co = np.array([v.co[:] for v in me.vertices])
    ext = co.max(0) - co.min(0); a, b, c = sorted(range(3), key=lambda i: -ext[i])
    n = (co - co.min(0)) / np.maximum(ext, 1e-9)
    h, w = mk.shape; melhor = None
    for troca in (False, True):
        for fu in (False, True):
            for fv in (False, True):
                u = n[:, b if troca else a]; v = n[:, a if troca else b]
                u = 1 - u if fu else u; v = 1 - v if fv else v
                dentro = mk[np.clip((v * (h - 1)).round().astype(int), 0, h - 1), np.clip((u * (w - 1)).round().astype(int), 0, w - 1)].mean()
                if melhor is None or dentro > melhor[0]:
                    melhor = (dentro, u.copy(), v.copy())
    _, U, V = melhor
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    lados = 0
    for pl in me.polygons:
        borda = abs(pl.normal[c]) < .5                    # normal quase paralela ao plano da silhueta
        lados += borda
        for li in pl.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = (float(U[vi]), float(n[vi, c]) * F_LADO * .98 + .002) if borda else (float(U[vi]), F_LADO + float(V[vi]) * (1 - F_LADO))
    print("[DETALHE] textura do bife: %.0f%% dos vertices dentro da carne; %d faces da borda com a vista lateral" % (melhor[0] * 100, lados))

def textura_batata(enc):
    """Recorte da batata da referencia em que a malha foi modelada (modelos/batata_encaixe.json); fundo -> cor media."""
    img = bpy.data.images.get("Batata_Frita_Cor")
    if img:
        bpy.data.images.remove(img)
    ref = bpy.data.images.load(os.path.join(PASTA_MOD, enc["imagem"]))
    W, H = ref.size
    px4 = np.array(ref.pixels[:], np.float32).reshape(H, W, 4)
    x, y, w, h = enc["x"], enc["y"], enc["w"], enc["h"]
    rec = px4[y:y + h, x:x + w].copy()
    r, g, b = rec[..., 0], rec[..., 1], rec[..., 2]
    frita = (r > .75) & (g > .5) & (b < .55) & (r - b > .3) & (rec[..., 3] > .5)
    rec[~frita, :3] = rec[frita, :3].mean(0); rec[..., 3] = 1
    img = bpy.data.images.new("Batata_Frita_Cor", w, h, alpha=False)
    img.pixels.foreach_set(rec.ravel()); img.scale(256, 256); img.pack()
    bpy.data.images.remove(ref)
    return img

def uv_batata(me, enc):
    """Mesma projecao do encaixe: plano (a, b) -> pixels do recorte."""
    co = np.array([v.co[:] for v in me.vertices])[:, [enc["a"], enc["b"]]]
    if enc["troca"]:
        co = co[:, ::-1]
    Q = co * np.array([enc["fu"], enc["fv"]]) * enc["s"] - np.array(enc["min"])
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for l in me.loops:
        q = Q[l.vertex_index]
        uv.data[l.index].uv = (float(q[0] / enc["w"]), float(q[1] / enc["h"]))

def mat_imagem(nome, img, rough):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    for n in [n for n in nt.nodes if n.type == "TEX_IMAGE"]:
        nt.nodes.remove(n)
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*[img.pixels[i] for i in (0, 1, 2)], 1)
    return m

for o in [o for o in bpy.data.objects if o.name.startswith(("Bife_Prato_", "Batatas_Prato_"))]:
    bpy.data.objects.remove(o, do_unlink=True)
if os.path.exists(COMIDA):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=COMIDA)
    novos = [o for o in bpy.data.objects if o not in antes]
    bpy.context.view_layer.update()
    malhas = sorted((o for o in novos if o.type == "MESH"), key=lambda o: -len(o.data.polygons))
    def copia_mundo(o):
        me = o.data.copy(); me.transform(o.matrix_world); return me
    img_bife, mk_bife = textura_bife()
    me_bife = copia_mundo(malhas[0])                     # o maior e o bife
    uv_como_modelado(me_bife, mk_bife)                   # a textura e projetada no plano em que o bife foi modelado
    me_bife = alinhar(me_bife, .12)                      # ~12 x 8 cm, deitado
    import json
    enc_bat = json.load(open(os.path.join(PASTA_MOD, "batata_encaixe.json")))
    me_bat = copia_mundo(malhas[1])
    uv_batata(me_bat, enc_bat)                           # textura da batata em que ela foi modelada
    me_bat = alinhar(me_bat, 1.0)                        # palito com comprimento 1, escalado em cada batata
    for o in novos:
        bpy.data.objects.remove(o, do_unlink=True)
    M_BIFE = mat_imagem("Bife_Grelhado", img_bife, .55)
    M_BATATA = mat_imagem("Batata_Frita", textura_batata(enc_bat), .6)
    me_bife.materials.clear(); me_bife.materials.append(M_BIFE)
    for p in me_bife.polygons:
        p.use_smooth = True
    for i in (1, 2):
        prato = bpy.data.objects.get("Prato_%d" % i)
        if not prato:
            continue
        P = prato.location
        piso = P.z - .0003                                  # fundo do prato
        rr = random.Random(40 + i)
        # arroz e feijao para tras, um pouco menores
        for nome, dx, dy, esc in (("Arroz_%d" % i, -.03, .042, .72), ("Feijao_%d" % i, .045, .04, .78)):
            a = bpy.data.objects.get(nome)
            if a:
                a.location = (P.x + dx, P.y + dy, a.location.z); a.scale = (esc, esc, 1)
        bife = bpy.data.objects.new("Bife_Prato_%d" % i, me_bife if i == 1 else me_bife.copy())
        for c in prato.users_collection: c.objects.link(bife)
        bife.parent = prato.parent; bife.matrix_parent_inverse = prato.matrix_parent_inverse.copy()
        bife.location = (P.x - .035, P.y - .032, piso); bife.rotation_euler = (0, 0, rr.uniform(.35, .6))
        bife["detalhado"] = True
        # batatas: um monte espalhado, umas por cima das outras
        LY = max(v.co.y for v in me_bat.vertices) - min(v.co.y for v in me_bat.vertices)     # grossura do palito original
        LZ = max(v.co.z for v in me_bat.vertices) - min(v.co.z for v in me_bat.vertices)
        bm = bmesh.new()
        for k in range(13):
            L = rr.uniform(.045, .068); g = rr.uniform(.0065, .0085)
            cam = 0 if k < 6 else (1 if k < 10 else 2)
            T = (Matrix.Translation((.05 + rr.uniform(-.026, .022), -.035 + rr.uniform(-.03, .03), cam * .0068))
                 @ Matrix.Rotation(rr.uniform(-.12, .12), 4, "X") @ Matrix.Rotation(rr.uniform(0, math.pi), 4, "Z")
                 @ Matrix.Diagonal((L, g / LY, g / LZ, 1)))
            tmp = me_bat.copy(); tmp.transform(T); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        me = bpy.data.meshes.new("Batatas_Prato_%d" % i); bm.to_mesh(me); bm.free()
        me.materials.append(M_BATATA)
        for p in me.polygons:
            p.use_smooth = True
        bat = bpy.data.objects.new("Batatas_Prato_%d" % i, me)
        for c in prato.users_collection: c.objects.link(bat)
        bat.parent = prato.parent; bat.matrix_parent_inverse = prato.matrix_parent_inverse.copy()
        bat.location = (P.x, P.y, piso); bat["detalhado"] = True
        feitos += [bife.name, bat.name]

print("[DETALHE] %d pecas remodeladas: %s" % (len(feitos), ", ".join(feitos)))
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[DETALHE] cena principal salva")
