"""
Gera 06_Audio/ROTEIRO_VOZES.html (para imprimir) a partir do cenario do treinamento.
Lista todas as falas por personagem, com o nome do arquivo e se ja existe gravacao em 06_Audio/brutos.

Uso:  "C:\\Program Files\\Blender Foundation\\Blender 5.2\\5.2\\python\\bin\\python.exe" gerar_roteiro_vozes.py
"""
import json, os, html

AQUI = os.path.dirname(os.path.abspath(__file__))
CEN = json.load(open(os.path.join(AQUI, '..', '05_Treinamento', 'cenario_vd_01.json'), encoding='utf8'))
BRUTOS = os.path.join(AQUI, 'brutos')
gravados = {os.path.splitext(f)[0] for f in os.listdir(BRUTOS)} if os.path.isdir(BRUTOS) else set()

falas = []
for k, rotulo in (('completo', 'Relato (ao clicar nela / "conte o que aconteceu")'), ('minimiza', 'Relato na variação em que ela minimiza')):
    for l in CEN['relato_vitima'][k]:
        quando = rotulo + (' · só quando ' + l['condicao'].split("'")[1].replace('_', ' ') if l.get('condicao') else '')
        falas.append({'arquivo': l['audio'], 'personagem': 'Vítima', 'quando': quando, 'texto': l['texto']})
falas += CEN['vozes']['falas']

ORDEM = ['Vítima', 'Agressor', 'Criança', 'Vizinho', 'Atendente do 190', 'COPOM (rádio)']
DICAS = {
    'Vítima': 'Mulher, cerca de 30 anos, acabou de ser agredida. Voz baixa e cansada, com pausas nos "…". As falas da ligação para o 190 são sussurradas, com medo de ser ouvida.',
    'Agressor': 'Homem, cerca de 35 anos, bebeu. Alterna entre minimizar ("foi só uma briga") e irritação. Nada de grito exagerado: a tensão é mais realista.',
    'Criança': 'Menina de 6 anos, assustada, voz baixa. Grave com uma criança só com autorização dos responsáveis; uma adulta imitando voz infantil também funciona.',
    'Vizinho': 'Homem adulto, preocupado, falando com o policial na calçada. Tom de quem quer ajudar sem se envolver demais.',
    'Atendente do 190': 'Atendente da central: voz calma, firme e objetiva.',
    'COPOM (rádio)': 'Operador de rádio: frases curtas, tom neutro. Pode gravar perto do microfone com um pouco de "rádio" na voz.',
}
def seg(t):   # estimativa: fala pausada (~2,3 palavras/s) + pausas nos "…"
    s = len(t.split()) / 2.3 + t.count('…') * .6
    return '%d–%d s' % (max(1, round(s)), max(2, round(s * 1.35)))

linhas, total, feitas = [], 0, 0
for p in ORDEM:
    grupo = [f for f in falas if f['personagem'] == p]
    if not grupo: continue
    fz = sum(f['arquivo'] in gravados for f in grupo); total += len(grupo); feitas += fz
    linhas.append(f'<h2>{html.escape(p)} <small>{fz}/{len(grupo)} gravadas</small></h2><p class="dica">{html.escape(DICAS.get(p, ""))}</p>')
    linhas.append('<table><tr><th>#</th><th>Fala</th><th>Tempo</th><th>Arquivo</th><th class="ok">✓</th></tr>')
    for i, f in enumerate(grupo, 1):
        ok = f['arquivo'] in gravados
        linhas.append(f'<tr class="{"feita" if ok else ""}"><td class="n">{i}</td><td class="fala">{html.escape(f["texto"])}'
                      f'<span class="obs">{html.escape(f["quando"])}</span></td><td class="t">{seg(f["texto"])}</td>'
                      f'<td class="arq">{f["arquivo"]}</td><td class="ok">{"✓" if ok else ""}</td></tr>')
    linhas.append('</table>')

doc = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Roteiro de vozes</title>
<style>
  body {{ font: 15px/1.45 "Segoe UI", system-ui, sans-serif; color: #111; background: #fff; max-width: 860px; margin: 24px auto; padding: 0 16px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }} h2 {{ font-size: 17px; margin: 28px 0 4px; border-bottom: 2px solid #111; padding-bottom: 3px; }}
  h2 small {{ font-weight: 400; color: #555; font-size: 13px; }} .sub {{ color: #444; margin: 0 0 12px; }} .dica {{ color: #333; margin: 4px 0 10px; font-style: italic; }}
  .box {{ border: 1px solid #999; padding: 10px 14px; margin: 12px 0; }} .box ul {{ margin: 6px 0 0; padding-left: 18px; }}
  table {{ width: 100%; border-collapse: collapse; }} th, td {{ border: 1px solid #888; padding: 7px 9px; vertical-align: top; text-align: left; }}
  th {{ background: #eee; font-size: 13px; }} td.n {{ width: 26px; text-align: center; font-weight: 700; }} td.fala {{ font-size: 16.5px; }}
  td.t {{ width: 64px; text-align: center; white-space: nowrap; font-size: 13px; }} td.arq {{ width: 175px; font: 12px Consolas, monospace; word-break: break-all; }}
  .ok {{ width: 22px; text-align: center; }} .obs {{ display: block; color: #555; font-size: 12px; margin-top: 3px; }} tr.feita td {{ color: #777; }}
  @media print {{ body {{ margin: 0; }} h2 {{ break-after: avoid; }} tr {{ break-inside: avoid; }} }}
</style></head><body>
<h1>Roteiro de vozes — todos os personagens</h1>
<p class="sub">A Casa em Silêncio · cenário vd_01 · {feitas} de {total} falas já gravadas (linhas em cinza)</p>
<div class="box"><b>Como gravar</b><ul>
<li><b>Um arquivo por fala</b>, com o nome da coluna "Arquivo" (.wav ou .mp3), em <b>06_Audio\\brutos\\</b>. Deixe ~0,5 s de silêncio no começo e no fim.</li>
<li>O <b>tempo é só referência</b>: o site usa a duração real do arquivo.</li>
<li>Fale <b>exatamente o texto</b> da tabela (se quiser mudar uma fala, me avise para eu mudar no site também).</li>
<li>Cômodo pequeno e sem eco (cortina, roupas, almofadas), sem ventilador ou geladeira ligados. Celular serve.</li>
<li>A fala que tiver arquivo toca com a voz gravada saindo do personagem (com a boca mexendo); as outras continuam com voz sintética.</li>
</ul></div>
{"".join(linhas)}
</body></html>
'''
open(os.path.join(AQUI, 'ROTEIRO_VOZES.html'), 'w', encoding='utf8').write(doc)
print('[VOZES] %d falas, %d gravadas -> ROTEIRO_VOZES.html' % (total, feitas))
