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
    tempoFachada: 0, tempoDentro: 0, avisoAgressor: false, faca: null
  };
  const acoes = {};
  CEN.fases.forEach(f => {
    (f.acoes || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'acao' });
    (f.erros || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'erro' });
    (f.falhas_graves || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'grave' });
  });
  const cond = c => {
    if (!c) return true;
    const m = c.match(/variacao\.(\w+)\s*(==|!=)\s*'([^']*)'/);
    if (!m) return true;
    return m[2] === '==' ? S.variacao[m[1]] === m[3] : S.variacao[m[1]] !== m[3];
  };
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
    esconder() { this.mesh.visible = false; }
    clique(ray) {
      if (!this.mesh.visible) return false;
      const h = ray.intersectObject(this.mesh, false)[0]; if (!h) return false;
      const py = (1 - h.uv.y) * this.H, b = this.botoes.find(b => py >= b.y0 && py <= b.y1);
      if (b && b.acao) b.acao();
      return true;
    }
  }
  const menu = new Painel(1.1), dialogo = new Painel(1.15);
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
    legenda(quem, texto, Math.max(3, texto.length / 14));
    if (!S.voz || !('speechSynthesis' in window)) return;
    try {
      const u = new SpeechSynthesisUtterance(texto); u.lang = 'pt-BR';
      const vs = speechSynthesis.getVoices().filter(v => v.lang && v.lang.startsWith('pt'));
      if (vs.length) u.voice = vs[(voz === 'm' ? 1 : 0) % vs.length];
      u.pitch = voz === 'c' ? 1.6 : voz === 'm' ? .8 : 1.1; u.rate = 1.0; speechSynthesis.speak(u);
    } catch (e) { }
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
  // modo exploracao (antes de iniciar o treinamento): personagens ja aparecem na cena, sem faca
  modelosProntos.then(() => {
    if (S.ativo || !Object.keys(modelos).length) return;
    S.variacao = { agressor: 'calmo', crianca: 'quarto', vizinho: 'presente', faca: 'nenhuma' };
    criarNPCs();
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
    g.userData = { hit, rotulo, nome, mixer, acoes, atual: parada, modelo: m, bracoD: mao || g, real: true };
    return g;
  }
  function animar(npc, nome, segundos = 6) {
    const u = npc?.userData; if (!u?.real || !u.acoes[nome] || u.atual === u.acoes[nome]) return;
    const nova = u.acoes[nome]; nova.reset().play(); u.atual?.crossFadeTo(nova, .4, false); u.atual = nova;
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
      if (va === 'escondido') a.position.set(-5.3, 0, 5.9); else a.position.set(3.6, 0, -1.6);
      a.rotation.y = -2.2; npcs.agressor = a; scene.add(a);
      if (va === 'agressivo') animar(a, 'parada'); else animar(a, 'nervoso', 9999);
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
    if (vv.id === 'V12') continue;    // a faca e um objeto proprio
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
      caracteristicas_agressor: ['Guarnição', 'COPOM, autor evadiu-se: homem, cerca de 35 anos, camiseta cinza.']
    }[id];
    som('radio'); window.__som?.tocar('radio_chiado');
    if (fala) falar(fala[0], fala[1], 'm');
    if (id === 'radio_chegada' && S.entrou) return;    // so vale antes de entrar
    if (id === 'caracteristicas_agressor' && S.variacao.agressor !== 'fugiu') return;
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
    ops.push({ label: 'O senhor está preso em flagrante por lesão corporal contra a mulher.', acao: () => { registrar('flagrante'); dialogo.esconder(); falar('Agressor', 'Isso é um absurdo…', 'm'); } });
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
        falar('Vizinho', CEN.personagens.vizinho.informacao + ' Meu nome é Carlos, moro no 150.', 'm');
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
    if (!S.ativo) return false;
    for (const p of paineis) if (p.clique(ray)) return true;
    // personagens
    const npcHits = Object.values(npcs).map(n => n.userData.hit);
    const hn = ray.intersectObjects(npcHits, false)[0];
    if (hn && hn.distance < 4) {
      const n = hn.object.userData.npc;
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
      if (S.ferramenta === 'mao') { tocar(vv); return true; }
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
    for (const [k, ops] of Object.entries(CEN.variacoes)) S.variacao[k] = forc[k] && ops.includes(forc[k]) ? forc[k] : ops[Math.floor(Math.random() * ops.length)];
  }
  function aviso() {
    fecharPaineis();
    menu.mostrar({
      tag: 'Treinamento', titulo: 'Ocorrência de violência doméstica',
      texto: 'Aviso de conteúdo: esta simulação trata de violência doméstica. Pause quando precisar.\n\n' +
        'Computador: clique para usar a ferramenta e falar com as pessoas · T ferramentas · R rádio · K checklist.\n' +
        'Quest: gatilho usa/clica · botão Y ou B abre as ferramentas · grip liga a lanterna.',
      botoes: [
        { label: 'Começar (com voz sintética)', acao: () => { S.voz = true; comecar(); } },
        { label: 'Começar (só legendas)', acao: () => { S.voz = false; comecar(); } },
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
      criancaAchada: false, vestReconhecidos: new Set(), vestFotografados: new Set(), placas: 0, fitas: [], fitaInicio: null, tempoFachada: 0, tempoDentro: 0, avisoAgressor: false });
    if (ctx.hotspots) ctx.hotspots.visible = false;      // modo avaliacao: sem marcadores
    criarNPCs();
    if (S.variacao.crianca !== 'vizinha') window.__som?.iniciarTreino();   // choro baixo de onde a crianca esta
    rig.position.set(1.0, 0, 18.4); ctx.setYaw(0);
    const lin = CEN.chamada_190.legenda; let t = 0;
    lin.forEach(([q, txt]) => { setTimeout(() => falar('Ligação 190 · ' + q, txt, q === 'Atendente' ? 'm' : 'f'), t); t += Math.max(2600, txt.length * 70); });
    setTimeout(() => falar('Rádio · COPOM', CEN.chamada_190.despacho, 'm'), t + 400);
    status();
  }
  function encerrar() {
    if (!S.ativo) return;
    if (!S.feitos.has('acionar_samu')) registrar('sem_socorro', 'vítima com lesão visível (lábio e braço)');
    if (S.contatoVitima && !S.erros.some(e => /Repetir perguntas/.test(e.texto))) registrar('sem_repeticao');   // credito por NAO repetir
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
    return { cenario: CEN.id, data: new Date().toISOString(), tempo: fmt(tempo()), variacao: S.variacao, nota, aprovado, obtidos, descontos: desc, possiveis,
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

  /* ================= status (computador) ================= */
  function status() {
    const el = document.getElementById('statusTrein'); if (!el) return;
    el.hidden = !S.ativo;
    el.innerHTML = `<b>Ocorrência em andamento</b> · ${fmt(tempo())}<br>Ferramenta: ${FERR[S.ferramenta]} · Luvas: ${S.luvas ? 'sim' : 'não'} · Vestígios: ${S.vestReconhecidos.size}`;
  }

  /* ================= verificacoes automaticas por quadro ================= */
  let ultimo = performance.now();
  function quadro() {
    const agora = performance.now(), dt = (agora - ultimo) / 1000; ultimo = agora;
    if (agora > legAte) { leg.visible = false; const hl = document.getElementById('legendaHTML'); if (hl && !hl.hidden) hl.hidden = true; }
    if (!S.ativo) { for (const n of Object.values(npcs)) n.userData.mixer?.update(dt); return; }
    camera.getWorldPosition(V); camera.getWorldDirection(V2);
    const dentroCasa = V.x > -6 && V.x < 6 && V.z > -4 && V.z < 4;
    if (dentroCasa && !S.entrou) { S.entrou = true; if (!S.identificado) registrar('entrada_sem_identificacao'); }
    if (V.z > 13.8 && V2.z < -.6) { S.tempoFachada += dt; if (S.tempoFachada > 3) registrar('observar_fachada'); }
    if (dentroCasa && ctx.lanternaLigada()) registrar('uso_lanterna');
    if (npcs.crianca && !S.criancaAchada && V.distanceTo(npcs.crianca.position.clone().setY(V.y)) < 3) { S.criancaAchada = true; registrar('localizar_crianca'); window.__som?.pararChoro(); falar('Criança', 'Moço… cadê a minha mãe?', 'c'); }
    if (dentroCasa) S.tempoDentro += dt;
    const ag = npcs.agressor;
    if (ag && !S.separado && !S.algemado && S.variacao.agressor !== 'escondido') {
      if (S.tempoDentro > 90 && !S.avisoAgressor) { S.avisoAgressor = true; falar('Agressor', 'Fala alguma coisa pra eles e eu te pego depois!', 'm'); }
      if (S.tempoDentro > 90) ag.position.lerp(new THREE.Vector3(-2.4, 0, 0.9), .01);
      if (S.tempoDentro > 120) registrar('vitima_com_agressor');
    }
    for (const n of Object.values(npcs)) {
      n.userData.rotulo.visible = V.distanceTo(n.position) < 7;
      n.userData.mixer?.update(dt);
      // vira o rosto para o policial quando ele chega perto (modelo do Rocketbox olha para +Z)
      if (n.userData.real && n !== npcs.crianca && V.distanceTo(n.position) < 3.5) {
        const alvo = Math.atan2(V.x - n.position.x, V.z - n.position.z);
        let d = alvo - n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
        n.rotation.y += d * Math.min(1, dt * 2.5);
      }
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
    gatilho: (ray) => usar(ray),
    menu: () => S.ativo ? abrirFerramentas() : aviso(),
    quadro, estado: S, relatorio,
    // acesso para testes automatizados e para o instrutor
    _t: { comecar, radio, conversarVitima, conversarAgressor, algemar, conversarVizinho, interagirPorta, foto, reconhecer, fita, tocar, encerrar,
      botoes: () => (dialogo.mesh.visible ? dialogo : menu).botoes, npcs, vest: CEN.vestigios }
  };
  return window.__trein;
}
