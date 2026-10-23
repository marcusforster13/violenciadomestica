/* Porta lateral da guarita (central de monitoramento): abre e fecha com um clique (desktop) ou o gatilho (VR).
   A folha gira na dobradica GuaritaC_Porta_Dobradica (01_Cena_Render_Cycles/central_monitoramento.py) e abre PARA
   FORA, sem passar por cima da mesa nem do balcao de dentro. A folha entra na lista de colisao: fechada, bloqueia a
   passagem; aberta, fica encostada para fora e o vao fica livre para entrar na guarita. */
const ABERTA = -Math.PI / 2;                     // mesmo giro do Blender (eixo vertical)
const TEMPO = .7, ALCANCE = 3.5;                 // segundos para abrir/fechar; distancia maxima do clique (m)

export function iniciarPorta({ scene, colisao }) {
  const dob = scene.getObjectByName('GuaritaC_Porta_Dobradica');
  if (!dob) return;
  const pecas = []; dob.traverse(o => { if (o.isMesh) pecas.push(o); });
  const folha = pecas.find(o => /Porta_Folha/.test(o.name));
  if (!folha) return;
  folha.geometry.computeBoundsTree?.();
  const lista = colisao();
  if (!lista.includes(folha)) lista.push(folha);
  const base = dob.rotation.y;
  let alvo = 0, atual = 0;                       // 0 = fechada, 1 = aberta
  const suave = t => t * t * (3 - 2 * t);

  window.__porta = {
    clique(ray) {
      const h = ray.intersectObjects(pecas, false)[0];
      if (!h || h.distance > ALCANCE) return false;
      alvo = alvo ? 0 : 1;
      return true;
    },
    quadro(dt) {
      if (atual === alvo) return;
      atual = alvo > atual ? Math.min(alvo, atual + dt / TEMPO) : Math.max(alvo, atual - dt / TEMPO);
      dob.rotation.y = base + ABERTA * suave(atual);
      dob.updateMatrixWorld(true);
    },
    get aberta() { return alvo === 1; },
    alternar() { alvo = alvo ? 0 : 1; },
  };
}
