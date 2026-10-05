# Briefing para um novo treinamento em VR no mesmo estilo

Este documento descreve como o projeto **"A Casa em Silêncio"** (treinamento VR de atendimento a violência doméstica, PMERJ) foi construído, para servir de base a um novo cenário — por exemplo, **Operação Lei Seca**.

**Como usar:** abra um novo chat com acesso a esta pasta (`C:\Users\marcus.leite\Downloads\DV`) e cole o texto da seção 1. O restante é referência técnica para o assistente ler.

---

## 1. Texto para colar no novo chat

> Quero criar um treinamento em realidade virtual para a **Operação Lei Seca** no Rio de Janeiro, **no mesmo estilo e com a mesma arquitetura** do projeto que está em `C:\Users\marcus.leite\Downloads\DV`.
>
> Antes de começar, leia `GUIA_PARA_NOVO_PROJETO.md` nessa pasta e use os scripts de lá como modelo (copie e adapte, não reescreva do zero).
>
> O que eu quero:
> - Cenário 3D modelado no **Blender** (arquivo `.blend` como fonte), em português e com a realidade brasileira.
> - Versão otimizada para VR (Unity/Unreal) e versão **three.js/WebXR** publicada no **Vercel** via GitHub, rodando no Meta Quest.
> - Texturas realistas de uso livre (CC0), iluminação pré-calculada (bake), personagens animados com voz, boca e olhar.
> - Mecânica de treinamento baseada na **lei e no procedimento brasileiros**, com variações sorteadas, modo treino, modo avaliação, modo história e relatório com nota e base legal.
> - Crie o projeto numa pasta nova (por exemplo `C:\Users\marcus.leite\Downloads\LeiSeca`), com repositório e projeto Vercel próprios.
>
> Trabalhe como no projeto anterior: fale comigo em português simples, mostre imagens do que fez, teste antes de subir e suba para o GitHub/Vercel a cada etapa.

---

## 2. Estrutura de pastas (repita no projeto novo)

| Pasta | Conteúdo |
|---|---|
| `01_Cena_Render_Cycles/` | `.blend` principal (a fonte de tudo), scripts que melhoram a cena, `modelos/` (peças modeladas à mão) e `backup/` |
| `02_Cena_VR_Otimizada/` | `otimizar_para_vr.py`: gera a versão para Unity/Unreal e a colisão |
| `04_ThreeJS/` | `pipeline_threejs.py` (bake de lightmaps e exportação), `texturas_cc0/`, `web/` (o site) |
| `05_Treinamento/` | `cenario_*.json` (toda a mecânica) e `ROTEIRO_TREINAMENTO.md` (documento para instrutores) |
| `06_Audio/` | `brutos/` (sons e vozes), `LISTA_SONS.md`, `gerar_roteiro_vozes.py` |
| `07_Personagens/` | `converter_personagens.py`, `checar_personagens.py`, `rocketbox/` (downloads, fora do Git) |
| raiz | `atualizar_tudo.ps1` (roda tudo em ordem), `vercel.json`, `.gitignore`, `.gitattributes` |

**Regra central:** o `.blend` de `01_` é a única fonte. Tudo o mais é gerado por `atualizar_tudo.ps1` e pode ser refeito.

## 3. Pipeline (`atualizar_tudo.ps1`)

Roda o Blender sem interface (`blender -b arquivo.blend --python script.py`), nesta ordem:

**Passo 0 — melhorias na cena principal** (cada script é idempotente e salva o `.blend`):

| Script | Faz |
|---|---|
| `integrar_modelos.py` | Importa os `.glb` de `modelos/` conforme `modelos.json` (`"arquivo.glb": {"substitui": "Objeto" ou [lista], "colecao": "..."}`), faz backup e religa materiais pelo nome |
| `melhorias_modelagem.py` | Chanfro em caixas |
| `pecas_detalhadas.py`, `detalhes_*.py` | Refaz objetos pequenos (louça, garrafas, pia, geladeira) |
| `arbustos.py`, `palmeiras.py` | Vegetação com cartões de folhas (textura gerada com transparência) |
| `viatura.py` | Viatura (loft de seções, rodas, pintura) e redução dos carros de fundo |
| `suavizar_objetos.py` | Subdivisão com vincos; pula objetos com `ob["detalhado"]` |
| `aplicar_texturas_cc0.py` | Texturas PBR do Poly Haven por projeção em caixa (tabela `material → pasta, escala, cor`) |

