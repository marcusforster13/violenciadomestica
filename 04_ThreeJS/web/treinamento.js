/*
  A Casa em Silencio - motor do treinamento (fase 2)
  Le treinamento/cenario_vd_01.json (fases, acoes, pontos, falhas graves, vestigios, variacoes, dialogos, radio).

  Controles
    Computador: clique = usar ferramenta / interagir / botoes   T = ferramentas   R = radio   K = checklist
    Quest:      gatilho = usar ferramenta / botoes / teleporte
                grip (qualquer mao) = lanterna   botao Y ou B = menu do treinamento
  Variacoes forcadas pela URL (para o instrutor):  ?v=agressor:agressivo,faca:pia,vitima:retrata
*/
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

export async function iniciar(ctx) {
  const { scene, camera, rig, renderer } = ctx;
  const CEN = await fetch('treinamento/cenario_vd_01.json').then(r => r.json());
  const V = new THREE.Vector3(), V2 = new THREE.Vector3(), Q = new THREE.Quaternion();

  /* ================= estado ================= */
  const S = {
    ativo: false, inicio: 0, fim: 0, variacao: {}, feitos: new Map(), erros: [], graves: [], log: [],
    ferramenta: 'mao', luvas: false, identificado: false, socorroOuvido: false, entrou: false,
    contatoVitima: false, separado: false, algemado: false, desistenciaResolvida: false, criancaAchada: false,
    vestReconhecidos: new Set(), vestFotografados: new Set(), placas: 0, fitas: [], fitaInicio: null,
    tempoFachada: 0, tempoDentro: 0, avisoAgressor: false, faca: null,
    modo: 'avaliacao', apoio: false, agressorAchado: false, rendido: false, abordando: false, quintal: []
  };
  const acoes = {};
  CEN.fases.forEach(f => {
    (f.acoes || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'acao' });
    (f.erros || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'erro' });
    (f.falhas_graves || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'grave' });
  });
  const cond1 = c => {
    const m = c.match(/variacao\.(\w+)\s*(==|!=)\s*'([^']*)'/);
    if (!m) return true;
    return m[2] === '==' ? S.variacao[m[1]] === m[3] : S.variacao[m[1]] !== m[3];
  };
  // "a == 'x' && b != 'y' || c == 'z'"  (&& tem precedencia sobre ||)
  const cond = c => !c || c.split('||').some(ou => ou.split('&&').every(cond1));
  const tempo = () => ((S.fim || performance.now()) - S.inicio) / 1000;
  const fmt = s => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  function registrar(id, extra = '') {
    const a = acoes[id]; if (!a || !S.ativo) return;
    if (a.tipo === 'acao') {
      if (S.feitos.has(id) || !cond(a.condicao)) return;
      S.feitos.set(id, tempo());
    } else if (a.tipo === 'erro') {
      S.erros.push({ id, texto: a.texto, pontos: a.pontos, t: tempo(), extra });
    } else {
      if (S.graves.some(g => g.id === id)) return;
      S.graves.push({ id, texto: a.texto, pontos: a.pontos, t: tempo(), extra });
      legenda('Instrutor', 'Falha grave registrada: ' + a.texto, 4);
    }
    S.log.push({ t: +tempo().toFixed(1), id, extra });
    status();
  }
  function penalidade(pontos, texto, feedback) {
    S.erros.push({ id: 'conduta', texto, pontos, feedback, t: tempo() });
    S.log.push({ t: +tempo().toFixed(1), id: 'conduta', extra: texto }); status();
  }

  /* ================= paineis 3D (funcionam no computador e no Quest) ================= */
  const paineis = [];
  class Painel {
    constructor(largura = 1.1) {
      this.largura = largura; this.botoes = [];
      this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
        new THREE.MeshBasicMaterial({ transparent: true, depthTest: false, toneMapped: false, fog: false }));
      this.mesh.renderOrder = 1000; this.mesh.visible = false; scene.add(this.mesh); paineis.push(this);
      // realce do botao apontado pelo controle (no VR a linha do controle some atras do painel)
      this.realce = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: 0xf0a340, transparent: true, opacity: .32, depthTest: false, toneMapped: false, fog: false }));
      this.realce.renderOrder = 1001; this.realce.visible = false; this.mesh.add(this.realce);
    }
    apontar(ray) {                                   // devolve o ponto atingido e realca o botao embaixo do raio
      if (!this.mesh.visible) return null;
      const h = ray.intersectObject(this.mesh, false)[0]; if (!h) return null;
      const py = (1 - h.uv.y) * this.H, b = this.botoes.find(b => py >= b.y0 && py <= b.y1);
      if (b) { this.realce.position.set(0, .5 - (b.y0 + b.y1) / 2 / this.H, .001); this.realce.scale.set(1 - 2 * 56 / 1024, (b.y1 - b.y0) / this.H, 1); this.realce.visible = true; }
      return h;
    }
    mostrar({ tag = '', titulo = '', texto = '', botoes = [], longe = 1.15 }) {
      const W = 1024, P = 56, cv = document.createElement('canvas'), g = cv.getContext('2d');
      cv.width = W; cv.height = 2400;
      const linhas = (txt, fonte, maxW) => { g.font = fonte; const out = []; for (const par of String(txt).split('\n')) { let l = ''; for (const w of par.split(' ')) { const t = l ? l + ' ' + w : w; if (g.measureText(t).width > maxW && l) { out.push(l); l = w; } else l = t; } out.push(l); } return out; };
      const lt = titulo ? linhas(titulo, '700 46px Segoe UI, sans-serif', W - 2 * P) : [];
      const lx = texto ? linhas(texto, '400 32px Segoe UI, sans-serif', W - 2 * P) : [];
      let y = P; const H0 = P + (tag ? 40 : 0) + lt.length * 56 + (lx.length ? 16 + lx.length * 44 : 0) + botoes.length * 92 + P + 10;
      cv.height = Math.min(2400, H0);
      g.fillStyle = 'rgba(11,14,22,.95)'; g.beginPath(); g.roundRect(0, 0, W, cv.height, 22); g.fill();
      g.strokeStyle = 'rgba(240,163,64,.5)'; g.lineWidth = 3; g.stroke();
      if (tag) { g.fillStyle = '#f0a340'; g.font = '500 24px Consolas, monospace'; g.fillText(tag.toUpperCase(), P, y + 22); y += 40; }
      g.fillStyle = '#efe9df'; g.font = '700 46px Segoe UI, sans-serif'; lt.forEach(l => { g.fillText(l, P, y + 44); y += 56; });
      if (lx.length) { y += 16; g.fillStyle = 'rgba(239,233,223,.86)'; g.font = '400 32px Segoe UI, sans-serif'; lx.forEach(l => { g.fillText(l, P, y + 32); y += 44; }); }
      y += 10; this.botoes = [];
      for (const b of botoes) {
        y += 12; const h = 72;
        g.fillStyle = b.cor || 'rgba(240,163,64,.14)'; g.beginPath(); g.roundRect(P, y, W - 2 * P, h, 12); g.fill();
        g.strokeStyle = 'rgba(240,163,64,.55)'; g.lineWidth = 2; g.stroke();
        g.fillStyle = '#efe9df'; g.font = '600 30px Segoe UI, sans-serif';
        let rot = b.label; while (g.measureText(rot).width > W - 2 * P - 40 && rot.length > 4) rot = rot.slice(0, -2);
        if (rot !== b.label) rot = rot.slice(0, -1) + '…';
        g.fillText(rot, P + 20, y + 46);
        this.botoes.push({ ...b, y0: y, y1: y + h }); y += h + 8;
      }
      const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
      this.mesh.material.map?.dispose(); this.mesh.material.map = tex; this.mesh.material.needsUpdate = true;
      this.H = cv.height; this.mesh.scale.set(this.largura, this.largura * cv.height / W, 1);
      camera.getWorldPosition(V); camera.getWorldDirection(V2); V2.y = 0; V2.normalize();
      this.mesh.position.copy(V).addScaledVector(V2, longe); this.mesh.position.y = V.y - .08;
      this.mesh.lookAt(V.x, this.mesh.position.y, V.z); this.mesh.visible = true;
      return this;
    }
    esconder() { this.mesh.visible = false; this.realce.visible = false; }
    clique(ray) {
      if (!this.mesh.visible) return false;
      const h = ray.intersectObject(this.mesh, false)[0]; if (!h) return false;
      const py = (1 - h.uv.y) * this.H, b = this.botoes.find(b => py >= b.y0 && py <= b.y1);
      if (b && b.acao) b.acao();
      return true;
    }
  }
  const menu = new Painel(1.1), dialogo = new Painel(1.15);
  const cursorVR = new THREE.Mesh(new THREE.CircleGeometry(.012, 20), new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false, toneMapped: false, fog: false }));
  cursorVR.renderOrder = 1003; cursorVR.visible = false; scene.add(cursorVR);
  // chamado a cada quadro pelo index.html com o raio de cada controle; devolve o acerto de cada raio (ou null)
  function apontar(raios) {
    for (const p of paineis) p.realce.visible = false;
    let ultimo = null;
    const hs = raios.map(r => { let h = null; for (const p of paineis) h = p.apontar(r) || h; if (h) ultimo = h; return h; });
    cursorVR.visible = !!ultimo;
    if (ultimo) { cursorVR.position.copy(ultimo.point); cursorVR.quaternion.copy(ultimo.object.quaternion); cursorVR.translateZ(.002); }
    return hs;
  }
  const fecharPaineis = () => paineis.forEach(p => p.esconder());

  /* legenda presa a camera */
  const lcv = document.createElement('canvas'); lcv.width = 1400; lcv.height = 200;
  const ltex = new THREE.CanvasTexture(lcv); ltex.colorSpace = THREE.SRGBColorSpace;
  const leg = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 1.0 * 200 / 1400), new THREE.MeshBasicMaterial({ map: ltex, transparent: true, depthTest: false, toneMapped: false, fog: false }));
  leg.position.set(0, -.3, -.95); leg.renderOrder = 1001; leg.visible = false; camera.add(leg);
  let legAte = 0;
  function legenda(quem, texto, seg = 4) {
    const g = lcv.getContext('2d'); g.clearRect(0, 0, 1400, 200);
    g.fillStyle = 'rgba(5,7,12,.82)'; g.beginPath(); g.roundRect(0, 0, 1400, 200, 18); g.fill();
    g.fillStyle = '#f0a340'; g.font = '600 34px Segoe UI, sans-serif'; g.fillText(quem, 36, 54);
    g.fillStyle = '#efe9df'; g.font = '400 38px Segoe UI, sans-serif';
    let l = '', y = 108; for (const w of texto.split(' ')) { const t = l ? l + ' ' + w : w; if (g.measureText(t).width > 1330 && l) { g.fillText(l, 36, y); y += 46; l = w; } else l = t; } g.fillText(l, 36, y);
    ltex.needsUpdate = true; legAte = performance.now() + seg * 1000;
    const vr = renderer.xr.isPresenting; leg.visible = vr;          // no VR: legenda no espaco; no computador: faixa HTML
    const hl = document.getElementById('legendaHTML'); if (hl && !vr) { hl.innerHTML = `<b>${quem}:</b> ${texto}`; hl.hidden = false; }
  }
  function falar(quem, texto, voz = 'f') {
    const seg = Math.max(3, texto.length / 14);
    legenda(quem, texto, seg);
    const npc = npcPorNome(quem), p = vozSintetica(texto, voz);
    if (npc) { const f = { sintetica: true, ate: performance.now() + (p ? seg + 6 : seg * .8) * 1000 }; npc.userData.fala = f; p?.then(() => { if (npc.userData.fala === f) npc.userData.fala = null; }); }
    return p;
  }
  const npcPorNome = quem => ({ 'Vítima': npcs.vitima, 'Agressor': npcs.agressor, 'Vizinho': npcs.vizinho, 'Criança': npcs.crianca })[String(quem).split(' ')[0]];
  // voz do navegador (pt-BR). Retorna uma promessa que termina quando a fala acaba (ou null sem voz)
  function vozSintetica(texto, voz = 'f') {
    if (S.voz === false || !('speechSynthesis' in window)) return null;
    const vs = speechSynthesis.getVoices().filter(v => v.lang && v.lang.replace('_', '-').startsWith('pt'));
    if (!vs.length) return null;
    try {
      const u = new SpeechSynthesisUtterance(texto); u.lang = 'pt-BR';
      const br = vs.filter(v => /BR/i.test(v.lang)), lista = br.length ? br : vs;
      const fem = lista.filter(v => /francisca|thalita|maria|luciana|feminin|female|google/i.test(v.name));
      const mas = lista.filter(v => /antonio|daniel|ricardo|masculin|male/i.test(v.name) && !/female/i.test(v.name));
      u.voice = (voz === 'm' ? mas[0] : fem[0]) || lista[(voz === 'm' ? 1 : 0) % lista.length];
      u.pitch = voz === 'c' ? 1.6 : voz === 'm' ? .85 : 1.05; u.rate = voz === 'm' ? 1 : .95;
      return new Promise(r => { u.onend = u.onerror = () => r(); speechSynthesis.speak(u); });
    } catch (e) { return null; }
  }
  if ('speechSynthesis' in window) speechSynthesis.getVoices();      // o Chrome carrega a lista de vozes na primeira chamada

  /* fala com audio gravado (06_Audio/brutos/<audio>.mp3) ou voz sintetica, legenda e gesto; termina quando a fala acaba */
  const espera = ms => new Promise(r => setTimeout(r, ms));
  async function dizer(npc, quem, linha, voz = 'f') {
    const { texto, gesto, audio } = linha;
    const som = window.__som, gravado = audio && som?.tem(audio);
    const seg = gravado ? som.duracao(audio) : Math.max(2.5, texto.length / 13);
    legenda(quem, texto, seg + .6);
    if (npc && gesto) animar(npc, gesto, seg + 1.5);
    if (gravado) {
      const med = som.tocar(audio, npc ? npc.position.clone().setY(1.55) : null, true);
      const f = npc && { medidor: typeof med === 'function' ? med : null, sintetica: typeof med !== 'function', ate: performance.now() + seg * 1000 };
      if (npc) npc.userData.fala = f;
      await espera(seg * 1000 + 350); if (npc?.userData.fala === f) npc.userData.fala = null; return;
    }
    const p = vozSintetica(texto, voz);
    const f = npc && { sintetica: true, ate: performance.now() + (p ? seg + 6 : seg) * 1000 };
    if (npc) npc.userData.fala = f;
    await (p ? Promise.race([p, espera(seg * 1000 + 6000)]) : espera(seg * 1000));
    if (npc?.userData.fala === f) npc.userData.fala = null;
    await espera(350);
  }
  let narrando = false;
  async function relatoVitima() {
    const v = npcs.vitima; if (!v || narrando) return;
    narrando = true;
    try {
      const R = CEN.relato_vitima || {};
      const linhas = (['minimiza', 'retrata'].includes(S.variacao.vitima) && R.minimiza) ? R.minimiza : (R.completo || []);
      for (const l of linhas) if (cond(l.condicao)) await dizer(v, 'Vítima', l, 'f');
      animar(v, 'parada');
    } finally { narrando = false; }
  }

  /* som simples (batida na porta, obturador da camera) */
  let AC = null;
  function som(tipo) {
    const arq = { porta: 'batida_porta', foto: 'obturador', fita: 'fita_zebrada', algemas: 'algemas', radio: 'radio_bip' }[tipo];
    if (arq && window.__som?.tocar(arq)) return;           // usa o arquivo de 06_Audio se existir
    if (tipo === 'fita' || tipo === 'algemas' || tipo === 'radio') return;
    try {
      AC = AC || new AudioContext();
      const n = AC.createBufferSource(), b = AC.createBuffer(1, AC.sampleRate * .25, AC.sampleRate), d = b.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.exp(-i / (tipo === 'porta' ? 900 : 300));
      n.buffer = b; const gn = AC.createGain(); gn.gain.value = tipo === 'porta' ? .9 : .4; n.connect(gn).connect(AC.destination); n.start();
      if (tipo === 'porta') { for (const t of [.35, .7]) { const n2 = AC.createBufferSource(); n2.buffer = b; n2.connect(gn); n2.start(AC.currentTime + t); } }
    } catch (e) { }
  }

  /* ================= personagens provisorios (fase 3 troca por modelos reais) ================= */
  function boneco(nome, corRoupa, altura = 1.7, corCalca = 0x2b2f3a) {
    const g = new THREE.Group(), s = altura / 1.7; g.name = 'NPC_' + nome;
    const pele = new THREE.MeshStandardMaterial({ color: 0xb98a68, roughness: .7 });
    const roupa = new THREE.MeshStandardMaterial({ color: corRoupa, roughness: .85 });
    const calca = new THREE.MeshStandardMaterial({ color: corCalca, roughness: .85 });
    const cap = (r, l, m, x, y, z, rz = 0) => { const k = new THREE.Mesh(new THREE.CapsuleGeometry(r * s, l * s, 4, 12), m); k.position.set(x * s, y * s, z * s); k.rotation.z = rz; g.add(k); return k; };
    cap(.075, .7, calca, -.1, .44, 0); cap(.075, .7, calca, .1, .44, 0);
    cap(.17, .4, roupa, 0, 1.14, 0);
    cap(.055, .52, roupa, -.25, 1.1, 0, .1); const bracoD = cap(.055, .52, roupa, .25, 1.1, 0, -.1);
    cap(.05, .05, pele, 0, 1.47, 0);
    const cab = new THREE.Mesh(new THREE.SphereGeometry(.115 * s, 24, 16), pele); cab.position.set(0, 1.62 * s, 0); g.add(cab);
    const hit = new THREE.Mesh(new THREE.CylinderGeometry(.38 * s, .38 * s, altura, 8), new THREE.MeshBasicMaterial({ visible: false }));
    hit.position.y = altura / 2; hit.userData.npc = nome; g.add(hit);
    const ecv = document.createElement('canvas'); ecv.width = 256; ecv.height = 64; const eg = ecv.getContext('2d');
    eg.fillStyle = 'rgba(5,7,12,.7)'; eg.beginPath(); eg.roundRect(0, 0, 256, 64, 14); eg.fill();
    eg.fillStyle = '#efe9df'; eg.font = '600 32px Segoe UI, sans-serif'; eg.textAlign = 'center'; eg.fillText(nome, 128, 44);
    const et = new THREE.CanvasTexture(ecv); et.colorSpace = THREE.SRGBColorSpace;
    const rotulo = new THREE.Sprite(new THREE.SpriteMaterial({ map: et, depthTest: true, transparent: true, fog: false }));
    rotulo.scale.set(.5, .125, 1); rotulo.position.y = altura + .25; rotulo.renderOrder = 999; g.add(rotulo);
    g.userData = { hit, bracoD, rotulo, nome };
    return g;
  }
  /* personagens reais (Rocketbox, licenca MIT) convertidos para personagens/*.glb; se faltar, usa o boneco */
  const modelos = {};
  const modelosProntos = fetch('personagens/manifest.json').then(r => r.ok ? r.json() : {}).then(man => {
    const gl = new GLTFLoader();
    return Promise.all(Object.entries(man).map(([papel, info]) => gl.loadAsync(info.arquivo).then(g => { modelos[papel] = g; }).catch(() => { })));
  }).catch(() => { });
  // modo exploracao (antes de iniciar o treinamento): personagens, rastros e a faca do quintal ja aparecem na cena
  modelosProntos.then(() => {
    if (S.ativo || !Object.keys(modelos).length) return;
    S.variacao = { agressor: 'escondido', crianca: 'quarto', vizinho: 'presente', faca: 'quintal', vitima: 'colabora', reacao: 'rende_se', fuga: 'nao' };
    criarNPCs(); montarQuintal();
  });
  function personagem(papel, nome, cor, altura, calca) {
    const base = modelos[papel];
    if (!base) return boneco(nome, cor, altura, calca);
    const g = new THREE.Group(); g.name = 'NPC_' + nome;
    const m = SkeletonUtils.clone(base.scene);
    m.traverse(o => { if (o.isMesh) o.frustumCulled = false; });
    g.add(m);
    const mixer = new THREE.AnimationMixer(m), acoes = {};
    for (const clip of base.animations) acoes[clip.name.replace(/\.\d+$/, '')] = mixer.clipAction(clip);
    const parada = acoes.parada || Object.values(acoes)[0];
    if (parada) { parada.play(); parada.time = Math.random() * parada.getClip().duration; }
    const box = new THREE.Box3().setFromObject(m), alt = Math.max(box.max.y - box.min.y, altura * .6);
    const hit = new THREE.Mesh(new THREE.CylinderGeometry(.38, .38, alt, 8), new THREE.MeshBasicMaterial({ visible: false }));
    hit.position.y = alt / 2; hit.userData.npc = nome; g.add(hit);
    const ecv = document.createElement('canvas'); ecv.width = 256; ecv.height = 64; const eg = ecv.getContext('2d');
    eg.fillStyle = 'rgba(5,7,12,.7)'; eg.beginPath(); eg.roundRect(0, 0, 256, 64, 14); eg.fill();
    eg.fillStyle = '#efe9df'; eg.font = '600 32px Segoe UI, sans-serif'; eg.textAlign = 'center'; eg.fillText(nome, 128, 44);
    const et = new THREE.CanvasTexture(ecv); et.colorSpace = THREE.SRGBColorSpace;
    const rotulo = new THREE.Sprite(new THREE.SpriteMaterial({ map: et, depthTest: true, transparent: true, fog: false }));
    rotulo.scale.set(.5, .125, 1); rotulo.position.y = alt + .25; g.add(rotulo);
    const mao = m.getObjectByName('Bip01_R_Hand') || m.getObjectByName('Bip01 R Hand');
    g.userData = { hit, rotulo, nome, mixer, acoes, atual: parada, modelo: m, bracoD: mao || g, real: true, rosto: montarRosto(m) };
    return g;
  }
  /* rosto: boca acompanha o volume da fala e as palpebras piscam (ossos faciais do esqueleto adulto) */
  function montarRosto(m) {
    const jaw = m.getObjectByName('Bip01_MJaw');
    if (!jaw) return null;                                   // crianca (Bip02) tem eixos diferentes: fica sem
    const palp = [['Bip01_REyeBlinkTop', -1.25], ['Bip01_LEyeBlinkTop', -1.25], ['Bip01_REyeBlinkBottom', .35], ['Bip01_LEyeBlinkBottom', .35]]
      .map(([n, k]) => { const b = m.getObjectByName(n); return b && { b, base: b.position.clone(), k }; }).filter(Boolean);
    return { jaw, jawBase: jaw.quaternion.clone(), escrito: null, boca: 0, palp, piscaIni: 0, proxPisca: performance.now() + 1000 + Math.random() * 3000 };
  }
  const QZ = new THREE.Quaternion(), EIXO_Z = new THREE.Vector3(0, 0, 1);
  function animarRosto(n, dt, agora) {
    const r = n.userData.rosto; if (!r) return;
    let alvo = 0; const f = n.userData.fala;
    if (f) {
      if (agora > f.ate) n.userData.fala = null;
      else if (f.medidor) alvo = Math.pow(Math.min(1, Math.max(0, f.medidor() - .06) / .75), .8);   // silencio ~0,04; fala 0,3 a 0,8
      else if (f.sintetica) alvo = Math.max(0, .3 + .45 * Math.sin(agora * .019) * Math.sin(agora * .0063 + 1.7));   // ritmo de silabas
    }
    r.boca += (alvo - r.boca) * Math.min(1, dt * (alvo > r.boca ? 28 : 14));
    const q = r.jaw.quaternion;
    if (r.escrito && q.equals(r.escrito)) q.copy(r.jawBase);   // a animacao nao mexeu na mandibula neste quadro
    q.multiply(QZ.setFromAxisAngle(EIXO_Z, r.boca * .17)); r.escrito = q.clone();     // ate ~10 graus de abertura
    // piscar: ~150 ms fechando e abrindo, a cada 2,5 a 6,5 s
    if (agora > r.proxPisca) { r.piscaIni = agora; r.proxPisca = agora + 2500 + Math.random() * 4000; }
    const t = (agora - r.piscaIni) / 75, k = t < 1 ? t : t < 2 ? 2 - t : 0;
    for (const p of r.palp) { p.b.position.copy(p.base); p.b.position.x += p.k * k; }
  }
  function animar(npc, nome, segundos = 6) {
    const u = npc?.userData; if (!u?.real || !u.acoes[nome]) return;
    const nova = u.acoes[nome];
    if (u.atual !== nova) { nova.reset().play(); u.atual?.crossFadeTo(nova, .5, false); u.atual = nova; }
    clearTimeout(u.volta);
    if (nome !== 'parada' && u.acoes.parada) u.volta = setTimeout(() => animar(npc, 'parada'), segundos * 1000);
  }
  const npcs = {};
  function criarNPCs() {
    Object.values(npcs).forEach(n => scene.remove(n)); for (const k in npcs) delete npcs[k];
    const v = personagem('vitima', 'Vítima', 0x9b2d3a, 1.64, 0x3a3f55); v.position.set(-3.1, 0, 0.7); v.rotation.y = 2.4;
    if (!v.userData.real) {
      const lesao = new THREE.MeshStandardMaterial({ color: 0x6a1010, roughness: .5 });
      const l1 = new THREE.Mesh(new THREE.SphereGeometry(.018, 8, 6), lesao); l1.position.set(.03, 1.52, .1); v.add(l1);
      const l2 = new THREE.Mesh(new THREE.SphereGeometry(.03, 8, 6), lesao); l2.position.set(.27, 1.05, .05); v.add(l2);
    }
    npcs.vitima = v; scene.add(v);
    const va = S.variacao.agressor;
    if (va !== 'fugiu') {
      const a = personagem('agressor', 'Agressor', 0x3d4045, 1.78);
      if (va === 'escondido') { a.position.set(10.5, 0, -1.25); a.rotation.y = -.6; }   // agachado na grama ao lado da casa, atras do arbusto
      else { a.position.set(3.6, 0, -1.6); a.rotation.y = -2.2; }
      npcs.agressor = a; scene.add(a);
      if (va === 'escondido') animar(a, a.userData.acoes?.escondido ? 'escondido' : 'nervoso', 1e6);
      else if (va === 'agressivo') animar(a, 'parada'); else animar(a, 'nervoso', 1e6);
      if (S.variacao.faca === 'na_mao') {
        S.faca = faca();
        if (a.userData.real) { S.faca.scale.setScalar(100); S.faca.rotation.set(0, Math.PI / 2, 0); }   // a mao do Rocketbox esta em centimetros
        else S.faca.position.set(0, -.3, 0);
        a.userData.bracoD.add(S.faca);
      }
    }
    if (S.variacao.faca === 'pia') { S.faca = faca(); S.faca.position.set(5.55, .935, -0.9); S.faca.rotation.y = .4; scene.add(S.faca); }
    const vc = S.variacao.crianca;
    const c = personagem('crianca', 'Criança', 0x2a6f97, 1.15, 0x1e2a44);
    if (vc === 'quarto') c.position.set(-6.55, 0, 2.05); else if (vc === 'corredor') c.position.set(-5.5, 0, 2.6); else c.position.set(5.0, 0, 14.9);
    c.rotation.y = 1.4; npcs.crianca = c; scene.add(c);
    if (S.variacao.vizinho === 'presente' || vc === 'vizinha') {
      const n = personagem('vizinho', 'Vizinho', 0x3d6b3a, 1.72); n.position.set(4.2, .1, 14.7); n.rotation.y = Math.PI; npcs.vizinho = n; scene.add(n);
    }
  }
  function faca() {
    const g = new THREE.Group(); g.name = 'Faca';
    const lam = new THREE.Mesh(new THREE.BoxGeometry(.03, .004, .2), new THREE.MeshStandardMaterial({ color: 0xc8ccd0, metalness: 1, roughness: .25 }));
    lam.position.z = .14; g.add(lam);
    const cabo = new THREE.Mesh(new THREE.BoxGeometry(.025, .02, .11), new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: .6 }));
    g.add(cabo);
    const hit = new THREE.Mesh(new THREE.SphereGeometry(.25, 8, 6), new THREE.MeshBasicMaterial({ visible: false })); hit.userData.faca = true; g.add(hit);
    g.userData.hit = hit; return g;
  }

  /* vestigios: esferas invisiveis nas posicoes do cenario */
  const vestHits = [];
  for (const vv of CEN.vestigios) {
    if (vv.id === 'V12' || vv.externo) continue;    // a faca e um objeto proprio; externos: montarQuintal()
    const h = new THREE.Mesh(new THREE.SphereGeometry(.4, 10, 8), new THREE.MeshBasicMaterial({ visible: false }));
    h.position.fromArray(vv.pos); h.userData.vest = vv; scene.add(h); vestHits.push(h);
  }
  /* porta da varanda (vidro de correr aberto) e portao */
  const porta = new THREE.Mesh(new THREE.BoxGeometry(2.0, 2.4, .6), new THREE.MeshBasicMaterial({ visible: false }));
  porta.position.set(0, 1.2, 4.2); porta.userData.porta = true; scene.add(porta);

  /* marcadores (placas numeradas) e fita zebrada */
  function placa(pos) {
    S.placas++;
    const cv = document.createElement('canvas'); cv.width = 128; cv.height = 128; const g = cv.getContext('2d');
    g.fillStyle = '#f2c200'; g.fillRect(0, 0, 128, 128); g.fillStyle = '#111'; g.font = '800 84px Segoe UI, sans-serif'; g.textAlign = 'center'; g.fillText(String(S.placas), 64, 96);
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace;
    const m = new THREE.MeshStandardMaterial({ map: t, roughness: .6, side: THREE.DoubleSide });
    const gr = new THREE.Group();
    for (const s of [-1, 1]) { const p = new THREE.Mesh(new THREE.PlaneGeometry(.1, .12), m); p.position.set(0, .055, s * .025); p.rotation.x = s * .4; gr.add(p); }
    gr.position.copy(pos); camera.getWorldPosition(V); gr.lookAt(V.x, pos.y, V.z); scene.add(gr);
    return gr;
  }
  const fitaTex = (() => { const cv = document.createElement('canvas'); cv.width = 256; cv.height = 32; const g = cv.getContext('2d');
    for (let i = 0; i < 8; i++) { g.fillStyle = i % 2 ? '#111' : '#f2c200'; g.beginPath(); g.moveTo(i * 32, 0); g.lineTo(i * 32 + 32, 0); g.lineTo(i * 32 + 16, 32); g.lineTo(i * 32 - 16, 32); g.fill(); }
    const t = new THREE.CanvasTexture(cv); t.wrapS = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t; })();
  function fita(a, b) {
    const d = b.clone().sub(a), L = Math.hypot(d.x, d.z); if (L < .3) return;
    const t = fitaTex.clone(); t.needsUpdate = true; t.repeat.set(L / .5, 1);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(L, .07), new THREE.MeshStandardMaterial({ map: t, side: THREE.DoubleSide, roughness: .6 }));
    m.position.set((a.x + b.x) / 2, Math.max(a.y, b.y) + .95, (a.z + b.z) / 2); m.rotation.y = -Math.atan2(d.z, d.x); scene.add(m);
    for (const p of [a, b]) { const c = new THREE.Mesh(new THREE.ConeGeometry(.12, .95, 12), new THREE.MeshStandardMaterial({ color: 0xff6a00, roughness: .6 })); c.position.set(p.x, p.y + .475, p.z); scene.add(c); }
    S.fitas.push({ a: a.toArray(), b: b.toArray() });
    const dentro = p => p.x > -6 && p.x < 6 && p.z > -4 && p.z < 4;
    som('fita');
    if (S.fitas.filter(f => dentro(new THREE.Vector3(...f.a)) || dentro(new THREE.Vector3(...f.b))).length >= 2) registrar('isolar_local');
  }

  /* ================= ferramentas e menus ================= */
  const FERR = { mao: 'Mão', camera: 'Câmera fotográfica', placa: 'Placa numerada', fita: 'Fita zebrada', algemas: 'Algemas' };
  function abrirFerramentas() {
    fecharPaineis();
    menu.mostrar({
      tag: 'Ferramentas', titulo: 'Equipamento', texto: `Em uso: ${FERR[S.ferramenta]} · Luvas: ${S.luvas ? 'calçadas' : 'não'}`,
      botoes: [
        ...Object.entries(FERR).map(([k, n]) => ({ label: (S.ferramenta === k ? '● ' : '') + n, acao: () => { S.ferramenta = k; S.fitaInicio = null; menu.esconder(); status(); } })),
        { label: S.luvas ? 'Tirar as luvas' : 'Calçar luvas', acao: () => { S.luvas = !S.luvas; menu.esconder(); status(); } },
        { label: 'Lanterna (liga/desliga)', acao: () => { ctx.setLanterna(!ctx.lanternaLigada(), camera); menu.esconder(); } },
        { label: 'Rádio', acao: abrirRadio },
        { label: 'Checklist / tablet', acao: abrirChecklist },
        { label: 'Encerrar ocorrência e ver relatório', cor: 'rgba(240,80,64,.22)', acao: encerrar },
        { label: 'Fechar', acao: () => menu.esconder() }
      ]
    });
  }
  function abrirRadio() {
    fecharPaineis();
    menu.mostrar({
      tag: 'Rádio', titulo: 'Comunicar com o COPOM', texto: CEN.chamada_190.despacho,
      botoes: [...CEN.radio.map(r => ({ label: r.texto, acao: () => radio(r.id) })), { label: 'Fechar', acao: () => menu.esconder() }]
    });
  }
  function radio(id) {
    menu.esconder();
    const fala = {
      radio_chegada: ['Guarnição', 'COPOM, guarnição no local da ocorrência.'], acionar_samu: ['Guarnição', 'COPOM, solicito SAMU no local: vítima com lesões no rosto e no braço.'],
      solicitar_pericia: ['Guarnição', 'COPOM, solicito perícia no local. Local isolado.'], pedir_apoio: ['Guarnição', 'COPOM, solicito apoio de outra guarnição.'],
      caracteristicas_agressor: ['Guarnição', 'COPOM, autor evadiu-se pelos fundos: homem, cerca de 35 anos, camisa polo listrada, bermuda bege, mão direita machucada.']
    }[id];
    if (id === 'pedir_apoio') S.apoio = true;
    som('radio'); window.__som?.tocar('radio_chiado');
    if (fala) falar(fala[0], fala[1], 'm');
    if (id === 'radio_chegada' && S.entrou) return;    // so vale antes de entrar
    if (id === 'caracteristicas_agressor') {
      if (S.variacao.agressor === 'fugiu' || S.variacao.fuga === 'sim') registrar('informar_fuga_radio');
      return setTimeout(() => legenda('COPOM', 'Copiado. Viaturas da área informadas.', 2.5), 1800);
    }
    registrar(id);
    setTimeout(() => legenda('COPOM', 'Copiado. Prossiga.', 2.5), 1800);
  }
  function abrirChecklist() {
    fecharPaineis();
    const linhas = CEN.fases.map(f => `${f.nome}: ` + (f.acoes || []).filter(a => cond(a.condicao)).map(a => (S.feitos.has(a.id) ? '✓ ' : '· ') + a.texto).join(' | ')).join('\n');
    menu.mostrar({ tag: 'Tablet', titulo: 'Checklist da ocorrência', texto: linhas + `\n\nTempo: ${fmt(tempo())}`, botoes: [{ label: 'Fechar', acao: () => menu.esconder() }], longe: 1.3 });
  }

  /* ================= dialogos ================= */
  function falarDialogo(quem, opcoes, titulo) {
    fecharPaineis();
    dialogo.mostrar({ tag: quem, titulo, botoes: [...opcoes, { label: 'Encerrar conversa', acao: () => dialogo.esconder() }] });
  }
  const dlg = id => CEN.dialogos[id];
  function aplicarEfeito(op) {
    const e = op.efeito || {};
    if (op.acao) registrar(op.acao);
    else if (e.pontos < 0) penalidade(e.pontos, op.fala, op.feedback);
    if (e.falha_grave) registrar(e.falha_grave);
  }
  function conversarVitima() {
    animar(npcs.vitima, 'falando');
    if (!S.contatoVitima) {
      return falarDialogo('Vítima', dlg('vitima_primeiro_contato').map(op => ({
        label: op.fala, acao: () => {
          S.contatoVitima = true; aplicarEfeito(op); dialogo.esconder();
          falar('Vítima', op.acao ? 'Na boca… e o meu braço. Ele me empurrou contra a mesa.' : 'Eu… não sei. Eu não fiz nada.', 'f');
        }
      })), 'Primeiro contato');
    }
    const ops = [
      ['A senhora pode me contar o que aconteceu? No seu tempo.', '__relato', null],
      ['A senhora já sofreu ameaças antes? Ele tem arma? Vocês estão se separando?', 'info_risco', 'Ele já me ameaçou outras vezes. Eu ia embora hoje… a mala está lá.'],
      ['Onde está a sua filha?', null, S.variacao.crianca === 'vizinha' ? 'Ela correu para a casa da vizinha.' : 'No quarto… ela está escondida.'],
      ['Vamos proteger a sua filha. O Conselho Tutelar será comunicado.', 'proteger_crianca', 'Tá… obrigada.'],
      ['A senhora tem direito a medida protetiva, Defensoria, DEAM e ao Ligue 180.', 'informar_direitos', 'Eu não sabia que podia pedir isso.'],
      ['Vamos levar a senhora ao hospital e ao IML para o exame.', 'iml_saude', 'Tá bom.'],
      ['Se houver risco, levamos a senhora e a sua filha para um local seguro.', 'local_seguro', 'Minha mãe mora em Niterói.'],
      ['Vamos até a delegacia (DEAM) registrar a ocorrência.', 'conducao_deam', null],
      ['Se precisar, acompanhamos a senhora para pegar seus pertences.', 'retirada_pertences', 'Os documentos da minha filha estão no quarto.'],
      ['Conte de novo, desde o início, tudo o que aconteceu.', '__repete', 'De novo? Eu já falei…']
    ];
    falarDialogo('Vítima', ops.map(([fala, id, resp]) => ({
      label: fala, acao: () => {
        dialogo.esconder();
        if (id === '__relato') return relatoVitima();
        if (id === '__repete') { penalidade(-2, 'Repetir perguntas sobre o mesmo fato', 'Evitar perguntas repetidas (LMP art. 10-A).'); }
        else if (id) registrar(id);
        if (id === 'conducao_deam' && ['minimiza', 'retrata'].includes(S.variacao.vitima) && !S.desistenciaResolvida) return vitimaDesiste();
        if (resp) falar('Vítima', resp, 'f');
      }
    })), 'Atendimento à vítima');
  }
  function vitimaDesiste() {
    animar(npcs.vitima, 'estressada', 8);
    falar('Vítima', S.variacao.vitima === 'minimiza' ? 'Não precisa disso tudo… eu caí, foi só uma discussão.' : 'Eu não quero dar queixa. Ele é o pai da minha filha.', 'f');
    setTimeout(() => falarDialogo('Vítima', dlg('vitima_desiste').map(op => ({
      label: op.fala, acao: () => { S.desistenciaResolvida = true; aplicarEfeito(op); dialogo.esconder(); if (op.acao) falar('Vítima', 'Tá… eu vou.', 'f'); }
    })), 'A vítima quer desistir'), 1500);
  }
  function conversarAgressor() {
    animar(npcs.agressor, 'falando');
    const ops = dlg('agressor_minimiza').map(op => ({
      label: op.fala, acao: () => {
        aplicarEfeito(op); dialogo.esconder();
        if (op.acao === 'separar_partes') { S.separado = true; npcs.agressor.position.set(-2.5, 0, 6.2); animar(npcs.agressor, 'nervoso', 9999); falar('Agressor', 'Tá bom, tá bom… mas foi só uma briga.', 'm'); }
        else falar('Agressor', 'Você não manda na minha casa!', 'm');
      }
    }));
    ops.push({ label: 'O senhor está preso em flagrante por lesão corporal contra a mulher.', acao: () => {
      registrar('flagrante'); dialogo.esconder(); falar('Agressor', 'Isso é um absurdo…', 'm');
      S.rendido = true; dica('Clique nele de novo para a busca pessoal, os direitos e a condução à viatura.');
    } });
    if (S.variacao.medida_protetiva === 'vigente') ops.push({ label: 'Há medida protetiva contra o senhor e ela foi descumprida.', acao: () => { registrar('descumprimento_mpu'); dialogo.esconder(); } });
    falarDialogo('Agressor', ops, S.variacao.agressor === 'agressivo' ? 'O agressor está alterado' : 'O agressor tenta minimizar');
    falar('Agressor', S.variacao.agressor === 'agressivo' ? 'Sai da minha casa! Isso não é assunto de polícia!' : 'Foi só uma briga de casal, pode ir embora.', 'm');
  }
  function algemar() {
    if (!npcs.agressor || S.algemado) return;
    falarDialogo('Algemas', [
      ['Resistência à prisão', true], ['Fundado receio de fuga', true], ['Perigo à integridade da vítima ou da guarnição', true], ['Por precaução, sem motivo específico', false]
    ].map(([m, ok]) => ({
      label: m, acao: () => {
        dialogo.esconder(); S.algemado = true; som('algemas');
        if (ok) registrar('algemas_justificadas', m); else penalidade(-4, 'Algemas sem justificativa', 'Uso de algemas exige justificativa por escrito (STF SV 11).');
        legenda('Guarnição', 'Algemado. Motivo registrado: ' + m, 3);
      }
    })), 'Justificativa do uso de algemas (SV 11)');
  }
  function conversarVizinho() {
    animar(npcs.vizinho, 'falando');
    falarDialogo('Vizinho', [{
      label: 'Boa noite. O senhor viu ou ouviu algo? Pode me passar nome e documento?', acao: () => {
        registrar('qualificar_testemunha'); dialogo.esconder();
        falar('Vizinho', CEN.personagens.vizinho.fala, 'm'); animar(npcs.vizinho, 'falando', 7);
      }
    }], 'Testemunha');
  }
  function conversarCrianca() {
    falarDialogo('Criança', [{ label: 'Oi, eu sou da polícia. Você está segura. Vamos ficar com a sua mãe?', acao: () => { dialogo.esconder(); falar('Criança', 'O papai gritou muito… a mamãe tá machucada?', 'c'); } }], 'Criança assustada');
  }
  function interagirPorta() {
    const ops = [];
    if (!S.identificado) ops.push({ label: 'Bater na porta e se identificar: "Polícia Militar!"', acao: () => {
      dialogo.esconder(); som('porta'); S.identificado = true; registrar('identificar_se');
      camera.getWorldPosition(V); if (Math.abs(V.x) > .6) registrar('aproximacao_segura');
      falar('Guarnição', 'Polícia Militar!', 'm');
      setTimeout(() => { S.socorroOuvido = true; falar('Vítima (lá dentro)', 'Socorro! Me ajuda, por favor!', 'f'); }, 2200);
    } });
    if (S.socorroOuvido && !S.feitos.has('entrada_legitima')) ops.push({ label: 'Entrar: pedido de socorro / flagrante (CF art. 5º, XI)', acao: () => { dialogo.esconder(); registrar('entrada_legitima'); } });
    if (!ops.length) return false;
    falarDialogo('Porta', ops, 'Acesso à residência');
    return true;
  }

  /* ================= uso das ferramentas ================= */
  function usar(ray) {
    for (const p of paineis) if (p.clique(ray)) return true;
    if (!S.ativo) return explorar(ray);
    // personagens
    const npcHits = Object.values(npcs).map(n => n.userData.hit);
    const hn = ray.intersectObjects(npcHits, false)[0];
    if (hn && hn.distance < 4) {
      const n = hn.object.userData.npc;
      if (n === 'Agressor' && (S.variacao.agressor === 'escondido' || S.rendido)) return abordagemClique(), true;
      if (S.ferramenta === 'algemas' && n === 'Agressor') return algemar(), true;
      ({ 'Vítima': conversarVitima, 'Agressor': conversarAgressor, 'Vizinho': conversarVizinho, 'Criança': conversarCrianca })[n]?.();
      return true;
    }
    // faca (risco imediato)
    if (S.faca && S.faca.parent) {
      const hf = ray.intersectObject(S.faca.userData.hit, false)[0];
      if (hf && hf.distance < 3) {
        if (S.ferramenta === 'mao') {
          registrar('neutralizar_faca', S.luvas ? 'com luvas' : 'sem luvas');
          S.faca.parent.remove(S.faca);
          legenda('Guarnição', 'Faca afastada do alcance e registrada' + (S.luvas ? '.' : ' (atenção: sem luvas).'), 3);
          return true;
        }
        if (S.ferramenta === 'camera') { foto({ id: 'V12', nome: 'Faca' }); return true; }
      }
    }
    // porta
    const hp = ray.intersectObject(porta, false)[0];
    if (hp && hp.distance < 3.5 && !S.feitos.has('entrada_legitima') && interagirPorta()) return true;
    // vestigios
    const hv = ray.intersectObjects(vestHits, false)[0];
    if (hv && hv.distance < 4) {
      const vv = hv.object.userData.vest;
      if (S.ferramenta === 'camera') { foto(vv); return true; }
      if (S.ferramenta === 'placa') { placa(hv.object.position.clone().setY(hv.point.y < .3 ? 0 : hv.object.position.y - .35)); reconhecer(vv); return true; }
      if (S.ferramenta === 'mao') { vv.id === 'V15' ? facaQuintal(vv, hv.object) : tocar(vv); return true; }
    }
    // chao: placa ou fita
    if (S.ferramenta === 'placa' || S.ferramenta === 'fita') {
      const hc = ray.intersectObjects(ctx.colisao(), false)[0];
      if (hc && hc.distance < 8) {
        if (S.ferramenta === 'placa') {
          placa(hc.point.clone());
          const perto = vestHits.find(h => Math.hypot(h.position.x - hc.point.x, h.position.z - hc.point.z) < 1.2);
          if (perto) reconhecer(perto.userData.vest);
        } else if (!S.fitaInicio) { S.fitaInicio = hc.point.clone(); legenda('Fita', 'Primeiro ponto marcado. Clique no segundo ponto.', 2.5); }
        else { fita(S.fitaInicio, hc.point.clone()); S.fitaInicio = null; }
        return true;
      }
    }
    if (S.ferramenta === 'camera') { som('foto'); return true; }
    return false;
  }
  function reconhecer(vv) {
    if (S.vestReconhecidos.has(vv.id)) return;
    S.vestReconhecidos.add(vv.id); legenda('Vestígio', `${vv.id} · ${vv.nome} — reconhecido`, 2.5); status();
  }
  function foto(vv) {
    som('foto'); flash.intensity = 30; setTimeout(() => flash.intensity = 0, 90);
    S.vestFotografados.add(vv.id); reconhecer(vv);
    S.log.push({ t: +tempo().toFixed(1), id: 'foto', extra: vv.id });
    if (S.vestFotografados.size >= 6) registrar('fotografar_vestigios');
  }
  function tocar(vv) {
    falarDialogo('Vestígio', [
      { label: 'Apenas observar e descrever (não tocar)', acao: () => { dialogo.esconder(); reconhecer(vv); } },
      { label: 'Mover com a mão para ver melhor', acao: () => { dialogo.esconder(); registrar('tocar_vestigio', vv.id); } },
      { label: 'Recolher e arrumar o objeto', acao: () => { dialogo.esconder(); registrar('alterar_local', vv.id); } }
    ], `${vv.nome}`);
  }
  const flash = new THREE.PointLight(0xffffff, 0, 6, 2); camera.add(flash);

  /* ================= fluxo ================= */
  function sortear() {
    const forc = Object.fromEntries((new URLSearchParams(location.search).get('v') || '').split(',').filter(Boolean).map(p => p.split(':')));
    S.variacao = {};
    for (const [k, ops] of Object.entries(CEN.variacoes)) S.variacao[k] = forc[k] && ops.includes(forc[k]) ? forc[k] : ops[Math.floor(Math.random() * ops.length)];
    const v = S.variacao, fora = v.agressor === 'escondido' || v.agressor === 'fugiu';
    if (!forc.faca) {
      if (fora && v.faca === 'na_mao') v.faca = 'quintal';            // ele largou a faca ao fugir
      if (!fora && v.faca === 'quintal') v.faca = 'pia';
    }
    v.fuga = 'nao';
  }
  function aviso() {
    fecharPaineis();
    menu.mostrar({
      tag: 'Treinamento', titulo: 'Ocorrência de violência doméstica',
      texto: 'Aviso de conteúdo: esta simulação trata de violência doméstica. Pause quando precisar.\n\n' +
        'Computador: clique para usar a ferramenta e falar com as pessoas · T ferramentas · R rádio · K checklist.\n' +
        'Quest: gatilho usa/clica · botão Y ou B abre as ferramentas · grip liga a lanterna.',
      botoes: [
        { label: 'Modo treino (objetivos e dicas na tela)', acao: () => { S.modo = 'treino'; comecar(); } },
        { label: 'Modo avaliação (sem dicas)', acao: () => { S.modo = 'avaliacao'; comecar(); } },
        { label: S.voz === false ? 'Voz sintética: desligada (só legendas)' : 'Voz sintética: ligada', acao: () => { S.voz = S.voz === false; aviso(); } },
        { label: 'Cancelar', acao: () => menu.esconder() }
      ]
    });
  }
  async function comecar() {
    fecharPaineis();
    // espera os personagens terminarem de baixar (~19 MB; ate 30 s em rede lenta, depois usa os bonecos)
    let carregou = false;
    modelosProntos.then(() => { carregou = true; });
    await new Promise(r => setTimeout(r, 0));
    if (!carregou) {
      menu.mostrar({ tag: 'Treinamento', titulo: 'Carregando personagens…', texto: 'Aguarde alguns segundos.', botoes: [] });
      await Promise.race([modelosProntos, new Promise(r => setTimeout(r, 30000))]);
      menu.esconder();
    }
    sortear();
    Object.assign(S, { ativo: true, inicio: performance.now(), fim: 0, feitos: new Map(), erros: [], graves: [], log: [], ferramenta: 'mao', luvas: false,
      identificado: false, socorroOuvido: false, entrou: false, contatoVitima: false, separado: false, algemado: false, desistenciaResolvida: false,
      criancaAchada: false, vestReconhecidos: new Set(), vestFotografados: new Set(), placas: 0, fitas: [], fitaInicio: null, tempoFachada: 0, tempoDentro: 0, avisoAgressor: false,
      apoio: false, agressorAchado: false, rendido: false, abordando: false });
    if (ctx.hotspots) ctx.hotspots.visible = false;      // sem marcadores (no modo treino os objetivos guiam)
    criarNPCs();
    montarQuintal();
    if (S.variacao.crianca !== 'vizinha') window.__som?.iniciarTreino();   // choro baixo de onde a crianca esta
    rig.position.set(1.0, 0, 18.4); ctx.setYaw(0);
    const lin = CEN.chamada_190.legenda; let t = 0;
    lin.forEach(([q, txt]) => { setTimeout(() => falar('Ligação 190 · ' + q, txt, q === 'Atendente' ? 'm' : 'f'), t); t += Math.max(2600, txt.length * 70); });
    setTimeout(() => falar('Rádio · COPOM', CEN.chamada_190.despacho, 'm'), t + 400);
    if (S.modo === 'treino') setTimeout(() => dica('Os objetivos aparecem no canto da tela. Comece informando a chegada pelo rádio (R ou menu).'), t + 4000);
    status();
  }
  function encerrar() {
    if (!S.ativo) return;
    if (!S.feitos.has('acionar_samu')) registrar('sem_socorro', 'vítima com lesão visível (lábio e braço)');
    if (S.contatoVitima && !S.erros.some(e => /Repetir perguntas/.test(e.texto))) registrar('sem_repeticao');   // credito por NAO repetir
    if (S.variacao.agressor === 'escondido' && !S.agressorAchado) S.erros.push({ id: 'agressor_nao_achado', texto: 'Agressor escondido no quintal não foi localizado', pontos: -5, feedback: 'A vítima indicou que ele estava por perto: faça a busca nos fundos com a lanterna.', t: tempo() });
    S.fim = performance.now(); S.ativo = false; fecharPaineis(); status();
    const rel = relatorio(); mostrarRelatorio(rel);
  }
  function relatorio() {
    let possiveis = 0, obtidos = 0; const fases = [];
    for (const f of CEN.fases) {
      let fp = 0, fo = 0; const itens = [];
      for (const a of f.acoes || []) {
        if (!cond(a.condicao)) continue;
        if (a.id === 'reconhecer_vestigios') { const n = Math.min(a.max, S.vestReconhecidos.size); fp += a.max; fo += n * a.pontos_por_item; itens.push({ texto: `${a.texto} (${n}/${a.max})`, ok: n > 0, pontos: n }); continue; }
        fp += a.pontos; const ok = S.feitos.has(a.id); if (ok) fo += a.pontos; itens.push({ texto: a.texto, ok, pontos: ok ? a.pontos : 0, base: a.base });
      }
      possiveis += fp; obtidos += fo; fases.push({ nome: f.nome, obtidos: fo, possiveis: fp, itens });
    }
    const desc = S.erros.reduce((s, e) => s + e.pontos, 0) + S.graves.reduce((s, e) => s + e.pontos, 0);
    const nota = Math.max(0, Math.round((obtidos + desc) / possiveis * 100));
    const aprovado = nota >= CEN.aprovacao.pontos_minimos && !(CEN.aprovacao.sem_falha_grave && S.graves.length);
    return { cenario: CEN.id, data: new Date().toISOString(), tempo: fmt(tempo()), modo: S.modo, variacao: S.variacao, nota, aprovado, obtidos, descontos: desc, possiveis,
      fases, erros: S.erros, falhas_graves: S.graves, fotos: [...S.vestFotografados], vestigios_reconhecidos: [...S.vestReconhecidos], placas: S.placas, fitas: S.fitas.length, linha_do_tempo: S.log };
  }
  function mostrarRelatorio(r) {
    const txtFases = r.fases.map(f => `${f.nome}: ${f.obtidos}/${f.possiveis}`).join('\n');
    const txtErros = [...r.falhas_graves.map(g => '⚠ FALHA GRAVE: ' + g.texto), ...r.erros.map(e => `• ${e.texto} (${e.pontos})${e.feedback ? ' — ' + e.feedback : ''}`)].join('\n') || 'Nenhum erro registrado.';
    menu.mostrar({
      tag: 'Relatório', titulo: `Nota ${r.nota}/100 · ${r.aprovado ? 'APROVADO' : 'NÃO APROVADO'}`,
      texto: `Tempo: ${r.tempo} · Vestígios reconhecidos: ${r.vestigios_reconhecidos.length} · Fotos: ${r.fotos.length}\n\n${txtFases}\n\n${txtErros}`,
      botoes: [{ label: 'Nova ocorrência (outras variações)', acao: () => { fecharPaineis(); aviso(); } }, { label: 'Fechar', acao: () => menu.esconder() }], longe: 1.4
    });
    const el = document.getElementById('relatorioHTML');
    if (el) {
      el.innerHTML = `<h2>Nota ${r.nota}/100 — ${r.aprovado ? 'aprovado' : 'não aprovado'}</h2>
        <p>Tempo ${r.tempo} · variação: ${Object.entries(r.variacao).map(([k, v]) => k + ' = ' + v).join(', ')}</p>
        ${r.fases.map(f => `<h3>${f.nome} <small>${f.obtidos}/${f.possiveis}</small></h3><ul>${f.itens.map(i => `<li class="${i.ok ? 'ok' : 'nao'}">${i.ok ? '✓' : '✗'} ${i.texto}${i.base ? ` <em>(${i.base})</em>` : ''}</li>`).join('')}</ul>`).join('')}
        <h3>Erros e falhas graves</h3><ul>${txtErros.split('\n').map(l => `<li>${l}</li>`).join('')}</ul>
        <p><button type="button" id="baixarRel">Baixar relatório (JSON)</button> <button type="button" id="fecharRel">Fechar</button></p>`;
      el.hidden = false;
      document.getElementById('baixarRel').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' })); a.download = `relatorio_${r.cenario}_${Date.now()}.json`; a.click(); };
      document.getElementById('fecharRel').onclick = () => el.hidden = true;
    }
  }

  /* ================= modo exploracao: clicar nos personagens antes de iniciar o treinamento ================= */
  function explorar(ray) {
    const hv = ray.intersectObjects(vestHits.filter(h => h.userData.vest.externo), false)[0];
    if (hv && hv.distance < 5) { legenda('Vestígio', hv.object.userData.vest.nome + ' — no treinamento: não tocar, marcar, fotografar e preservar.', 5); return true; }
    const hn = ray.intersectObjects(Object.values(npcs).map(n => n.userData.hit), false)[0];
    if (!hn || hn.distance > 5) return false;
    const n = hn.object.userData.npc;
    if (n === 'Vítima') relatoVitima();
    else if (n === 'Agressor') dizer(npcs.agressor, 'Agressor', { texto: 'O que vocês tão fazendo aqui? Eu não fiz nada, ela que tá inventando.', gesto: 'falando' }, 'm')
      .then(() => legenda('Modo exploração', 'Para abordar e prender o agressor, clique em "Iniciar treinamento" (no Quest: botão Y ou B).', 6));
    else if (n === 'Vizinho') dizer(npcs.vizinho, 'Vizinho', { texto: 'Eu ouvi gritaria e barulho de coisa quebrando. Já é a segunda vez esse mês.', gesto: 'falando' }, 'm');
    else if (n === 'Criança') dizer(npcs.crianca, 'Criança', { texto: 'Moço… cadê a minha mãe?' }, 'c');
    return true;
  }

  /* ================= missao do quintal: rastros, faca descartada, abordagem do agressor escondido ================= */
  function decal(desenhar, w, h, larg, alt) {
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h; desenhar(cv.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace;
    return new THREE.Mesh(new THREE.PlaneGeometry(larg, alt), new THREE.MeshStandardMaterial({ map: t, transparent: true, alphaTest: .05,
      depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, roughness: .85 }));
  }
  const pegada = (g, w, h) => {             // sola de tenis com barro
    g.fillStyle = 'rgba(58,40,24,.85)';
    g.beginPath(); g.ellipse(w / 2, h * .32, w * .36, h * .27, 0, 0, 7); g.fill();
    g.beginPath(); g.ellipse(w / 2, h * .78, w * .28, h * .17, 0, 0, 7); g.fill();
    g.globalCompositeOperation = 'destination-out'; g.fillStyle = 'rgba(0,0,0,.55)';
    for (let y = h * .1; y < h * .95; y += h * .07) g.fillRect(w * .2, y, w * .6, h * .022);
    g.globalCompositeOperation = 'source-over';
  };
  const maoSangue = (g, w, h) => {          // mao apoiada na parede, arrastada para baixo
    g.fillStyle = 'rgba(92,8,8,.88)';
    g.beginPath(); g.ellipse(w * .5, h * .55, w * .2, h * .16, 0, 0, 7); g.fill();
    [[.3, .32, .05, .14, -.35], [.42, .24, .05, .17, -.12], [.55, .23, .05, .17, .08], [.67, .29, .045, .14, .3], [.74, .5, .045, .1, .9]]
      .forEach(([x, y, rx, ry, a]) => { g.beginPath(); g.ellipse(w * x, h * y, w * rx, h * ry, a, 0, 7); g.fill(); });
    g.fillStyle = 'rgba(92,8,8,.55)';
    for (let i = 0; i < 5; i++) g.fillRect(w * (.36 + i * .06), h * .65, w * .025, h * (.15 + Math.random() * .2));
  };
  function montarQuintal() {
    for (const o of S.quintal) { scene.remove(o); const i = vestHits.indexOf(o); if (i >= 0) vestHits.splice(i, 1); }
    S.quintal = [];
    for (const vv of CEN.vestigios) {
      if (!vv.externo || !cond(vv.condicao)) continue;
      const [x, y, z] = vv.pos;
      if (vv.externo === 'pegadas') {          // da beira da varanda em direcao ao quintal lateral
        for (let i = 0; i < 7; i++) {
          const m = decal(pegada, 64, 160, .11, .28), lado = i % 2 ? .09 : -.09;
          m.rotation.x = -Math.PI / 2; m.rotation.z = -Math.PI / 2 + .35;
          m.position.set(x - 1.4 + i * .42, .006, z + .5 - i * .15 + lado); scene.add(m); S.quintal.push(m);
        }
      } else if (vv.externo === 'mao_sangue') {
        const m = decal(maoSangue, 128, 160, .2, .25); m.rotation.y = Math.PI / 2; m.position.set(6.212, y, z); scene.add(m); S.quintal.push(m);
      } else if (vv.externo === 'faca') {
        const f = faca(); f.remove(f.userData.hit); f.position.set(x, y, z); f.rotation.y = 2.2; scene.add(f); S.quintal.push(f); vv._obj = f;
      }
      const h = new THREE.Mesh(new THREE.SphereGeometry(.45, 10, 8), new THREE.MeshBasicMaterial({ visible: false }));
      h.position.set(x, Math.max(y, .3), z); h.userData.vest = vv; scene.add(h); vestHits.push(h); S.quintal.push(h);
    }
  }
  function dica(texto) { if (S.modo === 'treino' && S.ativo) legenda('Dica do instrutor', texto, 6); }
  function opcoesJSON(lista, aoEscolher) {
    return lista.map(op => ({ label: op.fala, acao: () => {
      dialogo.esconder();
      if (op.acao) registrar(op.acao);
      if (op.tambem) registrar(op.tambem);
      if (op.erro) registrar(op.erro);
      if (op.falha) registrar(op.falha);
      if (op.feedback && S.modo === 'treino') setTimeout(() => legenda('Instrutor', op.feedback, 7), 2500);
      aoEscolher?.(op);
    } }));
  }
  function descobrirAgressor() {
    if (S.agressorAchado) return;
    S.agressorAchado = true; registrar('localizar_agressor');
    if (S.apoio) registrar('apoio_antes_abordagem');
    const ag = npcs.agressor; if (!ag) return;
    ag.userData.semVirar = false;
    dica('Ele está agachado atrás do arbusto. Mantenha distância, identifique-se e dê ordens claras.');
    abrirAbordagem();
  }
  function abrirAbordagem() {
    S.abordando = true;
    falarDialogo('Abordagem', opcoesJSON(CEN.abordagem.inicio, () => reagir()), 'Suspeito escondido no quintal');
  }
  function abordagemClique() {
    if (S.rendido && !npcs.agressor.userData.destino) return S.ferramenta === 'algemas' ? algemar() : abrirPrisao();
    if (!S.agressorAchado) return descobrirAgressor();
    if (!S.abordando && !S.rendido && !npcs.agressor.userData.destino) abrirAbordagem();
  }
  function reagir() {
    const ag = npcs.agressor, r = S.variacao.reacao, fala = CEN.abordagem.reacao_fala[r];
    S.abordando = false;
    dizer(ag, 'Agressor', { texto: fala }, 'm');
    if (r === 'rende_se') return render(false);
    if (r === 'foge') {
      animar(ag, 'correndo', 1e6); ag.userData.vel = 4.2;
      ag.userData.rota = [new THREE.Vector3(13.6, 0, -6.5), new THREE.Vector3(15.2, 0, -10.8)];
      ag.userData.aoChegar = () => {                          // chegou ao muro: espera a decisao do policial
        if (S.rendido) return;
        animar(ag, 'nervoso', 1e6); ag.userData.noMuro = true;
        if (ag.userData.decisao === 'foge') pularMuro();
      };
      setTimeout(() => falarDialogo('Fuga', opcoesJSON(CEN.abordagem.fuga, op => {
        if (op.resultado === 'rende') { ag.userData.rota = []; ag.userData.destino = null; render(); }
        else { ag.userData.decisao = 'foge'; if (ag.userData.noMuro) pularMuro(); }
      }), 'Ele está correndo para o muro dos fundos!'), 700);
    } else if (r === 'volta_casa') {
      animar(ag, 'andando', 1e6); ag.userData.vel = 1.9;
      ag.userData.rota = [new THREE.Vector3(8.3, 0, 3.4), new THREE.Vector3(6.9, 0, 5.4)];
      ag.userData.aoChegar = () => { if (!S.rendido) render(); };
      setTimeout(() => falarDialogo('Risco à vítima', opcoesJSON(CEN.abordagem.retorno, op => {
        if (op.resultado === 'rende') { ag.userData.rota = []; ag.userData.destino = null; render(); }
      }), 'Ele está voltando para a casa, onde está a vítima!'), 700);
    }
  }
  function render(falarDeNovo = true) {
    const ag = npcs.agressor; S.rendido = true;
    ag.userData.destino = null; ag.userData.rota = [];
    animar(ag, ag.userData.acoes?.rendido ? 'rendido' : 'nervoso', 1e6);
    if (falarDeNovo) setTimeout(() => dizer(ag, 'Agressor', { texto: 'Tá bom! Tô parado… não atira!' }, 'm'), 600);
    dica('Ele se rendeu: clique nele para a busca pessoal e a voz de prisão. Algemas só com justificativa (STF SV 11).');
  }
  function pularMuro() {
    const ag = npcs.agressor, ini = ag.position.clone(), t0 = performance.now();
    S.variacao.fuga = 'sim'; ag.userData.semVirar = true;
    const passo = () => {
      const k = Math.min(1, (performance.now() - t0) / 1300);
      ag.position.set(ini.x, Math.sin(k * Math.PI) * 1.4 + k * .3, ini.z - k * 1.4);
      if (k < 1) requestAnimationFrame(passo); else ag.visible = false;
    };
    passo();
    legenda('Guarnição', 'O suspeito pulou o muro dos fundos e fugiu.', 4);
    dica('Informe pelo rádio a fuga e as características do agressor (R → "Informar fuga e características").');
  }
  function abrirPrisao() {
    const ops = opcoesJSON(CEN.abordagem.prisao, op => {
      if (op.resposta) setTimeout(() => legenda(op.acao === 'busca_pessoal' ? 'Busca pessoal' : 'Agressor', op.resposta, 5), 300);
      if (op.acao === 'conduzir_viatura') conduzir();
    });
    if (!S.algemado) ops.splice(1, 0, { label: 'Algemar (justificar o motivo)', acao: () => { dialogo.esconder(); algemar(); } });
    falarDialogo('Prisão', ops, 'Procedimento com o detido');
  }
  function conduzir() {
    const ag = npcs.agressor; S.separado = true; registrar('separar_partes');
    animar(ag, 'andando', 1e6); ag.userData.vel = 1.3; ag.userData.semVirar = true;
    const p = ag.position, dentro = Math.abs(p.x) < 6.2 && Math.abs(p.z) < 4.3;
    ag.userData.rota = [...(dentro ? [new THREE.Vector3(p.x * .3, 0, 2.6), new THREE.Vector3(0, 0, 5.6)] : [new THREE.Vector3(8.6, 0, 7.6)]),   // de dentro: pela porta da frente
      new THREE.Vector3(1.0, 0, 12.4), new THREE.Vector3(1.0, 0, 14.6), new THREE.Vector3(3.0, 0, 16.4)];   // pelo portao
    ag.userData.aoChegar = () => { animar(ag, 'parada', 1e6); ag.rotation.y = Math.PI / 2; };
    legenda('Guarnição', 'Conduzindo o preso até a viatura.', 3);
  }
  function moverNPC(n, dt) {
    const u = n.userData;
    if (!u.destino && u.rota?.length) u.destino = u.rota.shift();
    if (!u.destino) return;
    V2.copy(u.destino).sub(n.position); V2.y = 0;
    const L = V2.length();
    if (L < .12) { u.destino = null; if (!u.rota?.length) { const cb = u.aoChegar; u.aoChegar = null; cb?.(); } return; }
    n.position.addScaledVector(V2.normalize(), Math.min(L, (u.vel || 1.4) * dt));
    const alvo = Math.atan2(V2.x, V2.z); let d = alvo - n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
    n.rotation.y += d * Math.min(1, dt * 8);
    camera.getWorldDirection(V2);                         // V2 volta a ser a direcao do olhar (usada no quadro)
  }
  function facaQuintal(vv, hit) {
    falarDialogo('Vestígio', opcoesJSON(CEN.abordagem.faca_quintal, op => {
      reconhecer(vv);
      if (op.precisa_luvas || op.erro) {                     // recolhida: sai do lugar
        if (op.precisa_luvas && !S.luvas) registrar('faca_sem_luva');
        if (vv._obj) scene.remove(vv._obj);
        legenda('Guarnição', op.precisa_luvas ? 'Faca recolhida' + (S.luvas ? ', embalada e lacrada.' : ' sem luvas.') : 'Faca recolhida com a mão.', 3);
      }
    }), vv.nome);
  }

  /* ================= objetivos (modo treino) ================= */
  function objetivos() {
    const f = id => S.feitos.has(id), v = S.variacao, L = [];
    if (!S.entrou && !f('radio_chegada')) L.push('Informe a chegada pelo rádio');
    if (!f('identificar_se') && !S.entrou) L.push('Bata na porta e identifique-se');
    else if (S.socorroOuvido && !f('entrada_legitima')) L.push('Pedido de socorro: entre na casa');
    if (S.entrou) {
      if (!S.contatoVitima) L.push('Fale com a vítima');
      if (!f('acionar_samu')) L.push('Acione o SAMU pelo rádio');
      if (v.crianca !== 'vizinha' && !S.criancaAchada) L.push('Localize a criança');
      if (v.agressor === 'escondido' || v.agressor === 'fugiu') {
        if (!f('buscar_quintal')) L.push('Ele saiu da casa: faça a busca no quintal com a lanterna');
        else if (v.agressor === 'escondido' && !S.agressorAchado) L.push('Procure o agressor no quintal lateral');
      } else if (!S.separado) L.push('Separe o agressor da vítima');
      if (S.rendido && !f('busca_pessoal')) L.push('Faça a busca pessoal no detido');
      if (S.rendido && !f('informar_direitos_preso')) L.push('Dê voz de prisão e informe os direitos');
      if (S.rendido && !f('conduzir_viatura')) L.push('Conduza o preso à viatura');
      if ((v.agressor === 'fugiu' || v.fuga === 'sim') && !f('informar_fuga_radio')) L.push('Informe a fuga e as características pelo rádio');
      if (v.faca === 'quintal' && !f('preservar_faca_quintal') && S.vestReconhecidos.has('V15') === false && f('buscar_quintal')) L.push('Procure armas ou objetos descartados no quintal');
      if (S.vestReconhecidos.size < 6) L.push(`Reconheça e fotografe os vestígios (${S.vestReconhecidos.size}/6)`);
      if (!f('isolar_local')) L.push('Isole a sala e o jantar com a fita');
      if (!f('solicitar_pericia')) L.push('Solicite a perícia pelo rádio');
      if (!f('informar_direitos')) L.push('Informe à vítima os direitos e os serviços');
      if (!f('conducao_deam')) L.push('Combine a condução à DEAM');
    }
    if (!L.length) L.push('Tudo feito: encerre a ocorrência (menu → Encerrar)');
    return L.slice(0, 4);
  }
  const ocv = document.createElement('canvas'); ocv.width = 640; ocv.height = 300;
  const otex = new THREE.CanvasTexture(ocv); otex.colorSpace = THREE.SRGBColorSpace;
  const objVR = new THREE.Mesh(new THREE.PlaneGeometry(.42, .42 * 300 / 640), new THREE.MeshBasicMaterial({ map: otex, transparent: true, depthTest: false, toneMapped: false, fog: false }));
  objVR.position.set(-.32, .2, -.9); objVR.renderOrder = 1002; objVR.visible = false; camera.add(objVR);
  const objHTML = document.createElement('div'); objHTML.id = 'objetivosHTML'; objHTML.hidden = true;
  Object.assign(objHTML.style, { position: 'fixed', right: '16px', top: '16px', maxWidth: 'min(340px, calc(100vw - 32px))', zIndex: 6,
    background: 'rgba(11,14,22,.88)', color: '#efe9df', border: '1px solid rgba(240,163,64,.5)', borderRadius: '6px', padding: '10px 14px',
    font: '13px/1.45 "Segoe UI", system-ui, sans-serif', pointerEvents: 'none' });
  document.body.appendChild(objHTML);
  let ultimoObj = '';
  function mostrarObjetivos() {
    const on = S.ativo && S.modo === 'treino', L = on ? objetivos() : [], chave = on + L.join('|') + renderer.xr.isPresenting;
    if (chave === ultimoObj) return; ultimoObj = chave;
    objHTML.hidden = !on || renderer.xr.isPresenting; objVR.visible = on && renderer.xr.isPresenting;
    if (!on) return;
    objHTML.innerHTML = '<b style="color:#f0a340;font:600 11px Consolas,monospace;letter-spacing:.08em">OBJETIVOS</b><br>' + L.map(t => '▸ ' + t).join('<br>');
    const g = ocv.getContext('2d'); g.clearRect(0, 0, 640, 300);
    g.fillStyle = 'rgba(11,14,22,.85)'; g.beginPath(); g.roundRect(0, 0, 640, 300, 16); g.fill();
    g.fillStyle = '#f0a340'; g.font = '600 22px Consolas, monospace'; g.fillText('OBJETIVOS', 22, 38);
    g.fillStyle = '#efe9df'; g.font = '400 25px Segoe UI, sans-serif';
    let y = 80; for (const t of L) { let l = '▸ ', first = true; for (const w of t.split(' ')) { const tt = l + w + ' '; if (g.measureText(tt).width > 600 && l.trim()) { g.fillText(l, 22, y); y += 30; l = '  '; first = false; } else l = tt; } g.fillText(l, 22, y); y += 38; if (y > 290) break; }
    otex.needsUpdate = true;
  }

  /* ================= status (computador) ================= */
  function status() {
    const el = document.getElementById('statusTrein'); if (!el) return;
    el.hidden = !S.ativo;
    el.innerHTML = `<b>Ocorrência em andamento</b> · ${fmt(tempo())}${S.modo === 'treino' ? ' · modo treino' : ''}<br>Ferramenta: ${FERR[S.ferramenta]} · Luvas: ${S.luvas ? 'sim' : 'não'} · Vestígios: ${S.vestReconhecidos.size}`;
    mostrarObjetivos();
  }

  /* ================= verificacoes automaticas por quadro ================= */
  let ultimo = performance.now();
  function quadro() {
    const agora = performance.now(), dt = (agora - ultimo) / 1000; ultimo = agora;
    if (agora > legAte) { leg.visible = false; const hl = document.getElementById('legendaHTML'); if (hl && !hl.hidden) hl.hidden = true; }
    camera.getWorldPosition(V); camera.getWorldDirection(V2);
    for (const n of Object.values(npcs)) {
      n.userData.rotulo.visible = V.distanceTo(n.position) < 7;
      n.userData.mixer?.update(dt);
      animarRosto(n, dt, agora);
      moverNPC(n, dt);
      // vira o corpo para o policial quando ele chega perto (o modelo olha para +Z)
      if (n.userData.real && n !== npcs.crianca && !n.userData.destino && !n.userData.semVirar && V.distanceTo(n.position) < 3.5) {
        const alvo = Math.atan2(V.x - n.position.x, V.z - n.position.z);
        let d = alvo - n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
        n.rotation.y += d * Math.min(1, dt * 2.5);
      }
    }
    if (!S.ativo) return;
    const dentroCasa = V.x > -6 && V.x < 6 && V.z > -4 && V.z < 4;
    if (dentroCasa && !S.entrou) { S.entrou = true; if (!S.identificado) registrar('entrada_sem_identificacao'); }
    if (V.z > 13.8 && V2.z < -.6) { S.tempoFachada += dt; if (S.tempoFachada > 3) registrar('observar_fachada'); }
    if (dentroCasa && ctx.lanternaLigada()) registrar('uso_lanterna');
    if (npcs.crianca && !S.criancaAchada && V.distanceTo(npcs.crianca.position.clone().setY(V.y)) < 3) { S.criancaAchada = true; registrar('localizar_crianca'); window.__som?.pararChoro(); falar('Criança', 'Moço… cadê a minha mãe?', 'c'); }
    if (dentroCasa) S.tempoDentro += dt;
    // busca no quintal lateral/fundos com a lanterna
    if (V.x > 6.5 && V.x < 16.8 && V.z < 4.2 && V.z > -11.3 && ctx.lanternaLigada()) registrar('buscar_quintal');
    const esc = npcs.agressor;
    if (esc && S.variacao.agressor === 'escondido' && !S.agressorAchado) {
      const d = V.distanceTo(esc.position.clone().setY(.6));
      const olhando = V2.dot(esc.position.clone().setY(.6).sub(V).normalize()) > .93;
      if (d < 4 || (d < 10 && olhando && ctx.lanternaLigada())) descobrirAgressor();
    }
    const ag = npcs.agressor;
    if (ag && !S.separado && !S.algemado && S.variacao.agressor !== 'escondido') {
      if (S.tempoDentro > 90 && !S.avisoAgressor) { S.avisoAgressor = true; falar('Agressor', 'Fala alguma coisa pra eles e eu te pego depois!', 'm'); }
      if (S.tempoDentro > 90) ag.position.lerp(new THREE.Vector3(-2.4, 0, 0.9), .01);
      if (S.tempoDentro > 120) registrar('vitima_com_agressor');
    }
    if (Math.floor(agora / 1000) !== Math.floor((agora - dt * 1000) / 1000)) status();
  }

  /* ================= entradas ================= */
  addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    if (e.code === 'KeyT') S.ativo ? abrirFerramentas() : aviso();
    if (e.code === 'KeyR' && S.ativo) abrirRadio();
    if (e.code === 'KeyK' && S.ativo) abrirChecklist();
  });
  const bt = document.createElement('button'); bt.type = 'button'; bt.textContent = 'Iniciar treinamento'; bt.id = 'bTrein';
  bt.onclick = aviso; document.getElementById('acoes')?.prepend(bt);

  window.__trein = {
    clique: ray => usar(ray),
    apontar, painelAberto: () => paineis.some(p => p.mesh.visible),
    gatilho: (ray) => usar(ray),
    menu: () => S.ativo ? abrirFerramentas() : aviso(),
    quadro, estado: S, relatorio,
    // acesso para testes automatizados e para o instrutor
    _t: { comecar, radio, conversarVitima, conversarAgressor, algemar, conversarVizinho, interagirPorta, foto, reconhecer, fita, tocar, encerrar,
      botoes: () => (dialogo.mesh.visible ? dialogo : menu).botoes, npcs, vest: CEN.vestigios, descobrirAgressor, abordagemClique, objetivos, facaQuintal }
  };
  return window.__trein;
}
