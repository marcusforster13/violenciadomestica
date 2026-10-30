"""
A Casa em Silencio - passe de melhoria de modelagem na CENA PRINCIPAL.

- Quinas chanfradas (Bevel) em todas as pecas em caixa, proporcionais ao tamanho da peca,
  com normais "endurecidas" para a luz pegar nas bordas (o que mais denuncia o 3D sao quinas vivas).
- Estofados (sofas, poltrona, almofadas) com cantos bem arredondados.
- Menos segmentos nas pecas distantes (rua, casas vizinhas) para nao pesar no VR.
Nao destroi geometria: so acrescenta modificadores "MM_*". Pode rodar de novo sem duplicar.

Uso:  blender -b casa_em_silencio.blend --python melhorias_modelagem.py
"""
import bpy

INTERIOR = {"01_Estrutura", "02_Sala", "03_Jantar", "04_Cozinha", "05_Varanda", "08_Vestigios", "10_Viatura_PMERJ", "10b_Carros_Moradores"}
EXTERIOR = {"06_Jardim", "07_Rua_Condominio", "07b_Casas_Vizinhas", "07d_Postes_Fiacao"}
ESTOFADOS = ("Sofa_Assento", "Sofa_Encosto", "Sofa_Almofada", "Poltrona_Assento", "Poltrona_Braco", "Poltrona_Encosto",
             "Almofada", "Sala_Sofa", "Banco", "Mala_Base", "Mala_Tampa", "Roupa")
PULAR = ("Vidro", "Cortador", "Faixa", "Asfalto", "Calcada", "Sarjeta", "Gramado", "Remendo", "Neblina", "Placa_Faixa",
         "Tela", "Sala_Parede", "Sala_Teto", "Sala_Piso", "Painel_Azulejos", "Revestimento", "Marca_Quadro")

n = {"quinas": 0, "estofados": 0}
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.users_collection:
        continue
    col = ob.users_collection[0].name
    if col not in INTERIOR | EXTERIOR or any(p in ob.name for p in PULAR):
        continue
    if ob.modifiers.get("MM_Bevel"):
        continue
    if any(m.type in {"ARRAY", "BOOLEAN", "REMESH", "DISPLACE", "NODES", "WIREFRAME", "SOLIDIFY", "SUBSURF", "BEVEL"} for m in ob.modifiers):
        continue
    me = ob.data
    if len(me.vertices) != 8 or len(me.polygons) != 6:      # so pecas em caixa
        continue
    d = sorted(ob.dimensions)
    if d[2] > 30:
        continue
    estofado = any(e in ob.name for e in ESTOFADOS)
    if estofado:
        w = min(.045, d[0] * .32); seg = 4
    else:
        w = min(.012, d[0] * .22); seg = 2 if col in INTERIOR else 1
    if w < .0015:
        continue
    bv = ob.modifiers.new("MM_Bevel", "BEVEL")
    bv.width = w; bv.segments = seg; bv.limit_method = "ANGLE"
    bv.harden_normals = not estofado
    bv.profile = .7 if estofado else .5
    for p in me.polygons:
        p.use_smooth = True
    n["estofados" if estofado else "quinas"] += 1

print("[MODELAGEM] quinas chanfradas em %d pecas, %d estofados arredondados" % (n["quinas"], n["estofados"]))

# sacadas das casas vizinhas: o guarda-corpo de vidro so tinha a frente; fecha as duas laterais ate a fachada
import bmesh
from mathutils import Vector, Matrix


def _caixa_mundo(nome, ref, centro, tam, cilindro=False):
    if bpy.data.objects.get(nome):
        return 0
    bm = bmesh.new()
    if cilindro:      # corrimao ao longo de Y
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=tam[0], radius2=tam[0], depth=tam[1],
                              matrix=Matrix.Rotation(1.5708, 4, "X"))
    else:
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal(Vector(tam).to_4d()))
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    for m in ref.data.materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(nome, me)
    ref.users_collection[0].objects.link(ob)
    ob.matrix_world = Matrix.Translation(centro)
    if ref.parent:
        ob.parent = ref.parent; ob.matrix_parent_inverse = ref.parent.matrix_world.inverted()
    return 1


def _bb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(c[i] for c in cs) for i in range(3)]), Vector([max(c[i] for c in cs) for i in range(3)])


laterais = 0
for vidro in [o for o in bpy.data.objects if o.name.endswith("_Sacada_Vidro")]:
    base = vidro.name[:-len("_Sacada_Vidro")]
    piso, corr = bpy.data.objects.get(base + "_Sacada_Piso"), bpy.data.objects.get(base + "_Sacada_Corrimao")
    if not piso:
        continue
    v0, v1 = _bb(vidro); p0, p1 = _bb(piso)
    yv = (v0.y + v1.y) / 2
    yf = p1.y if abs(p1.y - yv) > abs(p0.y - yv) else p0.y          # fachada: lado do piso oposto ao vidro
    prof = abs(yf - yv); ym = (yf + yv) / 2; e = v1.y - v0.y
    for lado, x in (("E", v0.x + e / 2), ("D", v1.x - e / 2)):
        laterais += _caixa_mundo(base + "_Sacada_Vidro_Lado_" + lado, vidro, Vector((x, ym, (v0.z + v1.z) / 2)), (e, prof, v1.z - v0.z))
        if corr:
            c0, c1 = _bb(corr)
            _caixa_mundo(base + "_Sacada_Corrimao_Lado_" + lado, corr, Vector((x, ym, (c0.z + c1.z) / 2)), ((c1.z - c0.z) / 2, prof), cilindro=True)
print("[MODELAGEM] sacadas: %d vidros laterais novos (guarda-corpo fechado ate a fachada)" % laterais)
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[MODELAGEM] cena principal salva")
