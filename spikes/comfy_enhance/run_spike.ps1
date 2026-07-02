param(
    [string]$CharacterMp4 = "",
    [string]$ProductMp4 = "",
    [string]$ComfyUrl = $(if ($env:COMFYUI_API_URL) { $env:COMFYUI_API_URL } elseif ($env:COMFYUI_URL) { $env:COMFYUI_URL } else { "" }),
    [string]$Workflow = "workflows/conservative_sdxl_img2img_api.json",
    [string]$Checkpoint = "",
    [string]$FfmpegPath = $env:FFMPEG_PATH,
    [string]$FfprobePath = $env:FFPROBE_PATH,
    [string]$PythonPath = $env:PYTHON_PATH
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))

function Resolve-Python([string]$PathText) {
    if (-not [string]::IsNullOrWhiteSpace($PathText)) {
        return $PathText
    }
    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    return "python"
}

$extractArgs = @()
if ($CharacterMp4) { $extractArgs += @("-CharacterMp4", $CharacterMp4) }
if ($ProductMp4) { $extractArgs += @("-ProductMp4", $ProductMp4) }
if ($FfmpegPath) { $extractArgs += @("-FfmpegPath", $FfmpegPath) }
if ($FfprobePath) { $extractArgs += @("-FfprobePath", $FfprobePath) }

& (Join-Path $scriptDir "extract_keyframes.ps1") @extractArgs

$python = Resolve-Python $PythonPath
$comfyArgs = @((Join-Path $scriptDir "run_comfy_enhance.py"), "--workflow", $Workflow)
if ($ComfyUrl) { $comfyArgs += @("--comfy-url", $ComfyUrl) }
if ($Checkpoint) { $comfyArgs += @("--checkpoint", $Checkpoint) }
& $python @comfyArgs

$comparisonArgs = @()
if ($FfmpegPath) { $comparisonArgs += @("-FfmpegPath", $FfmpegPath) }
if ($FfprobePath) { $comparisonArgs += @("-FfprobePath", $FfprobePath) }
& (Join-Path $scriptDir "make_comparisons.ps1") @comparisonArgs
