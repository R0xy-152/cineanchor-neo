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
$manifestPath = Join-Path $outputRootPath "keyframes_manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Manifest not found: $manifestPath"
}

$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
foreach ($case in @("character_intro", "product_orbit")) {
    $caseRoot = Join-Path $outputRootPath $case
    $rawDir = Join-Path $caseRoot "keyframes_raw"
    $referenceDir = Join-Path $caseRoot "keyframes_reference"
    $comparisonDir = Join-Path $caseRoot "comparisons"
    $enhancedVideo = Join-Path $caseRoot "enhanced_ffmpeg.mp4"
    if (-not (Test-Path -LiteralPath $enhancedVideo)) {
        throw "Enhanced MP4 not found for ${case}: $enhancedVideo"
    }
    New-Item -ItemType Directory -Force -Path $comparisonDir | Out-Null
    Get-ChildItem -LiteralPath $comparisonDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force

    $caseEntries = @($manifest | Where-Object { $_.case -eq $case } | Sort-Object frame_index)
    foreach ($entry in $caseEntries) {
        $raw = Join-Path $rawDir ("frame_{0:D2}.png" -f [int]$entry.frame_index)
        $reference = Join-Path $referenceDir ("frame_{0:D2}.png" -f [int]$entry.frame_index)
        if (-not (Test-Path -LiteralPath $raw)) {
            throw "Raw frame not found: $raw"
        }
        if (-not (Test-Path -LiteralPath $reference)) {
            throw "Reference frame not found: $reference"
        }

        $timeText = ([double]$entry.source_time_seconds).ToString("0.###", [System.Globalization.CultureInfo]::InvariantCulture)
        $ffmpegFrame = Join-Path $comparisonDir ("frame_{0:D2}_ffmpeg_frame.png" -f [int]$entry.frame_index)
        & $ffmpeg -y -hide_banner -loglevel error -ss $timeText -i $enhancedVideo -frames:v 1 $ffmpegFrame
        if ($LASTEXITCODE -ne 0) {
            throw "FFmpeg frame extraction failed for $enhancedVideo at $timeText"
        }

        $size = Get-ImageSize $raw $ffprobe
        $rawRefPath = Join-Path $comparisonDir ("frame_{0:D2}_raw_vs_reference.png" -f [int]$entry.frame_index)
        $rawFfmpegPath = Join-Path $comparisonDir ("frame_{0:D2}_raw_vs_ffmpeg.png" -f [int]$entry.frame_index)
        $threeWayPath = Join-Path $comparisonDir ("frame_{0:D2}_raw_reference_ffmpeg.png" -f [int]$entry.frame_index)

        $filterRawRef = "[0:v]scale=${size}[left];[1:v]scale=${size}[right];[left][right]hstack=inputs=2[out]"
        & $ffmpeg -y -hide_banner -loglevel error -i $raw -i $reference -filter_complex $filterRawRef -map "[out]" -frames:v 1 $rawRefPath
        if ($LASTEXITCODE -ne 0) {
            throw "Raw/reference comparison failed for $raw"
        }

        $filterRawFfmpeg = "[0:v]scale=${size}[left];[1:v]scale=${size}[right];[left][right]hstack=inputs=2[out]"
        & $ffmpeg -y -hide_banner -loglevel error -i $raw -i $ffmpegFrame -filter_complex $filterRawFfmpeg -map "[out]" -frames:v 1 $rawFfmpegPath
        if ($LASTEXITCODE -ne 0) {
            throw "Raw/FFmpeg comparison failed for $raw"
        }

        $filterThree = "[0:v]scale=${size}[a];[1:v]scale=${size}[b];[2:v]scale=${size}[c];[a][b][c]hstack=inputs=3[out]"
        & $ffmpeg -y -hide_banner -loglevel error -i $raw -i $reference -i $ffmpegFrame -filter_complex $filterThree -map "[out]" -frames:v 1 $threeWayPath
        if ($LASTEXITCODE -ne 0) {
            throw "Three-way comparison failed for $raw"
        }

        Write-Output "ROUTE3B_COMPARISON=$rawRefPath"
        Write-Output "ROUTE3B_COMPARISON=$rawFfmpegPath"
        Write-Output "ROUTE3B_COMPARISON=$threeWayPath"
    }
}