**Passo 1 — `otimizar_para_vr.py`:** converte materiais para UV + PNG, assa os procedurais, junta objetos estáticos por coleção, gera `colisao.glb` (caixas orientadas) e mantém separados os objetos interativos.

**Passo 2 — `pipeline_threejs.py`:** aplica PBR, assa **lightmaps** no Cycles (segunda UV "Lightmap", níveis `rapido`/padrão/`alta`), converte o HDRI, exporta `web/cena.glb` (Draco) + `cena.json`, copia cenário, colisão e áudio para `web/`.

**Passo 3 — `converter_personagens.py`:** personagens para `web/personagens/*.glb`.

## 4. Site three.js (`04_ThreeJS/web/`)

- **three.js r160** por import map (jsDelivr), `GLTFLoader` + `DRACOLoader`, `RGBELoader`, `VRButton`, `XRControllerModelFactory`, **three-mesh-bvh** para colisão por raio.
- `index.html`: visualizador, céu procedural por shader, lightmaps, movimento com colisão (`mover()`/`seguirChao()`), controles VR.
- `treinamento.js`: motor do treinamento (lê o JSON do cenário).
- `audio.js`: sons ambiente, posicionais e de evento, normalizados para ~−20 dB.
- **Controles no Quest:** analógico esquerdo anda, direito gira em passos; gatilho direito teleporta e interage; gatilho esquerdo só interage; grip liga a lanterna; **Y/B** abre o menu.
- **Menus 3D:** painel desenhado em canvas na frente do jogador. Precisa de realce do botão apontado, ponto no local do raio e linha do controle terminando no painel (senão a linha some atrás do menu). Com menu aberto, o gatilho não teleporta.
- `vercel.json` com *rewrites* de `/` para `/04_ThreeJS/web/`.

## 5. Personagens

- **Fonte:** biblioteca de avatares **Rocketbox** (licença MIT), FBX + animações. Arquivos originais ficam fora do Git.
- **Problemas já resolvidos no conversor (não repetir):**
  - Os FBX de animação trazem a pose do 1º quadro como pose de repouso. A animação é **redirecionada osso a osso no espaço do mundo**, comparando com a T-pose de um adulto.
  - Crianças usam outro esqueleto (`Bip02`, eixos diferentes): o mesmo redirecionamento resolve.
  - A altura do quadril fica na raiz: a posição da pelve é escalada pela altura do personagem.
  - Corrida e caminhada são **fixadas no lugar** (o site move o personagem).
  - Poses que não existem (mãos na cabeça, algemado, escalando) são geradas no conversor com **IK de dois ossos** sobre uma animação base (`"nome": "animacao+pose"`).
  - Exportação glTF por faixas NLA, passo de 2 quadros, texturas em 1024 px.
- **No site:**
  - `SkeletonUtils.clone` + `AnimationMixer`; troca de animação com *crossfade*.
  - **Boca:** analisador de áudio na fonte do som (antes da atenuação por distância) gira a mandíbula; voz sintética usa um ritmo de sílabas.
  - **Piscar:** ossos das pálpebras movidos por posição.
  - **Olhar:** pescoço e cabeça giram para o jogador; a frente do rosto é medida na pose de repouso (não pelos olhos).
  - **Atenção:** a exportação remove faixas de animação constantes. Sempre que girar um osso por código, parta da pose base quando a animação não mexer nele, senão o giro acumula a cada quadro.
  - **Área de clique:** cilindro invisível que acompanha a altura da cabeça a cada quadro.

## 6. Mecânica do treinamento (`05_Treinamento/cenario_*.json`)

Tudo fica no JSON, para os instrutores poderem editar:

- `fases[]` com `acoes` (pontos, `base` legal, `condicao`), `erros` e `falhas_graves`.
- `variacoes` sorteadas a cada ocorrência; `condicao` no formato `variacao.x == 'y'`, com `&&` e `||`.
- `vestigios[]` (posição, nome, condição), `dialogos`, `radio`, roteiros de fala com gesto.
- `vozes.falas[]`: catálogo `arquivo / personagem / quando / texto`. **A gravação é encontrada pelo texto exato.**
- **Modos:** exploração (cena livre, personagens respondem ao clique), **treino** (objetivos na tela e dicas), **avaliação** (sem dicas), **história** (capítulos guiados a partir da exploração).
- **Relatório:** nota 0–100, aprovação com 70 e nenhuma falha grave, itens por fase com base legal, download em JSON.
- Variação pode ser forçada pela URL: `?v=chave:valor,chave:valor`.

