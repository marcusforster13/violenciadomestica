// A Casa em Silencio - gera as vozes dos personagens no ElevenLabs (mesmo esquema do Cassino e do Busca e Apreensao).
//
// Como usar:
//   1. A chave da API fica em 06_Audio/chave_elevenlabs.txt (so a chave, uma linha) - fora do GitHub (.gitignore).
//      Se esse arquivo nao existir, o script usa o do Busca e Apreensao
//      (Desktop\buscaeapreensao\06_Audio\chave_elevenlabs.txt) ou a variavel de ambiente ELEVENLABS_API_KEY.
//   2. Para so ver as falas e quantos caracteres vao ser gastos, sem usar a chave:
//        node 06_Audio/gerar_vozes_elevenlabs.js --listar
//   3. Para gerar:
//        node 06_Audio/gerar_vozes_elevenlabs.js
//      Rodar de novo so gera o que falta: fala que ja tem .mp3 ou .wav em 06_Audio/brutos nao gasta credito.
//   4. Os audios vao para 06_Audio/brutos e 04_ThreeJS/web/audio, e o catalogo "vozes.falas" do cenario passa a
//      ter todas as falas (o site acha o audio pelo TEXTO exato da fala).
//
// So vozes BRASILEIRAS (sotaque brazilian, idioma pt). As vozes de cada personagem estao em VOZES abaixo e sao
// conferidas na conta antes de gerar: se alguma nao for brasileira, o script para sem gastar nada.
// Diferenca do Cassino: aqui cada fala pertence a um so personagem (fala_vitima_.., fala_crianca_..), entao nao ha
// versao _f; a voz e escolhida pelo personagem.
const fs = require('fs'), path = require('path');
const AQUI = __dirname, RAIZ = path.join(AQUI, '..');
const BRUTOS = path.join(AQUI, 'brutos'), WEB_AUDIO = path.join(RAIZ, '04_ThreeJS', 'web', 'audio');
const CENARIOS = [path.join(RAIZ, '05_Treinamento', 'cenario_vd_01.json'), path.join(RAIZ, '04_ThreeJS', 'web', 'treinamento', 'cenario_vd_01.json')];
const API = 'https://api.elevenlabs.io/v1';
const MODELO = 'eleven_multilingual_v2';

// voz (brasileira) e jeito de falar de cada personagem.
const PERFIL = {
  vitima:    { nome: 'Vítima', voz: '4PNBmCCUBwRktp7B7R1y', rotulo: 'Larissa Diniz', estilo: { stability: .38, similarity_boost: .8, style: .4 } },
  crianca:   { nome: 'Criança', voz: 'HReOQZPV9tH5iTEnSbGo', rotulo: 'Bianca', estilo: { stability: .35, similarity_boost: .75, style: .55 } },
  vizinho:   { nome: 'Vizinho', voz: 'zoe2cQFqDDW4DteHDEWI', rotulo: 'Manoel Lopes', estilo: { stability: .5, similarity_boost: .8, style: .25 } },
  atendente: { nome: 'Atendente do 190', voz: '9pDzHy2OpOgeXM8SeL0t', rotulo: 'Borges', estilo: { stability: .65, similarity_boost: .8, style: .1 } },
  copom:     { nome: 'COPOM (rádio)', voz: 'FhdOWgf0bSw3HKWefhlq', rotulo: 'Jhony Tygas', estilo: { stability: .7, similarity_boost: .8, style: .05 } },
  guarnicao: { nome: 'Guarnição (policial)', voz: 'blPx0tvsvee8CuFd63lX', rotulo: 'Sávio F.', estilo: { stability: .6, similarity_boost: .8, style: .15 } },
  // agressor repete a voz do atendente do 190: o atendente so fala na ligacao do inicio, nunca junto com o agressor
  agressor:  { nome: 'Agressor', voz: '9pDzHy2OpOgeXM8SeL0t', rotulo: 'Borges (repetida: atendente do 190)', estilo: { stability: .32, similarity_boost: .8, style: .5 } },
};
const DE = { 'Vítima': 'vitima', 'Criança': 'crianca', 'Vizinho': 'vizinho', 'Atendente do 190': 'atendente', 'COPOM (rádio)': 'copom',
             'Guarnição (policial)': 'guarnicao', 'Agressor': 'agressor' };

