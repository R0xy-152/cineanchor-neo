param(
    [string]$CharacterMp4 = "",
    [string]$ProductMp4 = "",
    [int]$FramesPerVideo = 4,
    [string]$OutputRoot = "output",
    [string]$FfmpegPath = $env:FFMPEG_PATH,
    [string]$FfprobePath = $env:FFPROBE_PATH
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))

function Resolve-UnderRepo([string]$PathText, [bool]$MustExist = $false) {
    if ([string]::IsNullOrWhiteSpace($PathText)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($PathText)) {
        $resolved = [System.IO.Path]::GetFullPath($PathText)
    } else {
        $resolved = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PathText))
    }
    if (-not $resolved.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path must stay under repo root $repoRoot : $resolved"
    }
    if ($MustExist -and -not (Test-Path -LiteralPath $resolved)) {
        throw "Path not found: $resolved"
    }
    return $resolved
}

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

function Find-TemplateMp4([string]$Template) {
    $webRoot = Join-Path $repoRoot "spikes\render_json\output\web"
    if (Test-Path -LiteralPath $webRoot) {
        $matches = @(Get-ChildItem -LiteralPath $webRoot -Directory |
            ForEach-Object {
                $projectPath = Join-Path $_.FullName "project.json"
                $videoPath = Join-Path $_.FullName "final.mp4"
                if ((Test-Path -LiteralPath $projectPath) -and (Test-Path -LiteralPath $videoPath)) {
                    $project = Get-Content -Raw -LiteralPath $projectPath | ConvertFrom-Json
                    if ([string]$project.template -eq $Template) {
                        [PSCustomObject]@{
                            Video = $videoPath
                            LastWriteTime = (Get-Item -LiteralPath $videoPath).LastWriteTime
                        }
                    }
                }
            } | Sort-Object LastWriteTime -Descending)
        if ($matches.Count -gt 0) {
            return $matches[0].Video
        }
    }

    $fallback = Join-Path $repoRoot "spikes\render_json\output\$Template\final.mp4"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }
    throw "No MP4 found for template $Template"
}

function Get-DurationSeconds([string]$VideoPath, [string]$FfprobeExe) {
    $durationText = & $FfprobeExe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $VideoPath
    if ($LASTEXITCODE -ne 0) {
        throw "ffprobe failed for $VideoPath"
    }
    return [double]::Parse($durationText.Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-SampleTimes([double]$Duration, [int]$Count) {
    $times = @()
    for ($i = 0; $i -lt $Count; $i++) {
        $centered = (($i + 0.5) / $Count) * $Duration
        $safe = [Math]::Min($centered, [Math]::Max(0, $Duration - 0.05))
        $times += $safe
    }
    return $times
}

if ($FramesPerVideo -lt 1) {
    throw "FramesPerVideo must be at least 1"
}

$ffmpeg = Resolve-Tool $FfmpegPath "ffmpeg.exe"
$ffprobe = Resolve-Tool $FfprobePath "ffprobe.exe"
$outputRootPath = Resolve-OutputRoot $OutputRoot
New-Item -ItemType Directory -Force -Path $outputRootPath | Out-Null

$cases = @(
    [PSCustomObject]@{
        Name = "character_intro"
        Input = if ($CharacterMp4) { Resolve-UnderRepo $CharacterMp4 $true } else { Find-TemplateMp4 "character_intro" }
    },
    [PSCustomObject]@{
        Name = "product_orbit"
        Input = if ($ProductMp4) { Resolve-UnderRepo $ProductMp4 $true } else { Find-TemplateMp4 "product_orbit" }
    }
)

$manifest = @()
foreach ($case in $cases) {
    $caseRoot = Join-Path $outputRootPath $case.Name
    $rawDir = Join-Path $caseRoot "keyframes_raw"
    $enhancedDir = Join-Path $caseRoot "keyframes_enhanced"
    $comparisonDir = Join-Path $caseRoot "comparisons"
    New-Item -ItemType Directory -Force -Path $rawDir, $enhancedDir, $comparisonDir | Out-Null

    Get-ChildItem -LiteralPath $rawDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force

    $duration = Get-DurationSeconds $case.Input $ffprobe
    $times = Get-SampleTimes $duration $FramesPerVideo
    for ($i = 0; $i -lt $times.Count; $i++) {
        $frameName = "frame_{0:D2}.png" -f ($i + 1)
        $framePath = Join-Path $rawDir $frameName
        $timeText = $times[$i].ToString("0.###", [System.Globalization.CultureInfo]::InvariantCulture)
        & $ffmpeg -y -hide_banner -loglevel error -ss $timeText -i $case.Input -frames:v 1 $framePath
        if ($LASTEXITCODE -ne 0) {
            throw "FFmpeg keyframe extraction failed for $($case.Name) at $timeText seconds"
        }
        $manifest += [PSCustomObject]@{
            case = $case.Name
            source_mp4 = $case.Input
            frame_index = $i + 1
            source_time_seconds = [Math]::Round($times[$i], 3)
            raw_frame = $framePath
        }
        Write-Output "ROUTE3_KEYFRAME=$framePath"
    }
}

$manifestPath = Join-Path $outputRootPath "keyframes_manifest.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -LiteralPath $manifestPath
Write-Output "ROUTE3_KEYFRAME_MANIFEST=$manifestPath"
