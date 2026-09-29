# A Casa em Silêncio — treinamento VR em violência doméstica

Cena 3D de uma casa modernista brasileira num condomínio do Rio de Janeiro, após um episódio de violência doméstica, para treinamento policial em realidade virtual.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `01_Cena_Render_Cycles/` | **Fonte**: cena principal do Blender (`casa_em_silencio.blend`), script gerador e script das texturas CC0 |
| `02_Cena_VR_Otimizada/` | Versão otimizada para Unity/Unreal (`.blend`, `.glb`, `.fbx`), gerada a partir da fonte |
| `03_Web_Prototipo/` | Primeiro protótipo em HTML |
| `04_ThreeJS/` | Pipeline three.js (texturas PBR, lightmaps) e o visualizador WebXR em `web/` (publicado no Vercel) |
| `05_Treinamento/` | Roteiro do treinamento (`ROTEIRO_TREINAMENTO.md`) e cenário em dados (`cenario_vd_01.json`) |

## Atualizar tudo depois de mexer na cena

```powershell
.\atualizar_tudo.ps1          # padrão (~7 min)
.\atualizar_tudo.ps1 rapido   # teste
.\atualizar_tudo.ps1 alta     # lightmaps em qualidade máxima
```

Requer Blender 5.2. Arquivos `.blend`, `.fbx`, `.exr` e o `.glb` da versão VR usam **Git LFS**.

## Publicação

O Vercel publica a pasta `04_ThreeJS/web` (HTTPS, abre direto no navegador do Meta Quest).

Texturas: Poly Haven (CC0). Violência contra a mulher: **Ligue 180** · Emergência: **190**.
