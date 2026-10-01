"""
A Casa em Silencio - aplica as texturas CC0 (Poly Haven) na CENA PRINCIPAL (Cycles).

Uso:  blender -b casa_em_silencio.blend --python aplicar_texturas_cc0.py
      (ou abrir o .blend, aba Scripting > Open > Run Script, e salvar)

- Materiais PBR com projecao em caixa (coordenadas do objeto, em metros): nao precisa de UV.
- Cor + rugosidade + relevo (mapa de deslocamento como Bump).
- Cada material recebe as propriedades "cc0_pasta" e "cc0_tile"; os pipelines de VR e
  three.js leem isso para converter para UV e glTF.
- Pode rodar de novo quantas vezes quiser (reconstroi os materiais a partir da tabela).
- As texturas ficam em ../04_ThreeJS/texturas_cc0 e sao referenciadas por caminho relativo.
"""
import bpy, os
import numpy as np

try:
    AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    AQUI = ""
if not os.path.isdir(os.path.join(AQUI, "..", "04_ThreeJS", "texturas_cc0")):
    AQUI = os.path.join(os.path.expanduser("~"), "Downloads", "DV", "01_Cena_Render_Cycles")
TEX = os.path.normpath(os.path.join(AQUI, "..", "04_ThreeJS", "texturas_cc0"))

def hx(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))

def lin(c):
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def arquivos(pasta):
    d = os.path.join(TEX, pasta); fs = sorted(os.listdir(d))
    pick = lambda k: next((os.path.join(d, f) for f in fs if k in f.lower()), None)
    return pick("_diff") or pick("_col"), pick("_rough"), pick("_disp")

def grafite(path):
    """Versao grafite do metal verde (mantem arranhoes e ferrugem). Salva junto das texturas."""
    out = os.path.join(os.path.dirname(path), "metal_grafite_diff.png")
    if not os.path.exists(out):
        src = bpy.data.images.load(path)
        w, h = src.size; px = np.empty(w * h * 4, np.float32); src.pixels.foreach_get(px)
        px = px.reshape(-1, 4); rgb = px[:, :3]
        g = (rgb @ np.array([.3, .59, .11]))[:, None]
        rgb = np.clip(g + (rgb - g) * .18, 0, 1) / max(g.mean(), 1e-3) * .5
        px[:, :3] = np.clip(rgb, 0, 1)
        dst = bpy.data.images.new("_tmp_grafite", w, h, alpha=False)
        dst.pixels.foreach_set(px.ravel()); dst.filepath_raw = out; dst.file_format = "PNG"; dst.save()
        bpy.data.images.remove(src); bpy.data.images.remove(dst)
    return out

def neutro(path):
    """Tecido em tom neutro e claro (sem cor), para tingir com a cor de cada estofado."""
    out = os.path.join(os.path.dirname(path), "tecido_neutro_cor.png")
    if not os.path.exists(out):
        src = bpy.data.images.load(path)
        w, h = src.size; px = np.empty(w * h * 4, np.float32); src.pixels.foreach_get(px)
        px = px.reshape(-1, 4); g = (px[:, :3] @ np.array([.3, .59, .11]))[:, None]
        px[:, :3] = np.clip(g / max(g.mean(), 1e-3) * .78, 0, 1)
        dst = bpy.data.images.new("_tmp_neutro", w, h, alpha=False)
        dst.pixels.foreach_set(px.ravel()); dst.filepath_raw = out; dst.file_format = "PNG"; dst.save()
        bpy.data.images.remove(src); bpy.data.images.remove(dst)
    return out

def carregar(path, dados):
    img = bpy.data.images.load(path, check_existing=True)
    try:
        img.filepath = bpy.path.relpath(path)
    except ValueError:
        pass
    if dados:
        img.colorspace_settings.name = "Non-Color"
    return img

def media_linear(img):
    w, h = img.size; px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px)
    m = px.reshape(-1, 4)[::7, :3].mean(0)
    return lin(tuple(m))

