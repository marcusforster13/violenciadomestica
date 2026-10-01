/*
  A Casa em Silencio - sons do visualizador.
  Le audio/manifest.json (gerado pelo pipeline a partir de 06_Audio/brutos) e toca so o que existir.
  - ambientes: tocam em loop, com volume diferente dentro e fora da casa
  - posicionais: saem de um ponto da cena (geladeira, TV, viatura), ficam mais altos quanto mais perto
  - eventos: tocados pelo treinamento (porta, camera, fita, algemas, radio, passos)
  O navegador so libera som depois de um clique/tecla/entrada no VR; o modulo espera isso.
*/
import * as THREE from 'three';

// posicoes em coordenadas da cena web (Y para cima)
const DEF = {
  amb_rua_noite:       { tipo: 'ambiente', fora: .55, dentro: .18 },
  amb_casa_interior:   { tipo: 'ambiente', fora: 0, dentro: .35 },
  geladeira_zumbido:   { tipo: 'posicional', pos: [5.45, 1.0, 2.4], vol: .9, ref: .7, rolloff: 1.6 },
  tv_abafada:          { tipo: 'posicional', pos: [-5.6, .9, -1.1], vol: .7, ref: 1.2, rolloff: 1.3 },
  motor_viatura:       { tipo: 'posicional', pos: [3.4, .5, 18.05], vol: .6, ref: 2, rolloff: 1.2 },
  choro_crianca_baixo: { tipo: 'posicional', pos: [-6.4, 1.0, 2.05], vol: .5, ref: .8, rolloff: 1.6, soTreino: true },
  cachorro_longe:      { tipo: 'esporadico', area: [[-45, -25], [-45, 45]], vol: .45, intervalo: [25, 60] },
  sirene_longe:        { tipo: 'evento', vol: .4 },
  radio_chiado:        { tipo: 'evento', vol: .5 },
  radio_bip:           { tipo: 'evento', vol: .6 },
  batida_porta:        { tipo: 'evento', vol: .9 },
  passos_piso:         { tipo: 'evento', vol: .4 },
  caco_vidro:          { tipo: 'evento', vol: .6 },
  obturador:           { tipo: 'evento', vol: .7 },
  fita_zebrada:        { tipo: 'evento', vol: .6 },
  algemas:             { tipo: 'evento', vol: .7 }
};

export async function iniciarAudio({ scene, camera, renderer }) {
  let manifest = [];
  try { manifest = await fetch('audio/manifest.json').then(r => r.ok ? r.json() : []); } catch (e) { }
  const arquivos = Object.fromEntries(manifest.map(f => [f.replace(/\.(mp3|ogg|wav)$/i, ''), 'audio/' + f]));
  const listener = new THREE.AudioListener(); camera.add(listener);
  const loader = new THREE.AudioLoader(), buffers = {}, ambientes = [], posicionais = [];
  const V = new THREE.Vector3();
  let ligado = false, mudo = false;

  await Promise.all(Object.entries(arquivos).filter(([n]) => DEF[n]).map(([n, url]) =>
    loader.loadAsync(url).then(b => { buffers[n] = b; }).catch(() => console.warn('som nao carregou:', url))));

  function ligar() {
    if (ligado) return; ligado = true;
    listener.context.resume?.();
    for (const [n, b] of Object.entries(buffers)) {
      const d = DEF[n];
      if (d.tipo === 'ambiente') {
        const a = new THREE.Audio(listener); a.setBuffer(b); a.setLoop(true); a.setVolume(0); a.play();
        ambientes.push({ a, d });
      } else if (d.tipo === 'posicional' && !d.soTreino) {
        posicional(n, d);
      }
    }
    agendarEsporadicos();
  }
  function posicional(n, d) {
    const a = new THREE.PositionalAudio(listener); a.setBuffer(buffers[n]); a.setLoop(true);
    a.setRefDistance(d.ref); a.setRolloffFactor(d.rolloff); a.setDistanceModel('exponential'); a.setVolume(mudo ? 0 : d.vol);
    const o = new THREE.Object3D(); o.position.fromArray(d.pos); o.add(a); scene.add(o); a.play();
    posicionais.push({ n, a, o, d });
    return a;
  }
  function agendarEsporadicos() {
    for (const [n, d] of Object.entries(DEF)) {
      if (d.tipo !== 'esporadico' || !buffers[n]) continue;
      const tocar = () => {
        if (!mudo) {
          const a = new THREE.PositionalAudio(listener); a.setBuffer(buffers[n]); a.setRefDistance(8); a.setVolume(d.vol);
          const o = new THREE.Object3D();
          o.position.set(THREE.MathUtils.randFloat(...d.area[0]), 1, THREE.MathUtils.randFloat(...d.area[1]));
          o.add(a); scene.add(o); a.play(); a.onEnded = () => { a.isPlaying = false; scene.remove(o); };
        }
        setTimeout(tocar, THREE.MathUtils.randFloat(...d.intervalo) * 1000);
      };
      setTimeout(tocar, THREE.MathUtils.randFloat(5, 15) * 1000);
    }
  }
  for (const ev of ['pointerdown', 'keydown']) addEventListener(ev, ligar, { once: false });
  renderer.xr.addEventListener('sessionstart', ligar);

  // volume dos ambientes conforme dentro/fora da casa (transicao suave)
  let dentro = 0;
  function quadro(dt) {
    if (!ligado) return;
    camera.getWorldPosition(V);
    const alvo = (V.x > -6 && V.x < 6 && V.z > -4 && V.z < 4) ? 1 : 0;
    dentro += (alvo - dentro) * Math.min(1, dt * 1.5);
    for (const { a, d } of ambientes) a.setVolume(mudo ? 0 : d.fora * (1 - dentro) + d.dentro * dentro);
  }

  const api = {
    tem: n => !!buffers[n],
    tocar(n, pos) {                                   // eventos do treinamento; retorna false se o arquivo nao existe
      if (!buffers[n]) return false;
      ligar();
      const d = DEF[n] || { vol: .7 };
      if (mudo) return true;
      if (pos) {
        const a = new THREE.PositionalAudio(listener); a.setBuffer(buffers[n]); a.setRefDistance(1.2); a.setVolume(d.vol);
        const o = new THREE.Object3D(); o.position.copy(pos); o.add(a); scene.add(o); a.play();
        a.onEnded = () => { a.isPlaying = false; scene.remove(o); };
      } else {
        const a = new THREE.Audio(listener); a.setBuffer(buffers[n]); a.setVolume(d.vol); a.play();
      }
      return true;
    },
    iniciarTreino() { if (buffers.choro_crianca_baixo && !posicionais.some(p => p.n === 'choro_crianca_baixo')) { ligar(); posicional('choro_crianca_baixo', DEF.choro_crianca_baixo); } },
    pararChoro() { const p = posicionais.find(p => p.n === 'choro_crianca_baixo'); if (p) { p.a.stop(); scene.remove(p.o); posicionais.splice(posicionais.indexOf(p), 1); } },
    mudo(v) { mudo = v; for (const p of posicionais) p.a.setVolume(v ? 0 : p.d.vol); },
    quadro, carregados: () => Object.keys(buffers)
  };
  window.__som = api;
  return api;
}