// frases fixas do motor (04_ThreeJS/web/treinamento.js) que nao estavam no catalogo
const FIXAS = [
  ['guarnicao', 'Na porta, ao se identificar', 'Polícia Militar!'],
  ['guarnicao', 'Rádio: informa a chegada', 'COPOM, guarnição no local da ocorrência.'],
  ['guarnicao', 'Rádio: pede o SAMU', 'COPOM, solicito SAMU no local: vítima com lesões no rosto e no braço.'],
  ['guarnicao', 'Rádio: pede a perícia', 'COPOM, solicito perícia no local. Local isolado.'],
  ['guarnicao', 'Rádio: pede apoio', 'COPOM, solicito apoio de outra guarnição.'],
  ['guarnicao', 'Rádio: informa a fuga', 'COPOM, autor evadiu-se pelos fundos: homem, cerca de 35 anos, camisa polo listrada, bermuda bege, mão direita machucada.'],
  ['copom', 'Rádio: depois da prisão, pede a preservação do local', 'Guarnição, perícia a caminho. Preservem o local e fotografem os vestígios com placa até a chegada.'],
];

// ---------------------------------------------------------------- falas
function montarFalas() {
  const c = JSON.parse(fs.readFileSync(CENARIOS[0], 'utf8'));
  const cat = (c.vozes && c.vozes.falas) || [], saida = [], visto = new Set();
  const add = (quem, arquivo, quando, texto, noCatalogo) => {
    if (!texto || visto.has(texto)) return; visto.add(texto);
    saida.push({ quem, arquivo, quando, texto, noCatalogo });
  };
  for (const l of [...((c.relato_vitima || {}).completo || []), ...((c.relato_vitima || {}).minimiza || [])])
    add('vitima', l.audio, 'Relato da vítima', l.texto, false);           // o relato acha o audio pelo campo "audio"
  for (const f of cat) add(DE[f.personagem] || 'vitima', f.arquivo, f.quando, f.texto, true);
  const usados = new Set(saida.map(f => f.arquivo)), cont = {};
  const novoNome = quem => { let n; do { cont[quem] = (cont[quem] || 0) + 1; n = `fala_${quem}_${String(cont[quem]).padStart(2, '0')}`; } while (usados.has(n)); usados.add(n); return n; };
  for (const [quem, quando, texto] of FIXAS) if (!visto.has(texto)) add(quem, novoNome(quem), quando, texto, true);
  return saida;
}
const existe = a => ['.mp3', '.wav'].some(e => fs.existsSync(path.join(BRUTOS, a + e)));

// catalogo no cenario: troca so o bloco "vozes" (o resto do arquivo mantem a formatacao feita a mao)
function gravarCatalogo(falas) {
  const itens = falas.filter(f => f.noCatalogo).map(f => ({ arquivo: f.arquivo, personagem: PERFIL[f.quem].nome, quando: f.quando, texto: f.texto }));
  for (const arq of CENARIOS) {
    const s = fs.readFileSync(arq, 'utf8'), i = s.indexOf('"vozes"');
    if (i < 0) throw new Error('bloco "vozes" nao encontrado em ' + arq);
    const nota = JSON.parse(s).vozes._nota || '';
    const bloco = '"vozes": {\n    "_nota": ' + JSON.stringify(nota) + ',\n    "falas": [\n' +
      itens.map(f => '      ' + JSON.stringify(f)).join(',\n') + '\n    ]\n  }\n}\n';
    const novo = s.slice(0, i) + bloco;
    JSON.parse(novo);                                                    // garante JSON valido
    fs.writeFileSync(arq, novo);
  }
}

