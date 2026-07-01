param(
    [string]$BlenderPath = $(if ($env:BLENDER_PATH) { $env:BLENDER_PATH } else { "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" }),
    [string]$PythonPath = $(if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }),
    [string]$ComfyUrl = $(if ($env:COMFYUI_API_URL) { $env:COMFYUI_API_URL } elseif ($env:COMFYUI_URL) { $env:COMFYUI_URL } else { "http://127.0.0.1:8188" }),
    [switch]$IncludeProduct
)

$ErrorActionPreference = "Stop"

function Invoke-Gate2 {
    param([string[]]$Command)
    Write-Host ("`n> " + ($Command -join " "))
    & $Command[0] @($Command | Select-Object -Skip 1)
}

Invoke-Gate2 @($PythonPath, "-m", "py_compile",
    "spikes\ai_enhance_gate2\render_structural.py",
    "spikes\ai_enhance_gate2\video_ops.py",
    "spikes\ai_enhance_gate2\run_comfy_gate2.py")

Invoke-RestMethod -Uri "$ComfyUrl/system_stats" -TimeoutSec 10 | Out-Null

Invoke-Gate2 @($BlenderPath, "--background", "--python", ".\spikes\ai_enhance_gate2\render_structural.py", "--", "--case", "character_intro")
Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "compose-raw", "--case", "character_intro")
Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "extract-keyframes", "--case", "character_intro", "--count", "4")
Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "make-canny",
    "--input-dir", "output/character_intro/keyframes/raw",
    "--output-dir", "output/character_intro/keyframes/canny")

Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\run_comfy_gate2.py",
    "--mode", "plain",
    "--case", "character_intro",
    "--experiment", "keyframes_plain",
    "--input-dir", "output/character_intro/keyframes/raw",
    "--output-dir", "output/character_intro/keyframes/plain_img2img",
    "--report", "output/character_intro/comfy_keyframes_plain_report.json",
    "--denoise", "0.25", "--denoise", "0.35", "--denoise", "0.45")

Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\run_comfy_gate2.py",
    "--mode", "control",
    "--control-method", "canny",
    "--case", "character_intro",
    "--experiment", "keyframes_control_canny",
    "--input-dir", "output/character_intro/keyframes/raw",
    "--control-dir", "output/character_intro/keyframes/canny",
    "--output-dir", "output/character_intro/keyframes/control_canny",
    "--report", "output/character_intro/comfy_keyframes_control_canny_report.json",
    "--denoise", "0.25", "--denoise", "0.35", "--denoise", "0.45")

foreach ($denoise in @("0.25", "0.35", "0.45")) {
    $label = "denoise_" + $denoise.Replace(".", "_")
    Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "composite-protected",
        "--raw-dir", "output/character_intro/keyframes/raw",
        "--ai-dir", "output/character_intro/keyframes/control_canny/$label",
        "--mask-dir", "output/character_intro/keyframes/mask",
        "--output-dir", "output/character_intro/keyframes/protected_canny/$label")
}

Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "make-keyframe-grid",
    "--case", "character_intro", "--method", "canny",
    "--denoise", "0.25", "--denoise", "0.35", "--denoise", "0.45")

Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "extract-continuous", "--case", "character_intro", "--seconds", "2")
Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "make-canny",
    "--input-dir", "output/character_intro/continuous/raw",
    "--output-dir", "output/character_intro/continuous/canny")

Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\run_comfy_gate2.py",
    "--mode", "control",
    "--control-method", "canny",
    "--case", "character_intro",
    "--experiment", "continuous_2s_control_canny",
    "--input-dir", "output/character_intro/continuous/raw",
    "--control-dir", "output/character_intro/continuous/canny",
    "--output-dir", "output/character_intro/continuous/control_canny",
    "--report", "output/character_intro/comfy_continuous_2s_control_canny_report.json",
    "--seed-mode", "fixed",
    "--denoise", "0.25")

Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "composite-protected",
    "--raw-dir", "output/character_intro/continuous/raw",
    "--ai-dir", "output/character_intro/continuous/control_canny/denoise_0_25",
    "--mask-dir", "output/character_intro/continuous/mask",
    "--output-dir", "output/character_intro/continuous/protected_canny/denoise_0_25")

Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "compose-frames",
    "--frames-dir", "output/character_intro/continuous/control_canny/denoise_0_25",
    "--fps", "24",
    "--output", "output/character_intro/control_canny_2s_denoise_0_25.mp4")
Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "compose-frames",
    "--frames-dir", "output/character_intro/continuous/protected_canny/denoise_0_25",
    "--fps", "24",
    "--output", "output/character_intro/protected_canny_2s_denoise_0_25.mp4")
Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "make-before-after-2s",
    "--case", "character_intro",
    "--method", "canny",
    "--denoise", "0.25")

if ($IncludeProduct) {
    Invoke-Gate2 @($BlenderPath, "--background", "--python", ".\spikes\ai_enhance_gate2\render_structural.py", "--", "--case", "product_orbit", "--skip-data-passes")
    Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "compose-raw", "--case", "product_orbit")
    Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "extract-keyframes", "--case", "product_orbit", "--count", "4")
    Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\video_ops.py", "make-canny",
        "--input-dir", "output/product_orbit/keyframes/raw",
        "--output-dir", "output/product_orbit/keyframes/canny")
    Invoke-Gate2 @($PythonPath, ".\spikes\ai_enhance_gate2\run_comfy_gate2.py",
        "--mode", "control",
        "--control-method", "canny",
        "--case", "product_orbit",
        "--experiment", "keyframes_control_canny",
        "--input-dir", "output/product_orbit/keyframes/raw",
        "--control-dir", "output/product_orbit/keyframes/canny",
        "--output-dir", "output/product_orbit/keyframes/control_canny",
        "--report", "output/product_orbit/comfy_keyframes_control_canny_report.json",
        "--denoise", "0.25", "--denoise", "0.35", "--denoise", "0.45")
}
