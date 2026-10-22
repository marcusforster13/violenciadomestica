"""
A Casa em Silencio - integra modelos feitos a mao (.glb) na CENA PRINCIPAL.

Como usar:
  1. Exporte o modelo do Blender como .glb, MANTENDO a mesma posicao da cena (como foi feito com os livros).
  2. Coloque o .glb em 01_Cena_Render_Cycles/modelos/
  3. Registre em modelos/modelos.json:  { "arquivo.glb": { "substitui": "NomeDoObjetoRaiz", "colecao": "02_Sala" } }
  4. Rode:  blender -b casa_em_silencio.blend --python integrar_modelos.py
     (ou pelo atualizar_tudo.ps1, que ja chama este script antes de gerar as versoes VR e three.js)

O que o script faz:
  - backup automatico em backup/ antes de alterar
  - apaga o objeto antigo (e todos os filhos) indicado em "substitui"
  - importa o .glb no lugar, na colecao indicada
  - religa materiais pelo nome (ex.: "Madeira_Freijo.001" -> "Madeira_Freijo"), entao as texturas CC0 da cena valem
  - so reintegra se o .glb mudou (guarda a data do arquivo no proprio .blend)
"""
import bpy, os, json, time, shutil, re, math
from mathutils import Matrix

try:
    AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    AQUI = os.path.join(os.path.expanduser("~"), "Downloads", "DV", "01_Cena_Render_Cycles")
MOD = os.path.join(AQUI, "modelos")
CFG = os.path.join(MOD, "modelos.json")

def say(m):
    print("[MODELOS] " + m)

def apagar_hierarquia(ob):
    for c in list(ob.children):
        apagar_hierarquia(c)
    bpy.data.objects.remove(ob, do_unlink=True)

def base(nome):
    return re.sub(r"\.\d{3}$", "", nome)

if not os.path.exists(CFG):
    say("nenhum modelos.json encontrado; nada a fazer")
else:
    cfg = json.load(open(CFG, encoding="utf-8"))
    estado = bpy.context.scene.get("modelos_integrados", "{}")
    estado = json.loads(estado) if isinstance(estado, str) else {}
    pendentes = []
    for arq, info in cfg.items():
        caminho = os.path.join(MOD, arq)
        if not os.path.exists(caminho):
            say("AVISO: %s nao encontrado" % arq); continue
        mtime = os.path.getmtime(caminho)
        if estado.get(arq) == mtime and "--forcar" not in os.sys.argv:
            say("%s ja integrado (sem mudancas)" % arq); continue
        pendentes.append((arq, caminho, mtime, info))

    if pendentes and bpy.data.filepath:
        bk = os.path.join(AQUI, "backup")
        os.makedirs(bk, exist_ok=True)
        destino = os.path.join(bk, "casa_em_silencio_%s.blend" % time.strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(bpy.data.filepath, destino)
        say("backup: %s" % os.path.basename(destino))

    for arq, caminho, mtime, info in pendentes:
        nomes = info["substitui"] if isinstance(info["substitui"], list) else [info["substitui"]]
        lugar = None
        for nome in nomes:                          # aceita um nome ou uma lista de nomes
            alvo = bpy.data.objects.get(nome)
            if alvo:
                if lugar is None:                   # para "no_lugar": posicao e giro do objeto antigo
                    lugar = (alvo.matrix_world.translation.copy(), alvo.matrix_world.to_euler().z)
                apagar_hierarquia(alvo)
        antes = set(bpy.data.objects)
        mats_antes = set(bpy.data.materials)
        bpy.ops.import_scene.gltf(filepath=caminho)
        novos = [o for o in bpy.data.objects if o not in antes]
        col = bpy.data.collections.get(info.get("colecao", "")) or bpy.context.scene.collection
        religados = 0
        for o in novos:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)
            o["modelo_usuario"] = arq          # os scripts de detalhamento nao mexem em modelos feitos a mao
            for slot in o.material_slots:
                m = slot.material
                if m and m not in mats_antes:
                    existente = bpy.data.materials.get(base(m.name))
                    if existente and existente not in (m,) and existente in mats_antes:
                        slot.material = existente; religados += 1
        if info.get("no_lugar") or info.get("juntar"):
            # "no_lugar": modelo feito na origem (base no chao) vai para o lugar do antigo; "juntar": ja esta no lugar.
            # Nos dois casos vira 1 objeto, simplificado se precisar
            malhas = [o for o in novos if o.type == "MESH"]
            for o in malhas:
                o.data = o.data.copy(); o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix.Identity(4)
            for o in [o for o in novos if o.type != "MESH"]:
                bpy.data.objects.remove(o, do_unlink=True)
            alvo = malhas[0]
            with bpy.context.temp_override(active_object=alvo, selected_objects=malhas, selected_editable_objects=malhas):
                bpy.ops.object.join()
            tris = sum(len(pl.vertices) - 2 for pl in alvo.data.polygons)
            limite = info.get("max_tris")
            if limite and tris > limite:
                d = alvo.modifiers.new("Simplificar", "DECIMATE"); d.ratio = limite / tris; d.use_collapse_triangulate = True
                dg = bpy.context.evaluated_depsgraph_get()
                me = bpy.data.meshes.new_from_object(alvo.evaluated_get(dg))
                alvo.modifiers.remove(d); velho = alvo.data; alvo.data = me; bpy.data.meshes.remove(velho)
            for pl in alvo.data.polygons:
                pl.use_smooth = True
            alvo.name = alvo.data.name = nomes[0]
            alvo.rotation_mode = "XYZ"              # o glTF importa em quaternion: sem isso o giro e ignorado
            if lugar and info.get("no_lugar"):
                alvo.location = lugar[0]; alvo.rotation_euler = (0, 0, lugar[1])
            if "posicao" in info:                   # posicao/giro explicitos (ex.: encostar na parede)
                alvo.location = info["posicao"]
            if "giro_z" in info:
                alvo.rotation_euler = (0, 0, math.radians(info["giro_z"]))
            alvo["detalhado"] = True                # suavizar_objetos.py nao subdivide
            if any(n.type == "TEX_IMAGE" for sl in alvo.material_slots if sl.material and sl.material.node_tree for n in sl.material.node_tree.nodes):
                alvo["uv_proprio"] = True           # tem textura: a versao VR nao refaz a UV
            novos = [alvo]
            say("%s: %d -> %d triangulos" % (arq, tris, sum(len(pl.vertices) - 2 for pl in alvo.data.polygons)))
        for m in [m for m in bpy.data.materials if m.users == 0 and m not in mats_antes]:
            bpy.data.materials.remove(m)
        estado[arq] = mtime
        say("%s -> substituiu '%s' com %d objetos em %s (%d materiais religados aos da cena)"
            % (arq, info["substitui"], len(novos), col.name, religados))

    bpy.context.scene["modelos_integrados"] = json.dumps(estado)
    if pendentes and bpy.app.background:
        bpy.ops.wm.save_mainfile()
        say("cena principal salva")
