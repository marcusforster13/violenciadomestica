"""
A Casa em Silencio - viatura da PMERJ refeita (SUV compacto de patrulha, ~4,34 x 1,82 m, sem marca).

Refaz a carroceria e as pecas da Viatura_PMERJ mantendo o que ja funciona: giroflex (base, lentes, luzes
animadas), antena, posicao na rua e os materiais da cena. A carroceria e um "loft" de 20 secoes com vidros
separados (para-brisa inclinado, janelas das portas e vigia), colunas pretas, estreitamento do teto,
saias plasticas pretas, para-choques moldados, rodas com pneu e aro, e o padrao de pintura
(branco com faixa azul, POLICIA MILITAR, 190, PMERJ e espaco do brasao).
Tambem tira os carros das garagens dos vizinhos (menos poligonos) e simplifica o carro vermelho da rua.

Idempotente. Uso:  blender -b casa_em_silencio.blend --python viatura.py
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

PI = math.pi
def say(m): print("[VIATURA] " + m)

VTR = bpy.data.objects["Viatura_PMERJ"]
COL = VTR.users_collection[0]
MANTER = ("Giroflex_", "Viatura_Antena", "Viatura_PMERJ_Farol_Luz")

def mat(prefixo):
    m = bpy.data.materials.get(prefixo)
    if m: return m
    return next(x for x in bpy.data.materials if x.name.startswith(prefixo))

def novo_mat(nome, cor, rough=.5, metal=0.0, emit=None, forca=0.0):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*cor, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = forca
    m.diffuse_color = (*cor, 1)
    return m

M = {
    "pint": mat("Viatura_PMERJ_Pintura"), "faixa": mat("Pintura_Faixa_Azul"), "plast": mat("Plastico_Preto_Texturizado"),
    "vidro": mat("Vidro_Carro_Fume"), "preto": mat("Preto_Brilhante"), "cromo": mat("Cromado"), "pneu": mat("Borracha_Pneu"),
    "disco": mat("Disco_Freio"), "farol": mat("Farol_Aceso"), "lanterna": mat("Lanterna_Acesa"), "interior": mat("Interior_Carro"),
    "texto": mat("Adesivo_Texto"), "placa": mat("Placa_Mercosul"), "placa_azul": mat("Placa_Faixa_Azul"), "placa_txt": mat("Placa_Texto"),
    "brasao": mat("Brasao_(inserir_imagem_oficial)"), "dourado": mat("Dourado"),
    # aro claro (le melhor a noite) e protetor de carter prata, como nos SUVs compactos
    "aro": novo_mat("Roda_Viatura", (.62, .64, .67), .32, .85),
    "prata": novo_mat("Protetor_Prata", (.55, .56, .58), .4, .6),
    "drl": novo_mat("Farol_DRL", (.9, .92, 1.0), .2, 0, (.85, .9, 1.0), 12),
    "refletor": novo_mat("Refletor_Ambar", (.9, .45, .05), .3, 0, (1.0, .45, .0), 1.5),
}

# ------------------------------------------------------------------ modelo do usuario (opcional)
# Se existir  modelos/viatura_usuario.glb  ele entra no lugar da viatura procedural, com o nosso giroflex no teto.
# Para voltar a viatura antiga: tire (ou renomeie) esse arquivo e rode o atualizar_tudo.ps1.
import os
import numpy as np
MODELO_USUARIO = os.path.join(os.path.dirname(bpy.data.filepath), "modelos", "viatura_usuario.glb")
USAR_MODELO = os.path.exists(MODELO_USUARIO)
ESCALA_MODELO = .042            # 98 unidades de comprimento -> ~4,1 m (escala unica para as rodas nao ficarem ovais)
GIRO_X = .15                    # posicao do giroflex ao longo do carro (0 = centro; + = para a frente)

def mover_equipamentos(dx_giro=0.0, dz_giro=0.0, antena=None, farol_x=None):
    """Giroflex, antena e luzes dos farois guardam a posicao original (pos0) e sao deslocados a partir dela."""
    for o in VTR.children:
        if not o.name.startswith(MANTER): continue
        if "pos0" not in o: o["pos0"] = list(o.location)
        x, y, z = o["pos0"]
        if o.name.startswith("Giroflex_"): o.location = (x + dx_giro, y, z + dz_giro)
        elif o.name.startswith("Viatura_Antena"): o.location = antena if antena else (x, y, z)
        elif o.name.startswith("Viatura_PMERJ_Farol_Luz"): o.location = (farol_x if farol_x is not None else x, y, z)

def apagar_emblema(ob, img_cor, img_normal):
    """Apaga o emblema do fabricante na grade dianteira (regra do projeto: sem marcas). A area e definida no
    espaco do modelo original; os pixels da textura que caem nela recebem a cor escura da grade e relevo liso."""
    me = ob.data; uvl = me.uv_layers.active.data; Mw = ob.matrix_world.copy()
    W, H = img_cor.size
    cor = np.array(img_cor.pixels[:], np.float32).reshape(H, W, 4)
    nor = np.array(img_normal.pixels[:], np.float32).reshape(img_normal.size[1], img_normal.size[0], 4) if img_normal else None
    X0, X1, Z0, Z1, YMAX = -5.6, 5.3, 16.6, 20.1, -44.0        # caixa do emblema (frente do carro em -Y)
    mask = np.zeros((H, W), bool)
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        P = [Mw @ me.vertices[me.loops[l].vertex_index].co for l in t.loops]      # coordenadas do arquivo original
        if min(q.y for q in P) > YMAX or max(q.x for q in P) < X0 or min(q.x for q in P) > X1 or max(q.z for q in P) < Z0 or min(q.z for q in P) > Z1: continue
        U = [uvl[l].uv for l in t.loops]
        us = [u.x * W for u in U]; vs = [u.y * H for u in U]
        a0, a1 = max(0, int(min(us))), min(W - 1, int(max(us)) + 1); b0, b1 = max(0, int(min(vs))), min(H - 1, int(max(vs)) + 1)
        if a1 <= a0 or b1 <= b0: continue
        gx, gy = np.meshgrid(np.arange(a0, a1 + 1) + .5, np.arange(b0, b1 + 1) + .5)
        den = (vs[1] - vs[2]) * (us[0] - us[2]) + (us[2] - us[1]) * (vs[0] - vs[2])
        if abs(den) < 1e-9: continue
        w0 = ((vs[1] - vs[2]) * (gx - us[2]) + (us[2] - us[1]) * (gy - vs[2])) / den
        w1 = ((vs[2] - vs[0]) * (gx - us[2]) + (us[0] - us[2]) * (gy - vs[2])) / den
        w2 = 1 - w0 - w1
        dentro = (w0 >= -.01) & (w1 >= -.01) & (w2 >= -.01)
        px = w0 * P[0].x + w1 * P[1].x + w2 * P[2].x; pz = w0 * P[0].z + w1 * P[1].z + w2 * P[2].z
        dentro &= (px > X0) & (px < X1) & (pz > Z0) & (pz < Z1)
        mask[b0:b1 + 1, a0:a1 + 1] |= dentro
    n = int(mask.sum())
    if not n: return 0
    brilho = cor[..., :3].sum(-1)[mask]
    escuro = cor[..., :3][mask][brilho <= np.percentile(brilho, 8)].mean(0) * .85   # o preto mais fundo da grade
    ruido = (np.random.default_rng(3).standard_normal((n, 1)) * .003).astype(np.float32)
    cor[..., :3][mask] = np.clip(escuro + ruido, 0, 1)
    img_cor.pixels.foreach_set(cor.ravel()); img_cor.update(); img_cor.pack()
    if nor is not None and nor.shape[:2] == (H, W):
        nor[..., :3][mask] = (.5, .5, 1.0)
        img_normal.pixels.foreach_set(nor.ravel()); img_normal.update(); img_normal.pack()
    return n

def usar_modelo_usuario():
    for m in M.values(): m.use_fake_user = True     # guarda os materiais da viatura antiga para poder voltar a ela
    for o in list(VTR.children_recursive):
        if not o.name.startswith(MANTER):
            bpy.data.objects.remove(o, do_unlink=True)
    for m in [m for m in bpy.data.materials if m.name.startswith("Viatura_Modelo_Usuario")]: bpy.data.materials.remove(m)
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=MODELO_USUARIO)
    novos = [o for o in bpy.data.objects if o not in antes]
    malhas = [o for o in novos if o.type == "MESH"]
    ob = malhas[0]
    # texturas em 2048 px (4096 pesa demais no Quest) e sem o emblema do fabricante
    mat_ = ob.data.materials[0]; mat_.name = "Viatura_Modelo_Usuario"
    imgs = {n.image for n in mat_.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}
    for im in imgs:
        if max(im.size) > 2048: im.scale(2048, 2048)
        im.pack()
    cor_n = next((n for n in mat_.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"), None)
    nor_n = next((n for n in mat_.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and "normal" in n.image.name.lower()), None)
    apagados = apagar_emblema(ob, cor_n.image, nor_n.image if nor_n else None) if cor_n else 0
    # leva a malha para o espaco da viatura: frente do modelo (-Y) vira +X, escala real, rodas no chao, centrada
    Mw = ob.matrix_world.copy()
    R = Matrix.Rotation(PI / 2, 4, "Z") @ Matrix.Scale(ESCALA_MODELO, 4)
    ob.data.transform(R @ Mw)
    vs = ob.data.vertices
    cx = (min(v.co.x for v in vs) + max(v.co.x for v in vs)) / 2; cy = (min(v.co.y for v in vs) + max(v.co.y for v in vs)) / 2
    ob.data.transform(Matrix.Translation((-cx, -cy, -min(v.co.z for v in vs))))
    ob.data.update()
    for c in list(ob.users_collection): c.objects.unlink(ob)
    COL.objects.link(ob)
    ob.parent = VTR; ob.matrix_parent_inverse = Matrix.Identity(4); ob.matrix_basis = Matrix.Identity(4)
    ob.name = "Viatura_PMERJ_Modelo"; ob.data.name = "Viatura_PMERJ_Modelo"
    for pl in ob.data.polygons: pl.use_smooth = True
    ob["detalhado"] = True; ob["uv_proprio"] = True; ob["modelo_usuario"] = "viatura_usuario.glb"
    for o in novos:
        if o is not ob: bpy.data.objects.remove(o, do_unlink=True)
    # altura do teto onde vai o giroflex (maior ponto sob a base de 0,34 x 1,3 m) e onde vai a antena
    def teto(x, ys=(0, -.25, .25, -.45, .45)):
        z = 0
        for y in ys:
            for dx in (-.15, 0, .15):
                ok, lc, _, _ = ob.ray_cast(Vector((x + dx, y, 5)), Vector((0, 0, -1)))
                if ok: z = max(z, lc.z)
        return z
    bpy.context.view_layer.update()
    z_giro = teto(GIRO_X)
    frente = max(v.co.x for v in vs)
    x_ant = -1.05; z_ant = teto(x_ant, ys=(.25,))
    mover_equipamentos(dx_giro=GIRO_X - (-.1), dz_giro=z_giro - 1.66, antena=(x_ant, .25, z_ant + .22), farol_x=frente + .03)
    dims = ob.dimensions
    say("modelo do usuario no lugar da viatura: %.2f x %.2f x %.2f m, %d triangulos, texturas 2048 px, giroflex a %.2f m do chao%s"
        % (dims.x, dims.y, dims.z, sum(len(pl.vertices) - 2 for pl in ob.data.polygons), z_giro,
           (", emblema da grade apagado (%d px)" % apagados) if apagados else ""))

# Se existir  modelos/viatura_pronta.glb  (carro ja em metros, frente para +X - ex.: a viatura exportada do projeto
# Busca e Apreensao), ele tem prioridade. O giroflex que vier no arquivo e descartado: fica o nosso, no teto.
# Para voltar: tire o arquivo e rode o atualizar_tudo.ps1.
MODELO_PRONTO = os.path.join(os.path.dirname(bpy.data.filepath), "modelos", "viatura_pronta.glb")

def usar_viatura_pronta():
    for m in M.values(): m.use_fake_user = True     # guarda os materiais da viatura antiga para poder voltar a ela
    for o in list(VTR.children_recursive):          # fica so com o nosso giroflex, a antena e as luzes dos farois
        if not o.name.startswith(MANTER):
            bpy.data.objects.remove(o, do_unlink=True)
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=MODELO_PRONTO)
    novos = [o for o in bpy.data.objects if o not in antes]
    for o in [o for o in novos if o.name.startswith("Giroflex_")]:     # o giroflex do arquivo sai; fica o nosso
        novos.remove(o); bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    malhas = [o for o in novos if o.type == "MESH"]
    for o in malhas:
        mw = o.matrix_world.copy()
        for c in list(o.users_collection): c.objects.unlink(o)
        COL.objects.link(o)
        o.parent = VTR; o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_basis = mw
        o["detalhado"] = True; o["uv_proprio"] = True          # a versao VR nao refaz a UV (textura do modelo)
        o.name = "Viatura_PMERJ_" + o.name.replace("Viatura_PC_", "").replace(".", "_")
        for im in {n.image for m in o.data.materials if m and m.node_tree for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}:
            im.pack()
    for o in novos:
        if o.type != "MESH": bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    corpo = next(o for o in VTR.children if o.name.endswith("Carroceria"))
    def teto(x, ys=(0, -.25, .25, -.45, .45)):      # ponto mais alto do teto sob a base do giroflex (0,34 x 1,3 m)
        z = 0
        for y in ys:
            for dx in (-.15, 0, .15):
                ok, lc, _, _ = corpo.ray_cast(Vector((x + dx, y, 5)), Vector((0, 0, -1)))
                if ok: z = max(z, lc.z)
        return z
    x_giro = -.3                                     # meio do teto deste carro
    z_giro = teto(x_giro)
    frente = max((corpo.matrix_basis @ Vector(c)).x for c in corpo.bound_box)
    x_ant = -1.15
    mover_equipamentos(dx_giro=x_giro - (-.1), dz_giro=z_giro - 1.66, antena=(x_ant, .25, teto(x_ant, ys=(.25,)) + .22), farol_x=frente + .03)
    say("viatura pronta no lugar da viatura: %d pecas, %d triangulos, nosso giroflex a %.2f m do chao"
        % (len(malhas), sum(len(pl.vertices) - 2 for o in malhas for pl in o.data.polygons), z_giro))

if os.path.exists(MODELO_PRONTO):
    usar_viatura_pronta()
elif USAR_MODELO:
    usar_modelo_usuario()
else:
    mover_equipamentos()            # giroflex, antena e farois de volta ao lugar original

    # ------------------------------------------------------------------ limpeza (mantem giroflex, antena e luzes dos farois)
    for o in list(VTR.children_recursive):
        if not o.name.startswith(MANTER):
            bpy.data.objects.remove(o, do_unlink=True)
    for nome in ("Viatura_PMERJ_Pintura",):
        pass

    def obj(nome, me, mats, pai=VTR, suave=True):
        for p in me.polygons: p.use_smooth = suave
        for m in mats: me.materials.append(m)
        o = bpy.data.objects.new(nome, me); COL.objects.link(o); o.parent = pai
        return o

    def caixa(nome, tam, pos, m, rot=(0, 0, 0), bevel=0.0, seg=3, pai=VTR):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=Vector(tam), verts=bm.verts)
        me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
        o = obj(nome, me, [m], pai, suave=bevel > 0)
        o.location = pos; o.rotation_euler = rot
        if bevel:
            b = o.modifiers.new("Chanfro", "BEVEL"); b.width = bevel; b.segments = seg; b.limit_method = "ANGLE"
        return o

    def cilindro(nome, r1, r2, h, pos, m, rot=(0, 0, 0), seg=24, pai=VTR):
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=h)
        me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
        o = obj(nome, me, [m], pai); o.location = pos; o.rotation_euler = rot
        return o

    def torno(nome, perfil, m, pai, seg=48):
        """Solido de revolucao em torno do eixo Z local (perfil = [(raio, z), ...])."""
        bm = bmesh.new(); aneis = []
        for k in range(seg):
            a = 2 * PI * k / seg
            aneis.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in perfil])
        for k in range(seg):
            A, B = aneis[k], aneis[(k + 1) % seg]
            for i in range(len(perfil) - 1):
                try: bm.faces.new((A[i], B[i], B[i + 1], A[i + 1]))
                except ValueError: pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
        return obj(nome, me, [m], pai)

    # ------------------------------------------------------------------ carroceria (loft)
    # x, z_baixo, z_ombro (linha de cintura), z_topo (teto ou capo), meia largura, meia largura do teto (None = capo)
    EST = [
        (2.17, .45, .70, .74, .66, None), (2.13, .36, .76, .80, .78, None), (2.02, .31, .82, .86, .85, None),
        (1.75, .29, .88, .92, .89, None), (1.40, .28, .92, .96, .905, None), (1.00, .28, .97, 1.01, .91, None),
        (.72, .28, 1.00, 1.32, .91, .80), (.32, .28, 1.01, 1.62, .91, .76), (.10, .28, 1.01, 1.655, .91, .755),
        (-.12, .28, 1.01, 1.665, .91, .755), (-.28, .28, 1.01, 1.67, .91, .755), (-.70, .28, 1.015, 1.67, .91, .755),
        (-1.05, .28, 1.02, 1.665, .91, .75), (-1.25, .28, 1.02, 1.66, .91, .75), (-1.55, .29, 1.02, 1.645, .905, .74),
        (-1.80, .30, 1.02, 1.62, .90, .725), (-1.92, .31, 1.01, 1.58, .89, .71), (-2.05, .33, 1.00, 1.40, .87, .68),
        (-2.13, .36, .99, 1.10, .82, .62), (-2.17, .44, .96, 1.00, .74, .55),
    ]

    def meia_secao(e):
        x, zb, zs, zt, hw, hr = e
        p = [(0, zb), (hw * .82, zb), (hw * .97, zb + .07), (hw, zb + .22), (hw, zb + .40), (hw * .995, zs - .06), (hw * .975, zs)]
        if hr is None:   # capo: o "teto" se acomoda sobre o capo
            p += [(hw * .9, zt - .015), (hw * .75, zt), (hw * .45, zt + .01), (0, zt + .015)]
        else:
            p += [(hr + .025, zs + .04), (hr, zt - .07), (hr * .86, zt), (0, zt + .01)]
        return p

    def material_faixa(j, x0, x1):
        """Material da faixa j (entre o ponto j e j+1 da meia secao) no segmento de x0 a x1."""
        xm = (x0 + x1) / 2
        if j == 0: return 2                          # fundo
        if j in (1, 2): return 2                     # saia plastica preta
        if j == 3: return 1                          # faixa azul
        if j in (4, 5): return 0                     # porta (branco)
        if j == 6: return 0                          # ombro / capo
        para_brisa = .32 <= xm <= 1.00
        vigia = xm <= -1.92
        if j == 7:                                   # faixa das janelas laterais
            if para_brisa or vigia: return 4         # colunas A e D
            if -.12 <= xm <= .32: return 3           # vidro da porta dianteira
            if -.28 <= xm <= -.12: return 4          # coluna B
            if -1.05 <= xm <= -.28: return 3         # vidro da porta traseira
            if -1.25 <= xm <= -1.05: return 4        # coluna C
            if -1.80 <= xm <= -1.25: return 3        # vidro lateral traseiro
            return 0                                 # coluna D (cor da carroceria)
        if para_brisa or vigia: return 3             # para-brisa / vigia (faixas do teto)
        return 0                                     # teto

    bm = bmesh.new(); aneis = []
    for e in EST:
        h = meia_secao(e)
        pts = h + [(-y, z) for (y, z) in reversed(h[1:-1])]
        aneis.append([bm.verts.new((e[0], y, z)) for (y, z) in pts])
    N = len(aneis[0]); NH = len(meia_secao(EST[0])) - 1   # faixas por lado
    for i in range(len(EST) - 1):
        for k in range(N):
            k2 = (k + 1) % N
            f = bm.faces.new((aneis[i][k], aneis[i][k2], aneis[i + 1][k2], aneis[i + 1][k]))
            j = k if k < NH else (N - 1 - k)
            f.material_index = material_faixa(j, EST[i + 1][0], EST[i][0])
    for anel in (aneis[0], aneis[-1]):            # frente e traseira fechadas
        c = bm.verts.new((anel[0].co.x, 0, sum(v.co.z for v in anel) / N))
        for k in range(N):
            bm.faces.new((anel[k], anel[(k + 1) % N], c)).material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    vinco = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    for i in range(len(EST) - 1):                 # vincos: saia, faixa, ombro, soleira da janela, borda do teto
        for jj, forca in ((3, .95), (4, .95), (6, .8), (7, .85), (9, .45)):
            for k in (jj, N - jj):
                e = bm.edges.get((aneis[i][k % N], aneis[i + 1][k % N]))
                if e: e[vinco] = forca
    for i in (0, len(EST) - 1):
        for k in range(N):
            e = bm.edges.get((aneis[i][k], aneis[i][(k + 1) % N]))
            if e: e[vinco] = .7
    me = bpy.data.meshes.new("Viatura_PMERJ_Carroceria"); bm.to_mesh(me); bm.free()
    corpo = obj("Viatura_PMERJ_Carroceria", me, [M["pint"], M["faixa"], M["plast"], M["vidro"], M["preto"]])
    s = corpo.modifiers.new("Suavizar", "SUBSURF"); s.levels = 1; s.render_levels = 2
    corpo["detalhado"] = True

    # caixas de roda: corte booleano + saias plasticas
    EIXOS = (1.33, -1.34); R_RODA = .35
    bm = bmesh.new()
    for x in EIXOS:
        bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=.40, radius2=.40, depth=2.4,
                              matrix=Matrix.Translation((x, 0, R_RODA + .01)) @ Matrix.Rotation(PI / 2, 4, "X"))
    me = bpy.data.meshes.new("Viatura_PMERJ_Cortador"); bm.to_mesh(me); bm.free()
    cort = obj("Viatura_PMERJ_Cortador", me, [M["plast"]]); cort.display_type = "WIRE"; cort.hide_render = True; cort.hide_viewport = True
    b = corpo.modifiers.new("Caixas_de_Roda", "BOOLEAN"); b.object = cort; b.solver = "EXACT"
    corpo.modifiers.move(1, 0)                    # corta antes de suavizar
    for x in EIXOS:
        cilindro("Viatura_PMERJ_Forro_Caixa", .395, .395, 1.62, (x, 0, R_RODA + .01), M["plast"], rot=(PI / 2, 0, 0), seg=40)
        for lado in (1, -1):                      # alargador de para-lama (arco plastico)
            vs, fs = [], []; A, T = 28, 8
            for i in range(A + 1):
                a = math.radians(-8 + 196 * i / A)
                for jt in range(T):
                    bb = 2 * PI * jt / T; r = .425 + .03 * math.cos(bb)
                    vs.append((x + r * math.cos(a), lado * (.895 + .035 * math.sin(bb)), R_RODA + .01 + r * math.sin(a)))
            for i in range(A):
                for jt in range(T):
                    p, q = i * T + jt, i * T + (jt + 1) % T
                    fs.append((p, q, q + T, p + T))
            mm = bpy.data.meshes.new("Viatura_PMERJ_Alargador"); mm.from_pydata(vs, [], fs)
            obj("Viatura_PMERJ_Alargador", mm, [M["plast"]])

    # rodas: pneu (flanco arredondado), aro de 5 raios duplos, disco e pinca
    PNEU = [(.215, -.105), (.29, -.112), (.325, -.105), (.343, -.08), (.35, -.04), (.35, .04), (.343, .08), (.325, .105), (.29, .112), (.215, .105)]
    ARO = [(0, .085), (.06, .085), (.075, .07), (.2, .07), (.215, .095), (.217, -.09), (.2, -.095)]
    for x in EIXOS:
        for lado in (1, -1):
            g = bpy.data.objects.new("Viatura_PMERJ_Roda", None); COL.objects.link(g); g.parent = VTR
            g.location = (x, lado * .79, R_RODA); g.rotation_euler = (-lado * PI / 2, 0, 0); g.empty_display_size = .2
            torno("Viatura_PMERJ_Pneu", PNEU, M["pneu"], g, seg=48)
            torno("Viatura_PMERJ_Aro", ARO, M["aro"], g, seg=40)
            for k in range(5):
                for d in (-.022, .022):
                    a = 2 * PI * k / 5 + d * 2.2
                    caixa("Viatura_PMERJ_Raio", (.15, .022, .03), (math.cos(a) * .135, math.sin(a) * .135, .075), M["aro"], rot=(0, 0, a), pai=g)
            cilindro("Viatura_PMERJ_Cubo", .05, .05, .03, (0, 0, .09), M["cromo"], seg=20, pai=g)
            cilindro("Viatura_PMERJ_Disco", .16, .16, .022, (0, 0, -.02), M["disco"], seg=32, pai=g)
            caixa("Viatura_PMERJ_Pinca", (.07, .1, .05), (.11, .11, -.01), M["preto"], rot=(0, 0, .8), bevel=.01, pai=g)

    # ------------------------------------------------------------------ superficie da carroceria (para colar pecas)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); ev = corpo.evaluated_get(dg)
    def sup_y(x, z, lado):
        ok, lc, _, _ = ev.ray_cast(Vector((x, lado * 2.0, z)), Vector((0, -lado, 0)))
        return lc.y if ok else lado * .9
    def sup_x(y, z, ponta):
        ok, lc, _, _ = ev.ray_cast(Vector((ponta * 3.0, y, z)), Vector((-ponta, 0, 0)))
        return lc.x if ok else ponta * 2.17

    # para-choques moldados (caixa chanfrada larga) e grade
    caixa("Viatura_PMERJ_Parachoque_Diant", (.24, 1.78, .3), (2.1, 0, .47), M["plast"], bevel=.09, seg=4)
    caixa("Viatura_PMERJ_Protetor_Carter", (.07, .9, .12), (2.21, 0, .34), M["prata"], rot=(0, .35, 0), bevel=.03, seg=2)
    caixa("Viatura_PMERJ_Grade", (.06, 1.02, .2), (2.16, 0, .66), M["preto"], bevel=.04, seg=3)
    for z in (.62, .7):
        caixa("Viatura_PMERJ_Grade_Friso", (.065, .98, .018), (2.17, 0, z), M["cromo"], bevel=.006, seg=2)
    caixa("Viatura_PMERJ_Parachoque_Tras", (.24, 1.76, .3), (-2.12, 0, .5), M["plast"], bevel=.09, seg=4)
    for lado in (1, -1):
        # farois envolventes (seguem a quina dianteira) + DRL
        xf = sup_x(lado * .6, .74, 1)
        caixa("Viatura_PMERJ_Farol", (.1, .36, .13), (xf - .02, lado * .58, .75), M["farol"], rot=(0, 0, -lado * .25), bevel=.035, seg=3)
        caixa("Viatura_PMERJ_DRL", (.04, .3, .018), (xf + .005, lado * .6, .685), M["drl"], rot=(0, 0, -lado * .25), bevel=.006, seg=2)
        cilindro("Viatura_PMERJ_Farol_Milha", .045, .045, .03, (2.22, lado * .66, .42), M["farol"], rot=(0, PI / 2, 0), seg=20)
        # lanternas traseiras verticais nas quinas
        xt = sup_x(lado * .72, .85, -1)
        caixa("Viatura_PMERJ_Lanterna", (.07, .16, .32), (xt + .015, lado * .7, .86), M["lanterna"], rot=(0, 0, lado * .3), bevel=.025, seg=3)
        caixa("Viatura_PMERJ_Refletor", (.02, .1, .03), (-2.235, lado * .72, .5), M["refletor"], bevel=.005, seg=2)
        # retrovisores arredondados
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=.1)
        bmesh.ops.scale(bm, vec=Vector((.9, 1.3, .75)), verts=bm.verts)
        mm = bpy.data.meshes.new("Viatura_PMERJ_Retrovisor"); bm.to_mesh(mm); bm.free()
        rv = obj("Viatura_PMERJ_Retrovisor", mm, [M["pint"]]); rv.location = (.62, lado * 1.0, 1.1)
        caixa("Viatura_PMERJ_Retrovisor_Base", (.12, .14, .05), (.66, lado * .9, 1.05), M["plast"], bevel=.015, seg=2)
        caixa("Viatura_PMERJ_Retrovisor_Espelho", (.005, .17, .1), (.53, lado * 1.02, 1.1), M["cromo"], bevel=.01, seg=2)
        # frisos das portas e macanetas
        for xl in (.96, -.2, -1.18):
            y = sup_y(xl, .72, lado)
            caixa("Viatura_PMERJ_Friso_Porta", (.006, .006, .66), (xl, y + lado * .001, .7), M["preto"])
        for xh in (.12, -.95):
            y = sup_y(xh, .93, lado)
            caixa("Viatura_PMERJ_Macaneta", (.14, .03, .035), (xh, y + lado * .012, .93), M["plast"], bevel=.01, seg=2)
        # rack de teto com apoios
        caixa("Viatura_PMERJ_Rack_Teto", (1.85, .035, .025), (-.6, lado * .62, 1.72), M["preto"], bevel=.01, seg=2)
        for xp in (.25, -1.45):
            caixa("Viatura_PMERJ_Rack_Apoio", (.08, .04, .06), (xp, lado * .62, 1.69), M["preto"], bevel=.01, seg=2)
    # limpadores
    for sy in (-.36, .3):
        caixa("Viatura_PMERJ_Limpador", (.02, .58, .015), (.98, sy, 1.04), M["preto"], rot=(0, -.75, .1))
    # interior visivel pelos vidros: painel, bancos, volante
    caixa("Viatura_PMERJ_Painel", (.35, 1.6, .25), (.75, 0, .98), M["interior"], bevel=.05, seg=2)
    for sx in (-1, 1):
        caixa("Viatura_PMERJ_Banco", (.5, .5, .1), (-.05, sx * .38, .62), M["interior"], bevel=.04, seg=2)
        caixa("Viatura_PMERJ_Encosto", (.12, .48, .6), (-.33, sx * .38, .95), M["interior"], rot=(0, .2, 0), bevel=.04, seg=2)
    caixa("Viatura_PMERJ_Banco_Tras", (.5, 1.4, .1), (-1.1, 0, .64), M["interior"], bevel=.04, seg=2)
    cilindro("Viatura_PMERJ_Volante", .19, .19, .03, (.5, -.38, 1.06), M["preto"], rot=(0, -1.15, 0), seg=24)

    # placas Mercosul
    def texto(nome, conteudo, tam, pos, rot, m, pai=VTR):
        cu = bpy.data.curves.new(nome, "FONT"); cu.body = conteudo; cu.size = tam; cu.align_x = "CENTER"; cu.align_y = "CENTER"
        cu.resolution_u = 2                     # letras chapadas e leves (sao adesivos)
        tmp = bpy.data.objects.new(nome + "_tmp", cu); COL.objects.link(tmp)
        bpy.context.view_layer.update()
        mm = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.curves.remove(cu)
        o = obj(nome, mm, [m], pai, suave=False); o.location = pos; o.rotation_euler = rot
        return o
    for ponta, x0, z0 in ((1, 2.23, .47), (-1, sup_x(0, .62, -1) - .015, .62)):
        caixa("Viatura_PMERJ_Placa", (.01, .4, .13), (x0, 0, z0), M["placa"])
        caixa("Viatura_PMERJ_Placa_Faixa", (.012, .4, .03), (x0 + ponta * .001, 0, z0 + .05), M["placa_azul"])
        texto("Viatura_PMERJ_Placa_Texto", "RJP0M19", .065, (x0 + ponta * .007, 0, z0 - .012), (PI / 2, 0, ponta * PI / 2), M["placa_txt"])

    # padrao de pintura PMERJ (aproximado; confira com fotos atuais): textos e espaco do brasao
    for lado in (1, -1):
        rot = (PI / 2, 0, PI) if lado > 0 else (PI / 2, 0, 0)
        texto("Adesivo_Policia_Militar", "POLÍCIA\nMILITAR", .1, (-.62, sup_y(-.62, .8, lado) + lado * .004, .8), rot, M["texto"])
        texto("Adesivo_190", "190", .13, (-1.62, sup_y(-1.62, .9, lado) + lado * .004, .9), rot, M["texto"])   # acima da caixa de roda
        texto("Adesivo_PMERJ", "PMERJ", .07, (1.6, sup_y(1.6, .78, lado) + lado * .004, .78), rot, M["texto"])
        y = sup_y(.42, .78, lado)
        cilindro("Brasao_Moldura", .115, .115, .004, (.42, y + lado * .003, .78), M["dourado"], rot=(PI / 2, 0, 0), seg=40)
        cilindro("Brasao_Imagem", .1, .1, .004, (.42, y + lado * .005, .78), M["brasao"], rot=(PI / 2, 0, 0), seg=40)
    xr = sup_x(0, .92, -1)
    texto("Adesivo_Traseira", "POLÍCIA MILITAR · 190", .07, (xr - .004, 0, .9), (PI / 2, 0, -PI / 2), M["texto"])

    # luzes dos farois acompanham os farois novos
    for o in VTR.children:
        if o.name.startswith("Viatura_PMERJ_Farol_Luz"):
            o.location.x = 2.24
    for o in VTR.children_recursive:
        o["detalhado"] = True                     # suavizar_objetos.py nao mexe


# ------------------------------------------------------------------ carros dos moradores: menos poligonos
removidos = 0
for nome in ("Vizinho_Esq_Carro", "Vizinho_A_Carro", "Vizinho_C_Carro"):    # garagens dos vizinhos ficam vazias
    carro = bpy.data.objects.get(nome)
    if carro:
        for o in list(carro.children_recursive) + [carro]:
            bpy.data.objects.remove(o, do_unlink=True)
        removidos += 1
for nome in ("Carro_Rua_Vermelho",):
    c = bpy.data.objects.get(nome)
    if not c: continue
    for o in c.children_recursive:
        if o.type != "MESH": continue
        sub = next((m for m in o.modifiers if m.type == "SUBSURF"), None)
        if sub: sub.levels = 1                # de longe a carroceria nao precisa de 2 niveis
        if o.name.endswith(("_Pneu", "_Aro", "_Arco_Roda")) or "_Pneu." in o.name or "_Aro." in o.name or "_Arco_Roda." in o.name:
            if not any(m.type == "DECIMATE" for m in o.modifiers):
                d = o.modifiers.new("Simplificar", "DECIMATE"); d.ratio = .35
dg = bpy.context.evaluated_depsgraph_get()
def tris(raiz):
    t = 0
    for o in [raiz] + list(raiz.children_recursive):
        if o.type != "MESH" or o.hide_render: continue
        e = o.evaluated_get(dg); m = e.to_mesh(); t += sum(len(p.vertices) - 2 for p in m.polygons); e.to_mesh_clear()
    return t
say("viatura (%s): ~%d triangulos" % ("viatura_pronta.glb" if os.path.exists(MODELO_PRONTO) else "modelo do usuario" if USAR_MODELO else "procedural", tris(VTR)))
say("carros de moradores: %d removidos das garagens; restantes: %s" % (removidos, ", ".join(
    "%s ~%d" % (n, tris(bpy.data.objects[n])) for n in ("Carro_Rua_Vermelho", "Vizinho_A_Carro", "Vizinho_C_Carro") if bpy.data.objects.get(n))))
bpy.ops.wm.save_mainfile()
