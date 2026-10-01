# 07 · Personagens (Microsoft Rocketbox)

Personagens animados do treinamento: vítima, agressor, criança e vizinho.
Fonte: <https://github.com/microsoft/Microsoft-Rocketbox>. A licença é MIT (uso livre, inclusive comercial; mantenha `rocketbox/LICENCA_MIT.txt`).

## Arquivos

| Pasta | O que é | Vai pro GitHub? |
|---|---|---|
| `rocketbox/` | FBX e texturas originais baixados (~290 MB) | não (está no .gitignore) |
| `converter_personagens.py` | converte para o site (glTF, texturas de 1024 px, animações redirecionadas) | sim |
| `checar_personagens.py` | confere se os pés estão no chão, a altura e a posição das mãos | sim |
| `../04_ThreeJS/web/personagens/*.glb` | resultado usado pelo site e pelo Vercel (~19 MB no total) | sim |

## Papéis e animações

O arquivo de cada papel fica em `PAPEIS`, no início de `converter_personagens.py`.

| Papel | Modelo | Animações (nome no site → arquivo Rocketbox) |
|---|---|---|
| vítima | Female_Adult_08 | parada → f_idle_nervous_01 · falando → f_gestic_talk_sad_01 · estressada → f_gestic_talk_femalestressed_01 · ofegante → f_idle_breathe_01 |
| agressor | Male_Adult_01 | parada → m_idle_angry_01 · falando → m_gestic_talk_neutral_01 · nervoso → m_idle_nervous_01 · escondido → m_crouch_idle · rendido → m_crouch_idle + pose "mãos na cabeça" (feita pelo conversor) · correndo → m_run_fast_01 · andando → m_walk_fast_01 (as duas da pasta `all_animations_max_motextr_xy`, fixadas no lugar; o site move o personagem) |
| criança | Female_Child_01 | parada → f_crouch_idle (agachada) · ofegante → f_idle_breathe_01 |
| vizinho | Male_Adult_14 | parada → m_idle_neutral_01 · falando → m_gestic_talk_neutral_01 |

## Como baixar de novo (só se apagar a pasta `rocketbox/`)

A base dos endereços é `https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets/`. Cada arquivo fica em:

- **Modelos adultos:** `Avatars/Adults/<Nome>/<Nome>.fbx` e `Avatars/Adults/<Nome>/Textures/*.tga`. Os nomes das texturas seguem o padrão `f008_body_color.tga`, `_body_normal`, `_head_color`, `_head_normal` e `_opacity_color`.
- **Crianças:** `Avatars/Children/<Nome>/…`, com a mesma estrutura dos adultos.
- **Animações:** `Animations/all_animations_max_motextr_static/<animacao>.fbx`.

Salve tudo assim:

- `rocketbox/<Nome>/<Nome>.fbx`
- `rocketbox/<Nome>/Textures/`
- `rocketbox/Animacoes/<animacao>.fbx`

## Converter

O `atualizar_tudo.ps1` (passo 3/3) já faz isso e só refaz o personagem cujo FBX mudou. Também dá para rodar à mão:

```
blender -b --factory-startup --python converter_personagens.py -- --forcar
set SO=crianca   (opcional: converte só um papel)
blender -b --factory-startup --python checar_personagens.py
```

### Por que as animações são "redirecionadas"

Os FBX de animação do Rocketbox vêm com a pose do 1º quadro gravada como pose de repouso, e a altura do quadril fica na raiz. Por isso o conversor faz o seguinte:

1. Compara cada osso da animação com a T-pose de um adulto, no espaço do mundo.
2. Aplica essa rotação sobre a T-pose do personagem.
3. Escala a posição do quadril pela altura do personagem.

A criança usa outro esqueleto (`Bip02`, com outra orientação dos ossos), e é isso que permite usar nela as animações de adulto.

## Trocar ou adicionar personagem

1. Escolha um modelo em `rocketbox/previas/` ou no GitHub do Rocketbox (`Assets/Avatars/...`). Escolha também as animações, em `Assets/Animations/...`.
2. Baixe os arquivos e edite `PAPEIS` no conversor.
3. Rode o conversor.

No site, as posições ficam em `criarNPCs()` de `04_ThreeJS/web/treinamento.js`.