def pbr_caixa(mat, pasta, tile, tint=None, recolor=None, relevo=.35):
    diff, rough, disp = arquivos(pasta)
    if recolor:
        diff = recolor(diff)
    alvo = lin(hx(tint)) if tint else tuple(mat.diffuse_color[:3])
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None) or nt.nodes.new("ShaderNodeBsdfPrincipled")
    for n in list(nt.nodes):
        if n not in (b, out):
            nt.nodes.remove(n)
    for inp in b.inputs:
        for l in list(inp.links):
            nt.links.remove(l)
    if not out.inputs["Surface"].is_linked:
        nt.links.new(b.outputs[0], out.inputs["Surface"])
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / tile,) * 3
    L(tc.outputs["Object"], mp.inputs["Vector"])
    def tex(path, dados):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = carregar(path, dados)
        t.projection = "BOX"; t.projection_blend = .2
        L(mp.outputs["Vector"], t.inputs["Vector"])
        return t
    td = tex(diff, False)
    fator = [min(1.0, a / max(m, 1e-3)) for a, m in zip(alvo, media_linear(td.image))]
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    next(i for i in mix.inputs if i.name == "Factor" and i.type == "VALUE").default_value = 1.0
    L(td.outputs["Color"], next(i for i in mix.inputs if i.name == "A" and i.type == "RGBA"))
    next(i for i in mix.inputs if i.name == "B" and i.type == "RGBA").default_value = (*fator, 1)
    L(next(o for o in mix.outputs if o.name == "Result" and o.type == "RGBA"), b.inputs["Base Color"])
    if rough:
        tr = tex(rough, True); sep = nt.nodes.new("ShaderNodeSeparateColor")
        L(tr.outputs["Color"], sep.inputs["Color"]); L(sep.outputs["Green"], b.inputs["Roughness"])
    if disp:
        tdp = tex(disp, True); bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = relevo; bp.inputs["Distance"].default_value = .02
        L(tdp.outputs["Color"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = 0.0
    mat["cc0_pasta"] = pasta
    mat["cc0_tile"] = float(tile)
    mat["cc0_tint"] = list(alvo)
    mat["cc0_recolor"] = recolor.__name__ if recolor else ""

# nome do material -> (pasta, tile em metros, cor alvo, recolor, forca do relevo)
TABELA = {
    "Reboco_Branco":            ("reboco_pintado", 2.0, None, None, .25),
    "Fachada_Branca":           ("reboco_pintado", 2.0, None, None, .25),
    "Fachada_Areia":            ("reboco_pintado", 2.0, None, None, .25),
    "Fachada_Terracota":        ("reboco_pintado", 2.0, None, None, .25),
    "Fachada_Cimento_Queimado": ("concreto", 2.0, None, None, .2),
    "Concreto_Aparente":        ("concreto", 2.0, None, None, .25),
    "Meio_Fio_Concreto":        ("concreto", 1.5, None, None, .35),
    "Sarjeta_Concreto":         ("concreto", 1.5, None, None, .35),
    "Concreto_Poste":           ("concreto", 1.2, None, None, .3),
    "Asfalto":                  ("asfalto", 3.0, "#3a3a3c", None, .5),
    "Asfalto_Remendo":          ("asfalto", 3.0, "#1f1f21", None, .5),
    "Madeira_Freijo":           ("madeira_tabuas", 1.5, "#b98458", None, .2),
    "Madeira_Forro":            ("madeira_tabuas", 1.5, "#a8744a", None, .2),
    "Madeira_Jacaranda":        ("madeira_escura", 1.0, None, None, .1),
    "Filete_de_Pedra":          ("pedra_filete", 1.2, "#d8ccb8", None, .8),
    "Solo_Grama":               ("grama", 2.0, "#5d7a3a", None, .5),
    "Terra_Canteiro":           ("terra", 1.5, None, None, .6),
    "Portao_Ferro":             ("metal_pintado", 1.0, "#2a2d31", grafite, .15),
    "Poste_Metal":              ("metal_pintado", 1.0, "#3b3d40", grafite, .15),
    "Transformador":            ("metal_pintado", 1.0, "#7e8488", grafite, .15),
    "Couro_Caramelo":           ("couro", .6, None, None, .5),
    "Tronco_Palmeira":          ("casca_arvore", 1.2, "#6b5b4a", None, .9),
    "Tecido_Verde":             ("tecido", .35, "#50604f", neutro, .3),
    "Tecido_Areia":             ("tecido", .35, "#c9b58c", neutro, .3),
}
# estofados e cortinas das casas vizinhas (cores sorteadas na criacao da cena)
for _m in list(bpy.data.materials):
    if _m.name.endswith(("_Tecido_Sofa", "_Cortina")) and _m.name not in TABELA:
        _c = tuple(round(min(1, max(0, x)) ** (1 / 2.2) * 255) for x in _m.diffuse_color[:3])
        TABELA[_m.name] = ("tecido", .35 if _m.name.endswith("Sofa") else .5, "#%02x%02x%02x" % _c, neutro, .25)
feitos = []
for nome, (pasta, tile, tint, rec, relevo) in TABELA.items():
    m = bpy.data.materials.get(nome)
    if m and os.path.isdir(os.path.join(TEX, pasta)):
        pbr_caixa(m, pasta, tile, tint, rec, relevo); feitos.append(nome)
print("[CC0] %d materiais com texturas Poly Haven: %s" % (len(feitos), ", ".join(feitos)))
if bpy.app.background:
    bpy.ops.wm.save_mainfile()
    print("[CC0] cena principal salva")