## 7. Áudio e vozes

- Sons em `06_Audio/brutos/` (`.mp3` ou `.wav`); o pipeline copia para `web/audio/` e gera `manifest.json`.
- Vozes: um arquivo por fala, nome do catálogo. Ao receber gravações: conferir ruído e duplicados, **cortar silêncios** (deixar ~0,12 s antes e ~0,35 s depois) e instalar.
- `gerar_roteiro_vozes.py` gera o roteiro para impressão (HTML) e um `.txt` por personagem, marcando o que já foi gravado.
- Sem gravação, o site usa a voz sintética do navegador (pt-BR) com legenda.

## 8. GitHub e Vercel

- `.gitattributes`: Git LFS para `*.blend`, `*.fbx`, `*.exr`.
- `.gitignore`: arquivos gerados de `02_`, downloads de personagens, backups, logs e temporários.
- Os `.glb` do site **não** vão para LFS (o Vercel precisa servir o arquivo real).
- Depois de cada `push`, conferir no site publicado que a versão nova entrou.

## 9. Regras que seguimos

- **Sem logotipos de marcas** e **sem reproduzir brasões oficiais**: deixar um espaço para imagem que o órgão esteja autorizado a usar.
- Texturas e sons só de fontes com licença livre (Poly Haven CC0; sons CC0). Não extrair áudio de vídeos.
- Downloads só com autorização, informando arquivo, origem e tamanho.
- Toda regra do treinamento tem **base legal** e os pontos incertos são marcados para **validação com instrutores**.
- Conteúdo sensível com aviso antes de começar.
- Fazer backup do `.blend` antes de cada script que altera a cena.

## 10. Armadilhas do ambiente (para o assistente)

- Não há Python no sistema: usar o do Blender (`...\Blender 5.2\5.2\python\bin\python.exe`).
- No PowerShell com `$ErrorActionPreference = "Stop"`, qualquer aviso do Blender em *stderr* derruba o `atualizar_tudo.ps1` (evitar APIs obsoletas como `use_nodes`).
- Em comandos de shell com *heredoc*, sequências `\\n`, `\\b` viram caracteres de controle: para editar código, gravar um script `.py` em arquivo e executar.
- Transparência recortada no glTF: usar nó **Math ROUND** entre o alfa e o Principled (vira `alphaMode: MASK`).
- O painel do navegador, quando escondido, pausa `requestAnimationFrame`: nos testes, chamar o `quadro()` do treinamento por `setInterval`.
- O servidor local simples faz cache dos `.js`: usar um servidor de testes com `Cache-Control: no-store`.
- Para ver o site por imagem: renderizar com um `WebGLRenderer` extra e enviar por `POST` ao servidor de testes.
- Caminhos de personagens: conferir contra a geometria visível (grades e portões podem não estar na malha de colisão).

## 11. O que definir para a Operação Lei Seca

O novo chat deve levantar e confirmar com você, antes de modelar:

- **Local:** trecho de via com a blitz montada (cones, tenda, viaturas, iluminação, painel de mensagem), dia ou noite.
- **Papel do jogador:** agente da operação (abordagem, teste do etilômetro, autuação).
- **Personagens:** condutor, passageiros, outros agentes, eventualmente pedestres.
- **Objetos interativos:** etilômetro e bocal descartável, documentos (CNH e CRLV), talonário ou tablet de autuação, cones, lanterna, rádio.
- **Variações:** condutor sóbrio, com sinais de embriaguez, que recusa o teste, sem habilitação ou com CNH vencida, veículo irregular, condutor agressivo, tentativa de fuga, passageiro habilitado que pode assumir o veículo.
- **Base legal a pesquisar e citar:** Código de Trânsito Brasileiro (arts. 165, 165-A, 276, 277 e 306), Lei 11.705/2008, Lei 12.760/2012, Lei 13.281/2016 e a resolução do CONTRAN sobre o etilômetro e os sinais de alteração da capacidade psicomotora; direitos do condutor na abordagem.
- **Pontos para validar com a coordenação da operação:** fluxo real da abordagem, quem faz cada etapa (agentes de trânsito, PM, outros órgãos), formulários usados e critérios de pontuação.