// ---------------------------------------------------------------- ElevenLabs
function chave() {
  if (process.env.ELEVENLABS_API_KEY) return process.env.ELEVENLABS_API_KEY.trim();
  for (const f of [path.join(AQUI, 'chave_elevenlabs.txt'), 'C:/Users/marcus.leite/Desktop/buscaeapreensao/06_Audio/chave_elevenlabs.txt'])
    if (fs.existsSync(f)) return fs.readFileSync(f, 'utf8').trim();
  console.error('Falta a chave: crie 06_Audio/chave_elevenlabs.txt com a sua chave da API do ElevenLabs.'); process.exit(1);
}
let KEY = null;
async function api(rota, opcoes = {}) {
  const r = await fetch(API + rota, { ...opcoes, headers: { 'xi-api-key': KEY, 'Content-Type': 'application/json', ...(opcoes.headers || {}) } });
  if (!r.ok) throw new Error(`${rota}: ${r.status} ${(await r.text()).slice(0, 300)}`);
  return r;
}
async function conferirVozesBrasileiras(quem) {
  const { voices } = await (await api('/voices')).json();
  const porId = new Map(voices.map(v => [v.voice_id, v]));
  for (const k of quem) {
    const v = porId.get(PERFIL[k].voz), l = (v && v.labels) || {};
    if (!v || !/brazil/i.test(l.accent || '') || !/^pt/i.test(l.language || 'pt'))
      throw new Error(`a voz de ${PERFIL[k].nome} (${PERFIL[k].rotulo}) nao e brasileira ou nao esta na conta; nada foi gerado`);
    console.log(`  ${PERFIL[k].nome.padEnd(22)} -> ${v.name} (${[l.gender, l.age, l.accent].filter(Boolean).join(', ')})`);
  }
}

(async () => {
  const falas = montarFalas();
  const faltam = falas.filter(f => !existe(f.arquivo) && PERFIL[f.quem].voz);
  const chars = faltam.reduce((a, f) => a + f.texto.length, 0);
  if (process.argv.includes('--listar')) {
    for (const f of falas) console.log(`${existe(f.arquivo) ? 'ok ' : PERFIL[f.quem].voz ? '   ' : '-- '} ${f.arquivo.padEnd(26)} ${f.quem.padEnd(10)} ${f.texto}`);
    const por = {}; for (const f of faltam) { por[f.quem] = por[f.quem] || [0, 0]; por[f.quem][0]++; por[f.quem][1] += f.texto.length; }
    console.log(`\n${falas.length} falas; ja gravadas ${falas.length - faltam.length}; faltam ${faltam.length}, que gastam ${chars} caracteres.`);
    for (const [k, [n, c]] of Object.entries(por)) console.log(`  ${PERFIL[k].nome.padEnd(22)} ${String(n).padStart(3)} falas  ${String(c).padStart(5)} caracteres  voz: ${PERFIL[k].rotulo}`);
    return;
  }
  KEY = chave();
  fs.mkdirSync(BRUTOS, { recursive: true }); fs.mkdirSync(WEB_AUDIO, { recursive: true });
  console.log(`${falas.length} falas; faltam ${faltam.length} (${chars} caracteres).`);
  await conferirVozesBrasileiras([...new Set(faltam.map(f => f.quem))]);
  let feitas = 0;
  for (const f of faltam) {
    const destino = path.join(BRUTOS, f.arquivo + '.mp3');
    const r = await api(`/text-to-speech/${PERFIL[f.quem].voz}?output_format=mp3_44100_128`, {
      method: 'POST', headers: { Accept: 'audio/mpeg' },
      body: JSON.stringify({ text: f.texto, model_id: MODELO, language_code: 'pt', voice_settings: { ...PERFIL[f.quem].estilo, use_speaker_boost: true } }),
    });
    fs.writeFileSync(destino, Buffer.from(await r.arrayBuffer()));
    feitas++; console.log(`  ${f.arquivo}: ${f.texto.slice(0, 60)}`);
  }
  for (const f of falas) for (const e of ['.mp3', '.wav']) {          // copia tudo o que existe para o site
    const o = path.join(BRUTOS, f.arquivo + e); if (fs.existsSync(o)) fs.copyFileSync(o, path.join(WEB_AUDIO, f.arquivo + e));
  }
  const sons = fs.readdirSync(BRUTOS).filter(n => /\.(mp3|ogg|wav)$/i.test(n)).sort();
  fs.writeFileSync(path.join(WEB_AUDIO, 'manifest.json'), JSON.stringify(sons));
  gravarCatalogo(falas);
  console.log(`Pronto: ${feitas} audios novos.`);
})().catch(e => { console.error('Erro:', e.message); process.exit(1); });
