/* Central de monitoramento da guarita (CFTV).
   As telas CFTV_Tela_<n>_c<cam> (geradas por 01_Cena_Render_Cycles/central_monitoramento.py) mostram AO VIVO
   o que cada camera CFTV_Cam_<cam> do cena.json ve: imagem de camera noturna (P&B, ruido, linhas), nome da
   camera, data/hora e REC piscando. Personagens, viatura e o proprio jogador aparecem nas imagens.
   Desempenho: 320x180 por camera; com o jogador a menos de PERTO metros da guarita atualiza 1 camera por quadro
   (cada uma ~12 vezes por segundo no Quest); longe, as telas ficam com a ultima imagem. */
import * as THREE from 'three';

const ROTULOS = { 1: 'PORTARIA', 2: 'RUA - SENTIDO OESTE', 3: 'CASA 147', 4: 'RUA - TRECHO CENTRAL',
                  5: 'CALÇADA 150-160', 6: 'ENTRADA / CANCELA' };
const W = 320, H = 180, PERTO = 22;
const INICIO = 23 * 3600 + 47 * 60 + 12;          // relogio das cameras: 23:47:12 quando a cena abre

const vertexShader = `varying vec2 vUv;
  void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const fragmentShader = `uniform sampler2D uImg, uTxt; uniform float uTempo, uSemente; varying vec2 vUv;
  float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
  void main(){
    vec2 uv = vec2(vUv.x, 1.0 - vUv.y);
    float l = dot(texture2D(uImg, uv).rgb, vec3(.3, .59, .11));
    l = 1.0 - exp(-l * 9.0);                                              // ganho de camera noturna
    l += (hash(floor(uv * vec2(320.0, 180.0)) + fract(uTempo * 7.3 + uSemente)) - .5) * .09;   // ruido
    l *= .93 + .07 * sin(uv.y * 565.0);                                   // linhas de varredura
    l *= mix(.6, 1.0, smoothstep(.85, .3, length(uv - .5)));              // vinheta
    vec3 col = clamp(l, 0.0, 1.0) * vec3(.88, 1.0, .9);
    vec4 t = texture2D(uTxt, uv);
    gl_FragColor = vec4(mix(col, t.rgb, t.a), 1.0);
  }`;

export function iniciarCFTV({ scene, camera, renderer, CFG }) {
  const telas = [];
  scene.traverse(o => { const m = o.isMesh && /^CFTV_Tela_\d+_c(\d+)/.exec(o.name); if (m) telas.push({ o, n: +m[1] }); });
  const cams = {};
  for (const n of new Set(telas.map(t => t.n))) {
    const c = CFG.cameras?.['CFTV_Cam_' + n];
    if (!c) continue;
    const cam = new THREE.PerspectiveCamera(51, W / H, .1, 90);
    cam.position.fromArray(c.pos); cam.lookAt(new THREE.Vector3().fromArray(c.alvo)); cam.updateMatrixWorld();
    const cv = document.createElement('canvas'); cv.width = 512; cv.height = 288;
    cams[n] = { cam, rt: new THREE.WebGLRenderTarget(W, H), cv, g: cv.getContext('2d'), tx: new THREE.CanvasTexture(cv) };
  }
  const ordem = Object.keys(cams).map(Number);
  if (!ordem.length) return;
  const centro = new THREE.Vector3(), v = new THREE.Vector3();
  telas.forEach(t => centro.add(t.o.getWorldPosition(v))); centro.divideScalar(telas.length);
  const mats = [];
  for (const t of telas) {
    const c = cams[t.n];
    if (!c) continue;
    t.o.material = new THREE.ShaderMaterial({
      uniforms: { uImg: { value: c.rt.texture }, uTxt: { value: c.tx }, uTempo: { value: 0 }, uSemente: { value: Math.random() * 10 } },
      vertexShader, fragmentShader, toneMapped: false, fog: false });
    mats.push(t.o.material);
  }

  const dois = x => String(x).padStart(2, '0');
  const hoje = new Date(), data = dois(hoje.getDate()) + '/' + dois(hoje.getMonth() + 1) + '/' + hoje.getFullYear();
  function legenda(n, t) {
    const { g, tx } = cams[n], s = Math.floor(INICIO + t) % 86400;
    g.clearRect(0, 0, 512, 288);
    g.font = 'bold 21px Consolas, monospace'; g.shadowColor = '#000'; g.shadowBlur = 5; g.fillStyle = 'rgba(255,255,255,.93)';
    g.fillText('CAM ' + dois(n) + '  ' + ROTULOS[n], 14, 30);
    g.fillText(data + '  ' + dois(Math.floor(s / 3600)) + ':' + dois(Math.floor(s / 60) % 60) + ':' + dois(s % 60), 14, 274);
    g.fillText('REC', 450, 30);
    if (Math.floor(t * 2) % 2 === 0) { g.fillStyle = '#ff2b20'; g.beginPath(); g.arc(436, 23, 7, 0, 7); g.fill(); }
    tx.needsUpdate = true;
  }
  function filmar(c) {
    for (const t of telas) t.o.visible = false;              // a tela nao pode aparecer na propria imagem
    const xr = renderer.xr.enabled, alvo = renderer.getRenderTarget();
    renderer.xr.enabled = false;
    renderer.setRenderTarget(c.rt); renderer.render(scene, c.cam);
    renderer.setRenderTarget(alvo); renderer.xr.enabled = xr;
    for (const t of telas) t.o.visible = true;
  }

  let k = 0, primeira = true, ultimo = -1;
  window.__cftv = {
    quadro(t) {
      if (primeira) { primeira = false; ordem.forEach(n => { filmar(cams[n]); legenda(n, 0); }); }
      camera.getWorldPosition(v);
      if (v.distanceTo(centro) > PERTO) return;
      filmar(cams[ordem[k++ % ordem.length]]);
      const meio = Math.floor(t * 2);
      if (meio !== ultimo) { ultimo = meio; ordem.forEach(n => legenda(n, t)); }
      for (const m of mats) m.uniforms.uTempo.value = t;
    },
    cameras: cams,
  };
  console.info('[CFTV] %d telas, %d cameras', telas.length, ordem.length);
}
