"""
A Casa em Silencio - copas de palmeira realistas (jeriva, comum nos condominios do Rio).

Substitui as folhas antigas (fitas lisas; nas palmeiras do jardim a copa estava virada para cima, em volta do tronco)
por ~18 folhas que saem do topo do tronco e arqueiam com o peso. Cada folha e uma fita dobrada em V com
textura de foliolos (transparencia recortada), mais uma segunda fita girada para dar volume ("plumosa").
Idempotente: apaga <palmeira>_Folhas / <palmeira>_Copa e refaz a partir do topo do tronco.

Uso:  blender -b casa_em_silencio.blend --python palmeiras.py
"""
import bpy, bmesh, math, random, zlib
import numpy as np
from mathutils import Vector, Matrix

def say(m):
    print("[PALMEIRA] " + m)

# ------------------------------------------------------------------ textura: folha pinada vista de frente (atlas 2x1)
def textura_folha(W=1024, H=1024, semente=11):
    rnd = np.random.default_rng(semente)
    img = np.zeros((H, W, 4), np.float32)
    C = W // 2
    yy, xx = np.mgrid[0:H, 0:C].astype(np.float32)
    for cel in range(2):
        cor = np.zeros((H, C, 3), np.float32); alfa = np.zeros((H, C), np.float32)
        cx = C / 2
        # raque (nervura central), da base (v=0, embaixo da imagem) ate a ponta
        d = np.abs(xx - cx) < np.interp(yy, [0, H], [1.2, 3.2])
        cor[d] = (.42, .40, .18); alfa[d] = 1
        n = 54
        for k in range(n):
            t = (k + .5) / n                                    # 0 = ponta (topo da imagem), 1 = base
            y0 = 8 + t * (H - 20)
            for lado in (-1, 1):
                if rnd.random() < .06: continue                 # falhas naturais
                L = C * .47 * math.sin(math.pi * min(1, .12 + t * .95)) * rnd.uniform(.85, 1.08)
                ang = math.radians(rnd.uniform(50, 64))          # foliolo inclinado para a ponta
                ux, uy = lado * math.sin(ang), -math.cos(ang)
                ux2, uy2 = ux, uy + .35                          # pende levemente
                nn = math.hypot(ux2, uy2); ux2, uy2 = ux2 / nn, uy2 / nn
                dx, dy = xx - cx, yy - y0
                u = dx * ux2 + dy * uy2; v = -dx * uy2 + dy * ux2
                s = np.clip(u / max(L, 1), 0, 1)
                larg = 5.4 * np.sin(np.pi * np.clip(s * .95 + .03, 0, 1)) ** .6 + .6
                dentro = (u > 0) & (u < L) & (np.abs(v) < larg)
                base = np.array([.16, .33, .11]) * rnd.uniform(.85, 1.15) + np.array([.04, .05, .0]) * t
                tom = base * (.75 + .4 * (1 - s))[..., None] * (1 - .25 * (np.abs(v) / (larg + 1e-3)))[..., None]
                cor[dentro] = tom[dentro]; alfa[dentro] = 1
        cor *= (1 + .07 * rnd.standard_normal((H, C, 1))).astype(np.float32)
        img[:, cel * C:(cel + 1) * C, :3] = np.clip(cor, 0, 1); img[:, cel * C:(cel + 1) * C, 3] = alfa
    for _ in range(4):                                          # sangra a cor para a borda transparente (mipmap)
        vaz = img[..., 3] == 0
        viz = np.maximum.reduce([np.roll(img[..., :3], s, ax) for s in (1, -1) for ax in (0, 1)])
        img[..., :3] = np.where(vaz[..., None], viz, img[..., :3])
    return img

def imagem(nome, arr):
    img = bpy.data.images.get(nome)
    if img: bpy.data.images.remove(img)
    h, w, _ = arr.shape
    img = bpy.data.images.new(nome, w, h, alpha=True)
    img.pixels.foreach_set(np.flipud(arr).ravel()); img.pack()
    return img

def material_folha():
    m = bpy.data.materials.get("Folha_Palmeira") or bpy.data.materials.new("Folha_Palmeira")
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = imagem("textura_folha_palmeira", textura_folha())
    r = nt.nodes.new("ShaderNodeMath"); r.operation = "ROUND"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = .5
    nt.links.new(b.outputs[0], out.inputs[0])
    for attr, val in (("surface_render_method", "DITHERED"), ("blend_method", "CLIP")):
        try: setattr(m, attr, val)
        except Exception: pass
    m.use_backface_culling = False
    return m

