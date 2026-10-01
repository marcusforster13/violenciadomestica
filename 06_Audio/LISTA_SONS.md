# Sons para o treinamento — onde buscar e o que baixar

## Onde buscar (gratuito e com licença que permite usar)

| Site | Licença | Como filtrar |
|---|---|---|
| **https://freesound.org** | Vários; use **CC0** (uso livre, sem crédito) | Busque em inglês → filtro *License* → **Creative Commons 0** |
| **https://pixabay.com/sound-effects/** | Pixabay Content License (livre, inclusive comercial, sem crédito) | Busque em inglês ou português |
| **https://www.zapsplat.com** | Grátis com crédito (ou pago sem crédito) | Precisa de conta |

**Evite baixar do YouTube.** Ripar áudio de vídeos viola os termos do YouTube, e a maioria dos sons de lá tem direitos autorais. Mesmo vídeos "sem copyright" costumam ter licença só para vídeos, não para software.

## Formato

- **MP3 ou OGG**, 44,1 kHz.
- **Ambientes**: estéreo, de preferência **em loop** (procure "loop" ou "seamless").
- **Sons pontuais** (porta, rádio, cachorro): **mono** — o visualizador posiciona o som no espaço 3D.
- Coloque os arquivos aqui, em `06_Audio\brutos\`, com o nome da tabela abaixo (pode ser .mp3 ou .ogg).

## Lista (por prioridade)

| Nome do arquivo | O que é | Buscar por (inglês) | Onde toca |
|---|---|---|---|
| ✅ `amb_rua_noite` | Ambiente noturno de bairro: grilos, cidade ao longe | *night ambience suburb crickets loop* | Rua, sempre (abafado dentro da casa) |
| `amb_casa_interior` | Silêncio de casa com zumbido baixo | *room tone house night* | Dentro da casa |
| `tv_abafada` | TV ligada, vozes abafadas | *tv murmur muffled* / *television background* | Sala (sai da TV) |
| ✅ `geladeira_zumbido` | Motor da geladeira | *refrigerator hum loop* | Cozinha (sai da geladeira) |
| `radio_chiado` | Chiado e bip do rádio policial (sem falas reais) | *police radio static beep* / *walkie talkie beep* | Rádio da guarnição |
| `radio_bip` | Bip curto de transmissão (PTT) | *radio push to talk beep* | Ao usar o rádio |
| `motor_viatura` | Carro parado em marcha lenta | *car engine idle loop* | Viatura |
| `cachorro_longe` | Cachorro latindo distante | *dog barking distant* | Vizinhança, de vez em quando |
| `batida_porta` | Batidas firmes em porta de vidro/madeira | *knocking on door* | Ao se identificar |
| `passos_piso` | Passos em piso de granilite/cerâmica | *footsteps tile floor* | Andando dentro da casa |
| `caco_vidro` | Pisar em caco de vidro/louça | *glass shards step crunch* | Ao passar pelos cacos |
| `obturador` | Clique de câmera fotográfica | *camera shutter click* | Ferramenta câmera |
| `fita_zebrada` | Fita plástica desenrolando | *tape unroll plastic* | Ferramenta fita |
| `algemas` | Algemas fechando | *handcuffs click* | Ferramenta algemas |
| `choro_crianca_baixo` | Choro baixo e contido de criança | *child crying softly* | Quarto (até ser encontrada) |
| `sirene_longe` | Sirene ao longe (opcional) | *police siren distant* | Início / chegada do apoio |

## Vozes (melhor gravar do que baixar)

As falas da **ligação do 190**, da **vítima**, do **agressor**, da **criança** e do **vizinho** estão no
`05_Treinamento\cenario_vd_01.json` e no roteiro. O ideal é **gravar com atrizes e atores** (pode ser com
celular num ambiente silencioso), um arquivo por fala. Enquanto isso, o visualizador usa voz sintética.

### Relato da vítima (já ligado no site: é só gravar e salvar com o nome certo)

Salve em `06_Audio\brutos\` com **exatamente** estes nomes (mp3). Rode o `atualizar_tudo.ps1` ou copie para
`04_ThreeJS\web\audio\` e acrescente o nome em `audio\manifest.json`. A fala que tiver arquivo toca com a voz
gravada saindo da personagem; a que não tiver continua com a voz sintética e legenda.
Dica de gravação: voz baixa, cansada, com pausas — ela acabou de ser agredida. Não precisa ser "atuação" exagerada.

| Arquivo | Fala |
|---|---|
| fala_vitima_relato_01.mp3 | Ele chegou tarde… já tinha bebido. Eu estava terminando a janta com a minha filha. |
| fala_vitima_relato_02.mp3 | Ele viu a mala no quarto. Eu falei que ia pra casa da minha mãe, e ele começou a gritar. |
| fala_vitima_relato_03.mp3 | Jogou o prato no chão, deu um soco na parede… pegou o meu celular e jogou longe. |
| fala_vitima_relato_04.mp3 | Aí ele me empurrou contra a mesa. A cadeira caiu, o copo virou… e ele me deu um tapa na boca. |
| fala_vitima_relato_05.mp3 | O meu braço tá doendo muito. A minha filha viu tudo… ela correu pro quarto. |
| fala_vitima_relato_06.mp3 | Quando eu liguei pra vocês ele saiu pelos fundos. Ele não foi embora… ele tá aqui perto, eu sei. |
| fala_vitima_relato_06b.mp3 | Quando ouviu a sirene ele saiu correndo pelo portão. Não sei pra onde ele foi. |
| fala_vitima_relato_06c.mp3 | Ele tá lá na cozinha… agora fica fingindo que não aconteceu nada. |
| fala_vitima_relato_06d.mp3 | Ele tá lá na cozinha… cuidado, ele tá muito alterado. |
| fala_vitima_relato_07.mp3 | Por favor… eu não aguento mais. Ele já me ameaçou outras vezes. |
| fala_vitima_minimiza_01.mp3 | Foi só uma discussão… ele bebeu um pouco e a gente brigou. |
| fala_vitima_minimiza_02.mp3 | Esse machucado? Eu bati na mesa. Não precisa fazer nada com ele, não. |

Os textos ficam em `05_Treinamento\cenario_vd_01.json` → `relato_vitima` (pode mudar o texto lá; o gesto de cada
fala também: falando, estressada, nervosa, ofegante).
