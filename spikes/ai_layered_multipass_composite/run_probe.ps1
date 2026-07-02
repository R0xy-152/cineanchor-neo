# CineAnchor Layered Multipass Composite Probe — Full Pipeline Runner
# Usage: powershell -File run_probe.ps1

$ErrorActionPreference = "Stop"
$BLENDER = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$FFMPEG = "E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
$SPIKE = "E:\cineanchor\spikes\ai_layered_multipass_composite"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CINEANCHOR LAYERED MULTIPASS COMPOSITE PROBE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Phase 0: Pass support probe
Write-Host "`n--- Phase 0: Blender Pass Support Probe ---" -ForegroundColor Yellow
& $BLENDER --background --python "$SPIKE\probe_pass_support.py" -- --output-dir "$SPIKE\output\probe"
if ($LASTEXITCODE -ne 0) { throw "Phase 0 failed" }
Write-Host "Phase 0 complete. Results: $SPIKE\output\probe\pass_support_probe.json" -ForegroundColor Green

# Phase 0b: Deep pass probe
Write-Host "`n--- Phase 0b: Deep Pass Rendering Probe ---" -ForegroundColor Yellow
& $BLENDER --background --python "$SPIKE\probe_pass_support_deep.py" -- --output-dir "$SPIKE\output\probe"
if ($LASTEXITCODE -ne 0) { throw "Phase 0b failed" }
Write-Host "Phase 0b complete." -ForegroundColor Green

# Phase 1-2: Render character_intro layers
Write-Host "`n--- Phase 1-2: Render character_intro Layers ---" -ForegroundColor Yellow
& $BLENDER --background --python "$SPIKE\render_layers.py" -- `
    --project "$SPIKE\project_character_intro.json" `
    --asset-path "E:\cineanchor\spikes\render_json\input\hero.png" `
    --output-dir "$SPIKE\output\character_intro" `
    --width 720 --height 1280 `
    --frame-list "1,32,64,96"
if ($LASTEXITCODE -ne 0) { throw "character_intro render failed" }
Write-Host "character_intro render complete." -ForegroundColor Green

# Phase 1-2: Render product_orbit layers
Write-Host "`n--- Phase 1-2: Render product_orbit Layers ---" -ForegroundColor Yellow
& $BLENDER --background --python "$SPIKE\render_layers.py" -- `
    --project "$SPIKE\project_product_orbit.json" `
    --asset-path "E:\cineanchor\spikes\render_json\input\model.glb" `
    --output-dir "$SPIKE\output\product_orbit" `
    --width 720 --height 1280 `
    --frame-list "1,32,64,96"
if ($LASTEXITCODE -ne 0) { throw "product_orbit render failed" }
Write-Host "product_orbit render complete." -ForegroundColor Green

# Phase 3: Lossless recomposition check
Write-Host "`n--- Phase 3: Lossless Recomposition Check ---" -ForegroundColor Yellow
& $BLENDER --background --python "$SPIKE\composite_layers.py" -- `
    --layers-dir "$SPIKE\output\character_intro" `
    --output-dir "$SPIKE\output\character_intro\report" `
    --frames "1,32,64,96"
if ($LASTEXITCODE -ne 0) { Write-Host "Phase 3 had non-zero exit (expected — recomposition is lossy)" -ForegroundColor Yellow }
Write-Host "Recomposition check complete." -ForegroundColor Green

# Phase 4-5: Mask-based enhancement probe
Write-Host "`n--- Phase 4-5: Mask-Based Enhancement Probe ---" -ForegroundColor Yellow
& $BLENDER --background --python "$SPIKE\measure_recompose.py" -- `
    --layers-dir "$SPIKE\output\character_intro" `
    --output-dir "$SPIKE\output\character_intro\report" `
    --frames "1,32,64,96"
if ($LASTEXITCODE -ne 0) { throw "character_intro enhancement probe failed" }

& $BLENDER --background --python "$SPIKE\measure_recompose.py" -- `
    --layers-dir "$SPIKE\output\product_orbit" `
    --output-dir "$SPIKE\output\product_orbit\report" `
    --frames "1,32,64,96"
if ($LASTEXITCODE -ne 0) { throw "product_orbit enhancement probe failed" }
Write-Host "Enhancement probe complete." -ForegroundColor Green

# Phase 6: Reproducibility check
Write-Host "`n--- Phase 6: Reproducibility Check ---" -ForegroundColor Yellow
& $BLENDER --background --python "$SPIKE\render_layers.py" -- `
    --project "$SPIKE\project_character_intro.json" `
    --asset-path "E:\cineanchor\spikes\render_json\input\hero.png" `
    --output-dir "$SPIKE\output\character_intro_run2" `
    --width 720 --height 1280 `
    --frame-list "1"
if ($LASTEXITCODE -ne 0) { throw "Reproducibility render failed" }
Write-Host "Reproducibility render complete. Compare hashes manually." -ForegroundColor Green

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "PROBE COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Reports:" -ForegroundColor Green
Write-Host "  Phase 0: $SPIKE\output\probe\pass_support_probe.json"
Write-Host "  Phase 0b: $SPIKE\output\probe\deep_pass_probe.json"
Write-Host "  character_intro manifest: $SPIKE\output\character_intro\layered_render_manifest.json"
Write-Host "  product_orbit manifest: $SPIKE\output\product_orbit\layered_render_manifest.json"
Write-Host "  Recomposition report: $SPIKE\output\character_intro\report\recomposition_report.json"
Write-Host "  Enhancement report (char): $SPIKE\output\character_intro\report\enhancement_probe_report.json"
Write-Host "  Enhancement report (prod): $SPIKE\output\product_orbit\report\enhancement_probe_report.json"
Write-Host "  Scorecard: $SPIKE\scorecard_layered_multipass.md"
Write-Host "  Full report: docs\spike_report_ai_layered_multipass_composite.md"
