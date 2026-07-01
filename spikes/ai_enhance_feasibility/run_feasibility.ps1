param(
    [string]$BlenderPath = $(if ($env:BLENDER_PATH) { $env:BLENDER_PATH } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }),
    [string]$FfmpegPath = $(if ($env:FFMPEG_PATH) { $env:FFMPEG_PATH } else { "E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe" }),
    [string]$FfprobePath = $(if ($env:FFPROBE_PATH) { $env:FFPROBE_PATH } else { "E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe" }),
    [string]$ComfyUrl = $(if ($env:COMFYUI_API_URL) { $env:COMFYUI_API_URL } elseif ($env:COMFYUI_URL) { $env:COMFYUI_URL } else { "http://127.0.0.1:8188" }),
    [string]$PythonPath = ".\.venv\Scripts\python.exe",
    [string]$BestDenoise = "0.25",
    [switch]$IncludeProduct
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))
$python = if ([System.IO.Path]::IsPathRooted($PythonPath)) { $PythonPath } else { Join-Path $repoRoot $PythonPath }

function Invoke-Step([string]$Name, [scriptblock]$Body) {
    Write-Output "AI_GATE_STEP_START=$Name"
    & $Body
    Write-Output "AI_GATE_STEP_DONE=$Name"
}

Invoke-Step "render-character-no-text" {
    & $BlenderPath --background --python (Join-Path $scriptDir "render_no_text.py") -- --case character_intro
}

Invoke-Step "compose-character-raw" {
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath compose-raw --case character_intro
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath overlay-text --case character_intro --input output/character_intro/raw_no_text.mp4 --output output/character_intro/final_with_text_overlay.mp4
}

Invoke-Step "extract-character-keyframes" {
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath extract-keyframes --case character_intro --count 4
}

Invoke-Step "comfy-character-denoise-sweep" {
    & $python (Join-Path $scriptDir "run_comfy_feasibility.py") `
        --comfy-url $ComfyUrl `
        --case character_intro `
        --experiment keyframes `
        --input-dir output/character_intro/keyframes_raw `
        --output-dir output/character_intro/keyframes_ai `
        --report output/character_intro/comfy_keyframes_report.json `
        --denoise 0.25 --denoise 0.35 --denoise 0.50
}

Invoke-Step "compare-character-keyframes" {
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath make-keyframe-comparisons --case character_intro --denoise 0.25 --denoise 0.35 --denoise 0.50
}

Invoke-Step "continuous-character-2s" {
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath extract-continuous --case character_intro --seconds 2
    & $python (Join-Path $scriptDir "run_comfy_feasibility.py") `
        --comfy-url $ComfyUrl `
        --case character_intro `
        --experiment continuous_2s `
        --input-dir output/character_intro/continuous_raw `
        --output-dir output/character_intro/continuous_ai `
        --report output/character_intro/comfy_continuous_2s_report.json `
        --seed-mode fixed `
        --denoise $BestDenoise
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath compose-ai-2s --case character_intro --denoise $BestDenoise
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath make-before-after-2s --case character_intro --denoise $BestDenoise
}

if ($IncludeProduct) {
    Invoke-Step "render-product-no-text" {
        & $BlenderPath --background --python (Join-Path $scriptDir "render_no_text.py") -- --case product_orbit
    }

    Invoke-Step "product-keyframe-denoise-sweep" {
        & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath compose-raw --case product_orbit
        & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath extract-keyframes --case product_orbit --count 4
        & $python (Join-Path $scriptDir "run_comfy_feasibility.py") `
            --comfy-url $ComfyUrl `
            --case product_orbit `
            --experiment keyframes `
            --input-dir output/product_orbit/keyframes_raw `
            --output-dir output/product_orbit/keyframes_ai `
            --report output/product_orbit/comfy_keyframes_report.json `
            --denoise 0.25 --denoise 0.35 --denoise 0.50
        & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath make-keyframe-comparisons --case product_orbit --denoise 0.25 --denoise 0.35 --denoise 0.50
    }
}

Invoke-Step "ffprobe" {
    & $python (Join-Path $scriptDir "video_ops.py") --ffmpeg $FfmpegPath --ffprobe $FfprobePath ffprobe `
        output/character_intro/raw_no_text.mp4 `
        output/character_intro/final_with_text_overlay.mp4 `
        output/character_intro/raw_no_text_2s.mp4 `
        output/character_intro/ai_enhanced_2s.mp4 `
        output/character_intro/ai_enhanced_2s_with_text.mp4 `
        output/character_intro/before_after_2s.mp4
}
