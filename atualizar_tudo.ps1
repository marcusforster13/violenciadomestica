# A Casa em Silencio - regenera todas as versoes a partir da cena principal.
#   01_Cena_Render_Cycles\casa_em_silencio.blend  (FONTE: modele aqui)
#     -> 02_Cena_VR_Otimizada  (Unity / Unreal: .blend, .glb, .fbx)
#     -> 04_ThreeJS\web         (WebXR: cena.glb, lightmaps, cena.json)
#   07_Personagens\rocketbox      -> 04_ThreeJS\web\personagens (personagens animados)
#
# Uso:  .\atualizar_tudo.ps1            (padrao: ~6 min no total)
#       .\atualizar_tudo.ps1 rapido     (teste: ~3 min no total)
#       .\atualizar_tudo.ps1 alta       (qualidade maxima: ~30-60 min)
$ErrorActionPreference = "Stop"
$B = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$D = $PSScriptRoot

Write-Host "0/3  Integrando modelos novos (01_Cena_Render_Cycles\modelos) na cena principal..."
Push-Location "$D\01_Cena_Render_Cycles"
& $B -b "casa_em_silencio.blend" --python "integrar_modelos.py" 2>&1 | Select-String -Pattern '^\[MODELOS\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "melhorias_modelagem.py" 2>&1 | Select-String -Pattern '^\[MODELAGEM\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "adicionar_cameras_lpr.py" 2>&1 | Select-String -Pattern '^\[LPR\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "pecas_detalhadas.py" 2>&1 | Select-String -Pattern '^\[DETALHE\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "detalhes_cozinha_sala.py" 2>&1 | Select-String -Pattern '^\[DETALHE2\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "detalhes_pia.py" 2>&1 | Select-String -Pattern '^\[PIA\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "arbustos.py" 2>&1 | Select-String -Pattern '^\[ARBUSTO\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "suavizar_objetos.py" 2>&1 | Select-String -Pattern '^\[SUAVE\]' | ForEach-Object { $_.Line }
& $B -b "casa_em_silencio.blend" --python "aplicar_texturas_cc0.py" 2>&1 | Select-String -Pattern '^\[CC0\]' | ForEach-Object { $_.Line }
Pop-Location

Write-Host "1/3  Gerando versao VR (Unity/Unreal)..."
Push-Location "$D\02_Cena_VR_Otimizada"
& $B -b "$D\01_Cena_Render_Cycles\casa_em_silencio.blend" --python "otimizar_para_vr.py" *> vr_log.txt
Pop-Location
Select-String -Path "$D\02_Cena_VR_Otimizada\vr_log.txt" -Pattern '^\[VR\] (TOTAL|Colisao)' | ForEach-Object { $_.Line }

Write-Host "2/3  Gerando versao three.js (bake de lightmaps)..."
Push-Location "$D\04_ThreeJS"
& $B -b "$D\02_Cena_VR_Otimizada\casa_em_silencio_VR.blend" --python "pipeline_threejs.py" -- $args *> pipeline_log.txt
Pop-Location
Select-String -Path "$D\04_ThreeJS\pipeline_log.txt" -Pattern '^\[THREE\]' | ForEach-Object { $_.Line }


Write-Host "3/3  Personagens (Rocketbox -> 04_ThreeJS\web\personagens; so refaz o que mudou)..."
if (Test-Path "$D\07_Personagens\rocketbox") {
    & $B -b --factory-startup --python "$D\07_Personagens\converter_personagens.py" 2>&1 | Select-String -Pattern '^\[PERSONAGENS\]' | ForEach-Object { $_.Line }
} else { Write-Host "     (pasta 07_Personagens\rocketbox nao existe; mantidos os .glb atuais - ver 07_Personagens\LEIA-ME.md)" }
Write-Host "Pronto. Para ver no navegador: 04_ThreeJS\web\iniciar_servidor.bat"
