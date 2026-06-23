param(
    [string]$OutputRoot = "output",
    [string]$FfmpegPath = $env:FFMPEG_PATH,
    [string]$FfprobePath = $env:FFPROBE_PATH
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))

function Resolve-OutputRoot([string]$PathText) {
    if ([System.IO.Path]::IsPathRooted($PathText)) {
        $resolved = [System.IO.Path]::GetFullPath($PathText)
    } else {
        $resolved = [System.IO.Path]::GetFullPath((Join-Path $scriptDir $PathText))
    }
    $allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "output"))
    if (-not $resolved.StartsWith($allowedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Output path must stay under $allowedRoot : $resolved"
    }
    return $resolved
}

function Resolve-Tool([string]$PathText, [string]$ExeName) {
    if (-not [string]::IsNullOrWhiteSpace($PathText)) {
        return $PathText
    }
    $candidate = Join-Path $repoRoot ".tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\$ExeName"
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }
    return $ExeName
}

function Get-ImageSize([string]$ImagePath, [string]$FfprobeExe) {
    $sizeText = & $FfprobeExe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 $ImagePath
    if ($LASTEXITCODE -ne 0) {
        throw "ffprobe failed for $ImagePath"
    }
    return $sizeText.Trim()
}

$ffmpeg = Resolve-Tool $FfmpegPath "ffmpeg.exe"
$ffprobe = Resolve-Tool $FfprobePath "ffprobe.exe"
$outputRootPath = Resolve-OutputRoot $OutputRoot

$cases = @("character_intro", "product_orbit")
foreach ($case in $cases) {
    $caseRoot = Join-Path $outputRootPath $case
    $rawDir = Join-Path $caseRoot "keyframes_raw"
    $enhancedDir = Join-Path $caseRoot "keyframes_enhanced"
    $comparisonDir = Join-Path $caseRoot "comparisons"
    New-Item -ItemType Directory -Force -Path $comparisonDir | Out-Null
    Get-ChildItem -LiteralPath $comparisonDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force

    $rawFrames = Get-ChildItem -LiteralPath $rawDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Sort-Object Name
    foreach ($raw in $rawFrames) {
        $enhanced = Join-Path $enhancedDir $raw.Name
        if (-not (Test-Path -LiteralPath $enhanced)) {
            Write-Output "ROUTE3_COMPARISON_SKIPPED=$($raw.FullName)"
            continue
        }
        $size = Get-ImageSize $raw.FullName $ffprobe
        $comparisonPath = Join-Path $comparisonDir ($raw.BaseName + "_comparison.png")
        $filter = "[0:v]scale=$size[left];[1:v]scale=$size[right];[left][right]hstack=inputs=2[out]"
        & $ffmpeg -y -hide_banner -loglevel error -i $raw.FullName -i $enhanced -filter_complex $filter -map "[out]" -frames:v 1 $comparisonPath
        if ($LASTEXITCODE -ne 0) {
            throw "FFmpeg comparison generation failed for $($raw.FullName)"
        }
        Write-Output "ROUTE3_COMPARISON=$comparisonPath"
    }
}
