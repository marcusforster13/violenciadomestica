"""
A Casa em Silencio - tira o visual "low poly" das pecas redondas (vasos, garrafas, pratos, potes,
filtro de barro, troncos, abajur, pilotis, lampadas, hidrante, caixa d'agua...).

Subdivision Surface (render 2 / viewport 1) + vincos automaticos nas bordas vivas (angulo > 50 graus):
as curvas ficam lisas e as bordas (boca do vaso, fundo da garrafa, aba do prato) continuam definidas.
Nao destroi geometria (modificador "MM_Suave"). Pode rodar de novo sem duplicar.

Uso:  blender -b casa_em_silencio.blend --python suavizar_objetos.py
"""
import bpy, bmesh, math

ALVOS = ("Vaso", "Garrafa", "Prato", "Pote", "Filtro", "Copo", "Arroz", "Feijao", "Cupula", "Lampada", "Bulbo",
         "Hidrante", "Caixa_dAgua", "Pendente", "Ima", "Volante", "Abajur", "Balizador", "Luminaria_Base",
         "Tronco", "Piloti", "Rolo", "Urso", "Mastro", "Abracadeira", "Moldura_Lente", "Haste", "Torneira",
         "Bucha", "Isolador", "Transformador", "Prego", "Tampa_Esgoto", "Junta", "Caule")
PULAR = ("Gradil", "Barras", "Lixeira", "Pneu", "Aro", "Cortador")
LIMITE = math.radians(50)

feitos = 0
for ob in bpy.data.objects:
    if ob.type != "MESH" or not any(a in ob.name for a in ALVOS) or any(p in ob.name for p in PULAR):
        continue
    if ob.modifiers.get("MM_Suave") or any(m.type in {"ARRAY", "BOOLEAN", "SUBSURF", "WIREFRAME", "NODES"} for m in ob.modifiers):
        continue
    me = ob.data
    if len(me.vertices) < 12 or len(me.polygons) > 4000:
        continue
    bm = bmesh.new(); bm.from_mesh(me)
    cl = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.link_faces[0].normal.angle(e.link_faces[1].normal, 0) > LIMITE:
            e[cl] = 1.0
        elif len(e.link_faces) < 2:
            e[cl] = 1.0
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    sb = ob.modifiers.new("MM_Suave", "SUBSURF")
    sb.levels = 1; sb.render_levels = 2; sb.use_limit_surface = True
    # a subdivisao vem antes de deslocamentos/espessuras ja existentes
    ob.modifiers.move(ob.modifiers.find("MM_Suave"), 0)
    feitos += 1

print("[SUAVE] %d pecas redondas suavizadas (subdivisao + vincos nas bordas)" % feitos)
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[SUAVE] cena principal salva")
