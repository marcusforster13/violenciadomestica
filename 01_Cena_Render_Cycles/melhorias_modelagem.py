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
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[MODELAGEM] cena principal salva")
