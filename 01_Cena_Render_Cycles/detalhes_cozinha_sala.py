"""
A Casa em Silencio - detalhamento: geladeira retro, filtro de barro, liquido derramado e costela-de-adao.

- Geladeira retro (anos 60): corpo com cantos arredondados, porta separada com friso, puxador cromado com
  suportes, frisos cromados, grade de ventilacao e pes. Vira um Empty "Geladeira" com as pecas (substituivel).
- Filtro de barro: frisos, anel de juncao, torneirinha cromada com alavanca, barro com variacao e relevo.
- Liquido derramado: poca irregular saindo da boca do copo, borda arredondada, escorrendo pela beira
  da mesa, gotas e pocinha no chao.
- Costela-de-adao: folhas em coracao com os recortes tipicos, dobradas na nervura e caidas na ponta,
  caules curvos saindo da terra.

Nao mexe em objetos vindos de modelos feitos a mao (propriedade "modelo_usuario"). Pode rodar de novo.
Uso:  blender -b casa_em_silencio.blend --python detalhes_cozinha_sala.py
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

PI = math.pi
rr = random.Random(77)

def lin(h):
    c = tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def mat(nome, cor, rough=.5, metal=0., transm=0., alpha=1.):
    m = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*lin(cor), 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Alpha"].default_value = alpha
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transm
    if alpha < 1:
        for a, v in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try: setattr(m, a, v)
            except Exception: pass
    m.diffuse_color = (*lin(cor), alpha)
    return m

def colecao(nome):
    return bpy.data.collections.get(nome) or bpy.context.scene.collection

def novo(nome, me, col, pai=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    o = bpy.data.objects.new(nome, me); col.objects.link(o)
    o.parent = pai; o.location = loc; o.rotation_euler = rot; o["detalhado"] = True
    return o

def vazio(nome, col, loc):
    e = bpy.data.objects.new(nome, None); col.objects.link(e); e.location = loc; e["detalhado"] = True
    return e

def caixa(nome, sx, sy, sz, col, pai, loc, material, chanfro=0., seg=3, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free(); me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    o = novo(nome, me, col, pai, loc, rot)
    if chanfro:
        bv = o.modifiers.new("MM_Bevel", "BEVEL"); bv.width = chanfro; bv.segments = seg; bv.limit_method = "ANGLE"
        bv.harden_normals = True
    return o

def cilindro(nome, r, h, col, pai, loc, material, rot=(0, 0, 0), seg=24, r2=None):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free(); me.materials.append(material)
    for p in me.polygons: p.use_smooth = True
    try: me.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    return novo(nome, me, col, pai, loc, rot)

def apagar(nome_ou_ob):
    ob = bpy.data.objects.get(nome_ou_ob) if isinstance(nome_ou_ob, str) else nome_ou_ob
    if not ob:
        return
    for c in list(ob.children):
        apagar(c)
    bpy.data.objects.remove(ob, do_unlink=True)

def protegido(nome):
    o = bpy.data.objects.get(nome)
    return bool(o and o.get("modelo_usuario"))

feito = []

# =============================================================== GELADEIRA RETRO
if not protegido("Geladeira"):
    COZ = colecao("04_Cozinha")
    cor = bpy.data.materials.get("Geladeira_Verde") or mat("Geladeira_Verde", "#8fbfab", .35)
    b = cor.node_tree.nodes.get("Principled BSDF")
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = .8; b.inputs["Coat Roughness"].default_value = .06
    cromo = bpy.data.materials.get("Cromado") or mat("Cromado", "#d0d2d4", .08, 1.)
    grade = mat("Geladeira_Grade", "#1c1d1f", .5, .3)
    borracha = mat("Geladeira_Borracha", "#202020", .7)
    apagar("Geladeira"); apagar("Geladeira_Puxador")
    g = vazio("Geladeira", COZ, (5.6, -2.4, 0.0))
    # corpo (frente da porta em x=5.25; fundo encostado na parede)
    caixa("Geladeira_Corpo", .66, .70, 1.70, COZ, g, (.04, 0, .93), cor, chanfro=.075, seg=6)
    caixa("Geladeira_Porta", .035, .66, 1.48, COZ, g, (-.3325, 0, 1.0), cor, chanfro=.022, seg=4)
    caixa("Geladeira_Vedacao", .01, .67, 1.50, COZ, g, (-.312, 0, 1.0), borracha, chanfro=.004)
    caixa("Geladeira_Friso_Alto", .012, .62, .018, COZ, g, (-.352, 0, 1.66), cromo, chanfro=.006)
    caixa("Geladeira_Friso_Baixo", .012, .62, .018, COZ, g, (-.352, 0, .34), cromo, chanfro=.006)
    # puxador cromado vertical com dois suportes (lado da dobradica oposto)
    for z in (.98, 1.42):
        caixa("Geladeira_Puxador_Suporte", .05, .022, .028, COZ, g, (-.372, .27, z), cromo, chanfro=.008)
    cilindro("Geladeira_Puxador", .011, .5, COZ, g, (-.405, .27, 1.2), cromo, seg=20)
    # dobradicas
    for z in (.27, 1.73):
        caixa("Geladeira_Dobradica", .05, .03, .04, COZ, g, (-.33, -.335, z), cromo, chanfro=.008)
    # base: grade de ventilacao e pes
    caixa("Geladeira_Base", .03, .62, .17, COZ, g, (-.32, 0, .155), grade, chanfro=.01)
    for k in range(7):
        caixa("Geladeira_Grade_Friso", .006, .56, .008, COZ, g, (-.338, 0, .09 + k * .022), cromo)
    for dx in (-.26, .3):
        for dy in (-.3, .3):
            cilindro("Geladeira_Pe", .02, .07, COZ, g, (dx, dy, .035), borracha, seg=16)
    feito.append("geladeira retro")

# =============================================================== FILTRO DE BARRO
fil = bpy.data.objects.get("Filtro_de_Barro")
if fil and not fil.get("modelo_usuario"):
    COZ = fil.users_collection[0]
    ter = bpy.data.materials.get("Terracota")
    if ter:   # variacao de cor e relevo do barro (Cycles); nas versoes VR/web vira cor lisa
        nt = ter.node_tree; b = nt.nodes.get("Principled BSDF")
        if not nt.nodes.get("Barro_Ruido"):
            tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise"); nz.name = "Barro_Ruido"
            nz.inputs["Scale"].default_value = 35; nz.inputs["Detail"].default_value = 8
            rp = nt.nodes.new("ShaderNodeValToRGB"); e = rp.color_ramp.elements
            e[0].color = (*lin("#8e4326"), 1); e[1].color = (*lin("#b45f3a"), 1)
            bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .25
            nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
            nt.links.new(rp.outputs["Color"], b.inputs["Base Color"]); nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
            nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    junta = mat("Barro_Escuro", "#7a3a22", .85)
    cromo = bpy.data.materials.get("Cromado") or mat("Cromado", "#d0d2d4", .08, 1.)
    for c in list(fil.children):
        apagar(c)
    apagar("Filtro_Torneirinha")
    # anel de juncao entre o reservatorio e a vela (z ~0,30 do perfil) e frisos decorativos
    def anel(nome, r, z, esp, material):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=56, radius1=r, radius2=r, depth=esp)
        me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free(); me.materials.append(material)
        for p in me.polygons: p.use_smooth = True
        o = novo(nome, me, COZ, fil, (0, 0, z))
        so = o.modifiers.new("Espessura", "SOLIDIFY"); so.thickness = .006
        return o
    anel("Filtro_Anel_Juncao", .141, .303, .016, junta)
    for z, r in ((.12, .1535), (.165, .159), (.42, .1615), (.47, .159)):
        anel("Filtro_Friso", r + .002, z, .006, junta)
    # torneirinha cromada (aponta para a frente da bancada, -Y)
    tg = vazio("Filtro_Torneira", COZ, (0, 0, 0)); tg.parent = fil; tg.location = (0, -.148, .07)
    cilindro("Filtro_Torneira_Rosca", .016, .02, COZ, tg, (0, .004, 0), cromo, rot=(PI / 2, 0, 0), seg=20)
    cilindro("Filtro_Torneira_Corpo", .011, .05, COZ, tg, (0, -.024, 0), cromo, rot=(PI / 2, 0, 0), seg=20)
    cilindro("Filtro_Torneira_Bico", .0075, .03, COZ, tg, (0, -.046, -.015), cromo, seg=16, r2=.006)
    cilindro("Filtro_Torneira_Eixo", .005, .018, COZ, tg, (0, -.026, .016), cromo, seg=12)
    caixa("Filtro_Torneira_Alavanca", .05, .009, .006, COZ, tg, (.018, -.026, .026), cromo, chanfro=.002)
    feito.append("filtro de barro")

# =============================================================== LIQUIDO DERRAMADO
if not protegido("V_Bebida_Derramada"):
    VEST = colecao("08_Vestigios")
    liq = bpy.data.materials.get("Liquido_Derramado") or mat("Liquido_Derramado", "#6a3e14", .02, alpha=.75)
    b = liq.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*lin("#8a5a14"), 1); b.inputs["Roughness"].default_value = .01
    b.inputs["Alpha"].default_value = .6
    if "Transmission Weight" in b.inputs: b.inputs["Transmission Weight"].default_value = .7
    for n in ("V_Bebida_Derramada", "V_Bebida_Escorrida", "V_Bebida_Chao"):
        apagar(n)
    for o in [o for o in bpy.data.objects if o.name.startswith("V_Bebida_Gota")]:
        apagar(o)

    def poca(nome, centro, rx, ry, pontas, seed, altura=.0016, cor=liq):
        """Poca irregular: contorno com ruido + 'linguas' na direcao das pontas; borda arredondada."""
        r2 = random.Random(seed); N = 96; pts = []
        fases = [r2.uniform(0, 2 * PI) for _ in range(4)]
        for i in range(N):
            a = 2 * PI * i / N
            k = 1 + .14 * math.sin(3 * a + fases[0]) + .08 * math.sin(5 * a + fases[1]) + .05 * math.sin(9 * a + fases[2])
            for ang, comp, larg in pontas:
                d = math.atan2(math.sin(a - ang), math.cos(a - ang))
                k += comp * math.exp(-(d / larg) ** 2)
            pts.append((math.cos(a) * rx * k, math.sin(a) * ry * k))
        bm = bmesh.new(); vs = [bm.verts.new((x, y, 0)) for x, y in pts]; f = bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=[f], quad_method="BEAUTY", ngon_method="EAR_CLIP")
        ext = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
        bmesh.ops.translate(bm, vec=(0, 0, altura), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free(); me.materials.append(cor)
        for p in me.polygons: p.use_smooth = True
        o = novo(nome, me, VEST, None, centro)
        bv = o.modifiers.new("Menisco", "BEVEL"); bv.width = altura * .9; bv.segments = 3; bv.limit_method = "ANGLE"
        return o

    # copo: boca em x ~1,04 (deitado para -X), mesa: topo z=0,775, borda da frente em y=-1,25
    # poca menor e fina: sai da boca do copo e chega ate a beira da mesa (y=-1,25), sem passar dela
    poca("V_Bebida_Derramada", (0.95, -1.135, .7752), .095, .062, [(-PI / 2, .75, .55), (PI, .25, .6)], 3, altura=.0011)
    # cortina escorrendo pela borda da mesa (fina, ondulada)
    bm = bmesh.new(); W, H, nx, nz = .07, .045, 10, 6; vs = []
    for j in range(nz + 1):
        for i in range(nx + 1):
            u = i / nx; v = j / nz
            larg = W * (1 - .6 * v) * (.8 + .2 * math.sin(u * 7)); x = (u - .5) * larg
            vs.append(bm.verts.new((x, -.0015 * math.sin(u * PI), -v * H * (1 + .3 * math.sin(u * 5 + 1)))))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 2], vs[a + nx + 1]))
    me = bpy.data.meshes.new("V_Bebida_Escorrida"); bm.to_mesh(me); bm.free(); me.materials.append(liq)
    for p in me.polygons: p.use_smooth = True
    o = novo("V_Bebida_Escorrida", me, VEST, None, (0.95, -1.2515, .7755))
    so = o.modifiers.new("Espessura", "SOLIDIFY"); so.thickness = .0018
    # pocinha no chao e gotas entre a mesa e o chao
    poca("V_Bebida_Chao", (0.97, -1.36, .0005), .09, .07, [(-PI / 2, .3, .5), (0, .2, .4)], 9, altura=.0012)
    for k in range(7):
        r = .006 + rr.random() * .009
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=r)
        bmesh.ops.scale(bm, vec=(1, 1, .3), verts=bm.verts)
        me = bpy.data.meshes.new("V_Bebida_Gota"); bm.to_mesh(me); bm.free(); me.materials.append(liq)
        for p in me.polygons: p.use_smooth = True
        a = rr.uniform(0, 2 * PI); d = rr.uniform(.11, .22)
        novo("V_Bebida_Gota_%d" % k, me, VEST, None, (0.97 + math.cos(a) * d, -1.36 + math.sin(a) * d * .7, .0008))
    feito.append("liquido derramado")

# =============================================================== COSTELA-DE-ADAO
raiz = bpy.data.objects.get("Costela_de_Adao")
if raiz and not raiz.get("modelo_usuario"):
    SALA = raiz.users_collection[0]
    folha_m = mat("Folha_Costela", "#1a3a1f", .4)
    fb = folha_m.node_tree.nodes.get("Principled BSDF")
    if "Subsurface Weight" in fb.inputs:
        fb.inputs["Subsurface Weight"].default_value = 0.0
    # textura da folha gerada: nervura central, nervuras laterais na direcao dos recortes, bordas mais escuras
    import numpy as np
    img = bpy.data.images.get("textura_folha_costela")
    if not img:
        H, W = 512, 256
        yy, xx = np.mgrid[0:H, 0:W]; u = 1 - yy / (H - 1); v = xx / (W - 1); d = np.abs(v - .5) * 2
        base = np.array(lin("#1f4a24"))[None, None, :] * (1 - .25 * d[..., None] ** 2)
        base = base * (1 + .1 * u[..., None])
        veia = (((u + d * .22 * np.sin(np.pi * np.minimum(u, .92))) * 11) % 1 < .045) & (d > .04)
        base = np.where(veia[..., None], base * 1.35 + .01, base)
        nerv = d < .025
        base = np.where(nerv[..., None], np.array(lin("#7f9e4c"))[None, None, :], base)
        base = base * (1 + np.random.default_rng(3).normal(0, .04, (H, W, 1)))
        srgb = np.where(base <= .0031308, base * 12.92, 1.055 * np.clip(base, 0, 1) ** (1 / 2.4) - .055)
        rgba = np.ones((H, W, 4), np.float32); rgba[..., :3] = np.clip(srgb, 0, 1)
        img = bpy.data.images.new("textura_folha_costela", W, H, alpha=False)
        img.pixels.foreach_set(np.flipud(rgba).ravel()); img.pack()
    nt = folha_m.node_tree
    if not nt.nodes.get("Folha_Img"):
        ti = nt.nodes.new("ShaderNodeTexImage"); ti.name = "Folha_Img"; ti.image = img
        nt.links.new(ti.outputs["Color"], fb.inputs["Base Color"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = .35
        nt.links.new(ti.outputs["Color"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], fb.inputs["Normal"])
    caule_m = mat("Caule_Costela", "#2f5a2a", .45)
    for c in list(raiz.children):
        if c.name.startswith("Vaso_Barro"):
            continue
        apagar(c)

    def folha(nome, L, seed):
        """Folha em grade (u ao longo da nervura, v de uma borda a outra): coracao com lobulos na base,
        recortes seguindo as nervuras (faixas de faces removidas), dobra na nervura e ponta caida."""
        r2 = random.Random(seed); NU, NV = 30, 20
        W = L * .48
        larg = lambda u: W * (.62 + .38 * math.sin(PI * min(u, .85) / 1.7 + .35)) * (1 - u) ** .45 + .002
        # recortes: linhas da grade (u constante) inteiras, de cada lado, da borda ate a profundidade sorteada
        linhas = sorted(r2.sample(range(6, NU - 6, 3), 5))
        cortes = {i: (r2.uniform(.5, .75), r2.uniform(.5, .75)) for i in linhas}   # profundidade (direita, esquerda)
        def pos(u, v):
            x = v * larg(u)
            # as linhas de u constante seguem as nervuras: inclinadas para a ponta, mais na borda do que no centro
            y = L * u + .12 * L * abs(v) * math.sin(PI * min(u, .92)) - .16 * L * (v * v) * (1 - u) ** 5
            z = -.13 * abs(x) - .32 * L * u * u + .005 * math.sin(u * 22 + v * 3)
            return Vector((x, y, z))
        def cortado(i, vc):
            if i not in cortes:
                return False
            prof = cortes[i][0] if vc > 0 else cortes[i][1]
            return abs(vc) > 1 - prof
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
        vs = [[bm.verts.new(pos(i / NU, -1 + 2 * j / NV)) for j in range(NV + 1)] for i in range(NU + 1)]
        for i in range(NU):
            for j in range(NV):
                vc = -1 + 2 * (j + .5) / NV
                if not cortado(i, vc):
                    f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
                    for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                        lp[uvl].uv = (b / NV, a / NU)          # u da imagem = largura, v = comprimento
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free(); me.materials.append(folha_m)
        for p in me.polygons: p.use_smooth = True
        return me

    r2 = random.Random(5)
    for k in range(8):
        a = k / 8 * 2 * PI + r2.uniform(-.25, .25)
        h = r2.uniform(.62, 1.15); rad = r2.uniform(.22, .42); L = r2.uniform(.3, .46)
        base = Vector((r2.uniform(-.03, .03), r2.uniform(-.03, .03), .37))
        ponta = Vector((math.cos(a) * rad, math.sin(a) * rad, h))
        # caule curvo (bezier com espessura)
        cu = bpy.data.curves.new("Costela_Peciolo_%d" % k, "CURVE"); cu.dimensions = "3D"
        cu.bevel_depth = .0065; cu.bevel_resolution = 2; cu.resolution_u = 10
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(1)
        p0, p1 = sp.bezier_points
        p0.co = base; p0.handle_left = base - Vector((0, 0, .1)); p0.handle_right = base + Vector((0, 0, h * .55))
        p1.co = ponta; p1.handle_left = ponta - Vector((math.cos(a) * .12, math.sin(a) * .12, -.06)); p1.handle_right = ponta + Vector((math.cos(a) * .05, math.sin(a) * .05, -.02))
        cu.materials.append(caule_m)
        po = bpy.data.objects.new("Costela_Peciolo_%d" % k, cu); SALA.objects.link(po); po.parent = raiz; po["detalhado"] = True
        # folha: eixo Y da folha segue para fora e um pouco para cima; normal para cima
        Y = Vector((math.cos(a), math.sin(a), r2.uniform(.15, .45))).normalized()
        X = Y.cross(Vector((0, 0, 1))).normalized(); Z = X.cross(Y).normalized()
        Mx = Matrix((X, Y, Z)).transposed().to_4x4()
        fo = novo("Costela_Folha_%d" % k, folha("Costela_Folha_%d" % k, L, 100 + k), SALA, raiz, ponta)
        fo.rotation_mode = "QUATERNION"; fo.rotation_quaternion = (Matrix.Rotation(r2.uniform(-.35, .35), 4, Y) @ Mx).to_quaternion()
        so = fo.modifiers.new("Espessura", "SOLIDIFY"); so.thickness = .002
    feito.append("costela-de-adao")

print("[DETALHE2] %s" % (", ".join(feito) or "nada (modelos do usuario preservados)"))
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[DETALHE2] cena principal salva")