# ------------------------------------------------------------------ geometria da copa
def copa(nome, topo, raio_tronco, rnd, m_folha, colecao, pai):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.verify()
    n_folhas = 18
    for k in range(n_folhas):
        idade = k / (n_folhas - 1)                               # 0 = folha nova (em pe), 1 = velha (caida)
        az = k * 2.39996 + rnd.uniform(-.2, .2)                  # angulo de ouro: distribui em volta
        theta = math.radians(18 + idade * 62 + rnd.uniform(-6, 6))   # inclinacao a partir da vertical
        L = rnd.uniform(2.3, 3.0) * (.85 + .15 * (1 - abs(idade - .55)))
        g = .55 + idade * 1.5                                    # quanto o peso puxa para baixo
        d = Vector((math.cos(az) * math.sin(theta), math.sin(az) * math.sin(theta), math.cos(theta)))
        p = topo + Vector((math.cos(az), math.sin(az), 0)) * raio_tronco * .6
        N = 11; passo = L / N
        pts, tans = [p.copy()], []
        for i in range(N):
            d = (d - Vector((0, 0, g * passo * .55))).normalized()
            p = p + d * passo; pts.append(p.copy()); tans.append(d.copy())
        tans.append(tans[-1])
        celula = rnd.randrange(2); u0 = celula * .5
        for faixa, giro in ((0, 0.0), (1, math.radians(rnd.choice((-1, 1)) * rnd.uniform(55, 70)))):
            largura_max = rnd.uniform(.95, 1.15) * (1 if faixa == 0 else .8)
            dobra = math.radians(rnd.uniform(22, 34))            # asas caidas (V)
            linhas = []
            for i, (pt, tg) in enumerate(zip(pts, tans)):
                tv = i / N
                w = largura_max * math.sin(math.pi * min(1, .1 + tv * .98)) ** .7 * .5 + .04
                lado = tg.cross(Vector((0, 0, 1)))
                if lado.length < 1e-4: lado = Vector((1, 0, 0))
                lado.normalize()
                lado = Matrix.Rotation(giro, 3, tg) @ lado
                baixo = tg.cross(lado).normalized()
                if baixo.z > 0: baixo = -baixo
                asaE = (-lado * math.cos(dobra) + baixo * math.sin(dobra)) * w
                asaD = (lado * math.cos(dobra) + baixo * math.sin(dobra)) * w
                linhas.append([bm.verts.new(pt + asaE), bm.verts.new(pt), bm.verts.new(pt + asaD)])
            for i in range(N):
                for j in range(2):
                    f = bm.faces.new((linhas[i][j], linhas[i][j + 1], linhas[i + 1][j + 1], linhas[i + 1][j]))
                    for lp, (uu, vv) in zip(f.loops, ((j * .5, i / N), ((j + 1) * .5, i / N), ((j + 1) * .5, (i + 1) / N), (j * .5, (i + 1) / N))):
                        lp[uvl].uv = (u0 + .004 + uu * .492, .004 + vv * .992)   # v=0 na base da folha (embaixo da textura)
    # base da copa: bainhas das folhas (um bulbo curto em volta do topo do tronco)
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me); bm.free()
    for poly in me.polygons: poly.use_smooth = True
    me.materials.append(m_folha)
    ob = bpy.data.objects.new(nome, me); colecao.objects.link(ob)
    if pai:
        ob.parent = pai; ob.matrix_parent_inverse = pai.matrix_world.inverted()
    ob["detalhado"] = True; ob["palmeira_v2"] = True
    return ob, len(me.polygons) * 2

m_folha = material_folha()
grupos = [o for o in bpy.data.objects if o.type == "EMPTY" and bpy.data.objects.get(o.name + "_Tronco")]
tris = 0
for g in grupos:
    for suf in ("_Folhas", "_Copa"):
        velho = bpy.data.objects.get(g.name + suf)
        if velho: bpy.data.objects.remove(velho, do_unlink=True)
    tronco = bpy.data.objects[g.name + "_Tronco"]
    palmito = bpy.data.objects.get(g.name + "_Palmito")
    ref = palmito or tronco
    bb = [ref.matrix_world @ Vector(c) for c in ref.bound_box]
    topo = Vector((sum(v.x for v in bb) / 8, sum(v.y for v in bb) / 8, max(v.z for v in bb) - .05))
    rt = max(tronco.dimensions.x, tronco.dimensions.y) / 2
    rnd = random.Random(zlib.crc32(g.name.encode()))
    _, t = copa(g.name + "_Copa", topo, rt, rnd, m_folha, tronco.users_collection[0], g)
    tris += t
say("%d palmeiras com copa nova (18 folhas cada, ~%d triangulos no total)" % (len(grupos), tris))
bpy.ops.wm.save_mainfile()
