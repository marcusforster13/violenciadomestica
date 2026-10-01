# Pedidos de modelagem — A Casa em Silêncio

Peças em que a modelagem à mão faz mais diferença. As peças "matemáticas" (garrafas, louça, copos,
potes, filtro de barro) ficam por conta dos scripts.

## Como entregar (igual aos livros)

1. Modele **no lugar certo da cena**: abra `casa_em_silencio.blend` e modele por cima do objeto antigo, ou importe-o como referência.
2. Escala real, em **metros**. Aplique escala e rotação (Ctrl+A → All Transforms) nas malhas; o objeto raiz pode ser um Empty.
3. **Use os nomes de material da cena** sempre que der (ex.: `Madeira_Jacaranda`, `Couro_Caramelo`, `Tecido_Verde`), para herdar as texturas. Materiais novos também funcionam.
4. Exporte **só aquele objeto** como `.glb` (File → Export → glTF, *Selected Objects*, formato *glTF Binary*).
5. Coloque o arquivo em `01_Cena_Render_Cycles\modelos\` e registre em `modelos.json`:
   ```json
   "sofa.glb": { "substitui": "Sofa", "colecao": "02_Sala" }
   ```
6. Rode `.\atualizar_tudo.ps1`: o script integra, faz backup, religa os materiais e refaz as versões VR e web.

## Prioridade 1 — vestígios (são o centro do treinamento)

| Objeto na cena (substitui) | Coleção | Limite de triângulos | Observações |
|---|---|---|---|
| `V_Celular` | 08_Vestigios | 1.500 | Smartphone com cantos arredondados, tela trincada (pode ser textura), capinha |
| `V_Porta_Retrato` | 08_Vestigios | 2.000 | Moldura quebrada, vidro estilhaçado, foto (deixe um plano para a imagem) |
| `V_Mala` | 08_Vestigios | 5.000 | Mala aberta com zíper, alça, rodinhas; roupas amassadas saindo |
| `V_Ursinho` | 08_Vestigios | 3.000 | Pelúcia caída de lado |
| `["V_Luminaria_Base", "V_Luminaria_Haste", "V_Luminaria_Cupula", "V_Luminaria_Lampada"]` | 08_Vestigios | 2.500 | Luminária de piso tombada (são 4 objetos soltos: use a lista no `modelos.json`) |
| `V_Cadeira_Tombada` | 08_Vestigios | 2.500 | Mesma cadeira de palhinha do jantar, caída para trás |

## Prioridade 2 — móveis principais (aparecem em todo enquadramento)

| Objeto na cena | Coleção | Limite | Observações |
|---|---|---|---|
| `Sofa` | 02_Sala | 6.000 | Sofá anos 60 de pés palito, almofadas com volume e costuras |
| `Poltrona` | 02_Sala | 6.000 | Referência: Poltrona Mole (Sergio Rodrigues) — couro com almofadas soltas |
| `Mesa_Centro` | 02_Sala | 1.500 | Madeira, pés palito |
| `Rack_TV` (+ TV) | 02_Sala | 3.000 | Rack anos 60 com portas de correr; TV fina |
| `Mesa_Jantar` | 03_Jantar | 2.000 | Tampo de jacarandá. **Atenção:** pratos, comida, talheres, copo e líquido são filhos da mesa e saem junto; inclua-os no seu `.glb` ou me avise para eu separá-los antes |
| `Cadeira_1` (a mesma para 2 e 3) | 03_Jantar | 2.500 | Cadeira de palhinha estilo Tenreiro/Zanine |
| `Costela_de_Adao` | 02_Sala | 6.000 | Folhas recortadas (fenestradas) e curvadas, vaso de barro |
| `Geladeira` | 04_Cozinha | 2.500 | Geladeira retrô com puxador cromado (verde-água) |

## Prioridade 3 — se sobrar tempo

| Objeto | Coleção | Limite |
|---|---|---|
| `Rede` (varanda) | 05_Varanda | 4.000 |
| Viatura (`Viatura_PMERJ`) | 10_Viatura_PMERJ | 60.000 — ou comprar um modelo licenciado |
| Carros dos moradores | 10b_Carros_Moradores | 40.000 cada |

## Dicas

- **Quinas**: um bevel pequeno (2 a 5 mm) em tudo que é "caixa" deixa o objeto muito mais real.
- **Normais**: ative *Shade Auto Smooth* e confira se nada ficou com sombreado quebrado.
- **UV**: se fizer UV, o pipeline respeita; se não fizer, ele projeta automaticamente.
- **Limite total no Quest**: a cena inteira está em ~360 mil triângulos; o teto confortável é ~750 mil.
