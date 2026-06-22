param(
    [string]$Project = "projects/character_intro.json",
    [string]$FfmpegPath = "ffmpeg"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-SpikePath([string]$PathText) {
    if ([System.IO.Path]::IsPathRooted($PathText)) {
        return [System.IO.Path]::GetFullPath($PathText)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $scriptDir $PathText))
}

function Assert-Under([string]$PathText, [string]$RootText) {
    $path = [System.IO.Path]::GetFullPath($PathText)
    $root = [System.IO.Path]::GetFullPath($RootText)
    if (-not $path.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path must stay under $root : $path"
    }
}

$projectPath = Resolve-SpikePath $Project
Assert-Under $projectPath $scriptDir
$projectJson = Get-Content -Raw -LiteralPath $projectPath | ConvertFrom-Json

$framesDir = Resolve-SpikePath ([string]$projectJson.output.frames_dir)
$outputPath = Resolve-SpikePath ([string]$projectJson.output.video_path)
$outputRoot = Join-Path $scriptDir "output"
Assert-Under $framesDir $outputRoot
Assert-Under $outputPath $outputRoot

$fps = [int]$projectJson.fps
$inputPattern = Join-Path $framesDir "%04d.png"
$outputDir = Split-Path -Parent $outputPath
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$timer = [System.Diagnostics.Stopwatch]::StartNew()

& $FfmpegPath `
    -y `
    -framerate $fps `
    -i $inputPattern `
    -c:v libx264 `
    -pix_fmt yuv420p `
    -movflags +faststart `
    -crf 18 `
    $outputPath

$exitCode = $LASTEXITCODE
$timer.Stop()
if ($exitCode -ne 0) {
    throw "FFmpeg failed with exit code $exitCode"
}

Write-Output ("ROUTE2_FFMPEG_SECONDS={0:N2}" -f $timer.Elapsed.TotalSeconds)
Write-Output "ROUTE2_PROJECT=$projectPath"
Write-Output "ROUTE2_MP4=$outputPath"
Write-Output "ROUTE2_FPS=$fps"
