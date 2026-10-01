"""
A Casa em Silencio - arbustos com folhas de verdade (substitui as "bolotas" de esfera deformada).

Cada arbusto vira: um miolo escuro (da volume e esconde o que esta atras) + dezenas de cartoes com raminhos
de folhas (textura gerada aqui, com transparencia recortada - funciona no Cycles, no Unity/Unreal e no three.js).
Idempotente: na 1a vez guarda o tamanho original de cada arbusto (props arb_*) e depois sempre reconstroi a partir dele.

Uso:  blender -b casa_em_silencio.blend --python arbustos.py
"""
import bpy, bmesh, math, random, zlib
import numpy as np
from mathutils import Vector, Matrix, noise

def say(m):
    print("[ARBUSTO] " + m)

# ------------------------------------------------------------------ textura: 4 raminhos (atlas 2x2)
def textura_raminhos(S=1024, semente=7):
    rnd = np.random.default_rng(semente)
    img = np.zeros((S, S, 4), np.float32)
    C = S // 2
    yy, xx = np.mgrid[0:C, 0:C].astype(np.float32)
    verdes = np.array([[38, 78, 30], [52, 96, 34], [70, 112, 40], [44, 88, 42], [86, 128, 48]], np.float32) / 255
    for cel in range(4):
        cx0, cy0 = (cel % 2) * C, (cel // 2) * C
        cor = np.zeros((C, C, 3), np.float32); alfa = np.zeros((C, C), np.float32)
        # galhos: 2 ou 3 hastes saindo da base, levemente curvas
        for h in range(rnd.integers(2, 4)):
            ang0 = rnd.uniform(-.45, .45); curva = rnd.uniform(-.5, .5)
            px, py = C / 2 + rnd.uniform(-20, 20), C - 4.0
            comp = rnd.uniform(.75, .95) * C
            pts = []
            for k in range(60):
                t = k / 59; a = ang0 + curva * t
                px += math.sin(a) * comp / 60; py -= math.cos(a) * comp / 60
                pts.append((px, py, a, t))
            for (px_, py_, a, t) in pts:          # haste fina
                d = np.hypot(xx - px_, yy - py_) < 2.2 - 1.2 * t
                cor[d] = (.20, .24, .10); alfa[d] = 1
            # folhas alternadas ao longo da haste (menores na ponta)
            for k in range(rnd.integers(9, 14)):
                t = .12 + .88 * k / 13
                px_, py_, a, _ = pts[min(59, int(t * 59))]
                lado = 1 if k % 2 else -1
                ang = a + lado * rnd.uniform(.55, 1.05)
                L = rnd.uniform(.17, .24) * C * (1.15 - .45 * t); W = L * rnd.uniform(.36, .48)
                ux, uy = math.sin(ang), -math.cos(ang)            # eixo da folha (da base para a ponta)
                dx, dy = xx - px_, yy - py_
                u = dx * ux + dy * uy; v = -dx * uy + dy * ux
                s = np.clip(u / L, 0, 1)
                larg = W / 2 * np.power(np.sin(np.pi * np.clip(s * .92 + .04, 0, 1)), .75)
                dentro = (u > 0) & (u < L) & (np.abs(v) < larg)
                base = verdes[rnd.integers(len(verdes))] * rnd.uniform(.85, 1.1)
                tom = base * (.78 + .32 * s[..., None]) * (1 - .25 * (np.abs(v) / (larg + 1e-3))[..., None])
                nerv = dentro & (np.abs(v) < 1.3)
                tom = np.where(nerv[..., None], base * 1.35, tom)
                cor[dentro] = tom[dentro]; alfa[dentro] = 1
        cor *= (1 + .08 * rnd.standard_normal((C, C, 1))).astype(np.float32)
        img[cy0:cy0 + C, cx0:cx0 + C, :3] = np.clip(cor, 0, 1); img[cy0:cy0 + C, cx0:cx0 + C, 3] = alfa
    # "sangra" a cor para os pixels transparentes vizinhos (evita borda escura no mipmap)
    for _ in range(4):
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
    m = bpy.data.materials.get("Folha_Arbusto") or bpy.data.materials.new("Folha_Arbusto")
    nt = m.node_tree; nt.nodes.clear()        # Blender 5: material sempre tem nos
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = imagem("textura_raminhos", textura_raminhos())
    r = nt.nodes.new("ShaderNodeMath"); r.operation = "ROUND"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = .55
    nt.links.new(b.outputs[0], out.inputs[0])
    for attr, val in (("surface_render_method", "DITHERED"), ("blend_method", "CLIP")):
        try: setattr(m, attr, val)
        except Exception: pass
    m.use_backface_culling = False
    return m

def material_miolo():
    m = bpy.data.materials.get("Arbusto_Miolo") or bpy.data.materials.new("Arbusto_Miolo")
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (.018, .045, .014, 1); b.inputs["Roughness"].default_value = .9
    return m

# ------------------------------------------------------------------ geometria
def construir(ob, m_folha, m_miolo):
    if "arb_r" not in ob:                         # 1a vez: guarda o tamanho da bolota original
        dg = bpy.context.evaluated_depsgraph_get(); e = ob.evaluated_get(dg)
        bb = [Vector(c) for c in e.bound_box]
        sc = ob.scale.copy()
        mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        c = (mn + mx) / 2
        ob["arb_c"] = [c.x * sc.x, c.y * sc.y, c.z * sc.z]
        ob["arb_r"] = [(mx.x - mn.x) / 2 * sc.x, (mx.y - mn.y) / 2 * sc.y, (mx.z - mn.z) / 2 * sc.z]
    c, r = Vector(ob["arb_c"]), Vector(ob["arb_r"])
    rnd = random.Random(zlib.crc32(ob.name.encode()))
    for md in list(ob.modifiers): ob.modifiers.remove(md)
    ob.scale = (1, 1, 1)
    mw = ob.matrix_world.copy()
    chao = 0.0
    bm = bmesh.new()
    # miolo: elipsoide irregular, 82% do tamanho
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
    sem = Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), rnd.uniform(0, 50)))
    for v in bm.verts:
        n = v.co.normalized()
        k = .82 * (1 + .18 * noise.noise(n * 2.2 + sem))
        v.co = Vector((n.x * r.x * k, n.y * r.y * k, n.z * r.z * k)) + c
    for f in bm.faces: f.material_index = 1; f.smooth = True
    # cartoes de folhas espalhados na superficie
    area = 4 * math.pi * ((r.x * r.y) ** 1.6 + (r.x * r.z) ** 1.6 + (r.y * r.z) ** 1.6) ** (1 / 1.6) / 3 ** (1 / 1.6)
    n_cart = int(min(240, max(40, area * 58)))
    esc = max(.75, min(1.15, (r.x + r.y) / 2 / .55))
    uvl = bm.loops.layers.uv.verify()
    feitos = 0; tent = 0
    while feitos < n_cart and tent < n_cart * 4:
        tent += 1
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), abs(rnd.gauss(0, 1)) * 1.3 - .25)).normalized()
        p = Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * rnd.uniform(.80, 1.0) + c
        if (mw @ p).z < chao + .05: continue
        nrm = Vector((d.x / r.x, d.y / r.y, d.z / r.z)).normalized()
        tam = rnd.uniform(.30, .46) * esc
        # o raminho cresce para fora/para cima: eixo "v" do cartao entre a normal e o vertical
        cima = (nrm * .55 + Vector((0, 0, 1)) * .45 + Vector((rnd.uniform(-.4, .4), rnd.uniform(-.4, .4), 0))).normalized()
        lado = cima.cross(nrm)
        if lado.length < 1e-3: lado = Vector((1, 0, 0))
        lado.normalize()
        lado = Matrix.Rotation(rnd.uniform(-.6, .6), 3, cima) @ lado
        base = p - cima * tam * .25
        cel = rnd.randrange(4); u0, v0 = (cel % 2) * .5, 1 - (cel // 2 + 1) * .5
        cantos = [base - lado * tam / 2, base + lado * tam / 2, base + lado * tam / 2 + cima * tam, base - lado * tam / 2 + cima * tam]
        vs = [bm.verts.new(q) for q in cantos]
        f = bm.faces.new(vs); f.material_index = 0; f.smooth = False
        for lp, (uu, vv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            lp[uvl].uv = (u0 + .005 + uu * .49, v0 + .005 + vv * .49)
        feitos += 1
    me = ob.data
    bm.to_mesh(me); bm.free(); me.update()
    me.materials.clear(); me.materials.append(m_folha); me.materials.append(m_miolo)
    ob["arbusto_v2"] = True; ob["detalhado"] = True      # suavizar_objetos.py nao subdivide
    return feitos

m_folha, m_miolo = material_folha(), material_miolo()
alvos = [o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith("Arbusto") or "_Arbusto" in o.name)]
total = 0
for o in alvos:
    if o.data.users > 1: o.data = o.data.copy()
    total += construir(o, m_folha, m_miolo)
say("%d arbustos refeitos com %d cartoes de folhas (~%d triangulos)" % (len(alvos), total, total * 2 + len(alvos) * 320))
bpy.ops.wm.save_mainfile()
