param(
    [string]$OutputRoot = "output",
    [string]$ColorParamsPath = "",
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

function Get-SourceFromManifest([string]$Case, [string]$OutputRootPath) {
    $manifestPath = Join-Path $OutputRootPath "keyframes_manifest.json"
    if (Test-Path -LiteralPath $manifestPath) {
        $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        $entry = @($manifest | Where-Object { $_.case -eq $Case } | Select-Object -First 1)
        if ($entry.Count -gt 0 -and $entry[0].source_mp4) {
            return [string]$entry[0].source_mp4
        }
    }
    return Find-TemplateMp4 $Case
}

function Format-Float([double]$Value) {
    return $Value.ToString("0.####", [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-VideoProbe([string]$VideoPath, [string]$FfprobeExe) {
    $jsonText = & $FfprobeExe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,avg_frame_rate,nb_frames,duration -show_entries format=duration,size -of json $VideoPath
    if ($LASTEXITCODE -ne 0) {
        throw "ffprobe failed for $VideoPath"
    }
    return $jsonText | ConvertFrom-Json
}

$ffmpeg = Resolve-Tool $FfmpegPath "ffmpeg.exe"
$ffprobe = Resolve-Tool $FfprobePath "ffprobe.exe"
$outputRootPath = Resolve-OutputRoot $OutputRoot
if ([string]::IsNullOrWhiteSpace($ColorParamsPath)) {
    $ColorParamsPath = Join-Path $outputRootPath "color_params.json"
}
if (-not (Test-Path -LiteralPath $ColorParamsPath)) {
    throw "Color params not found: $ColorParamsPath"
}

$colorParams = Get-Content -Raw -LiteralPath $ColorParamsPath | ConvertFrom-Json
if ($colorParams.status -ne "PASS") {
    throw "Color params status is not PASS: $($colorParams.status)"
}

$results = @()
foreach ($case in @("character_intro", "product_orbit")) {
    $caseRoot = Join-Path $outputRootPath $case
    New-Item -ItemType Directory -Force -Path $caseRoot | Out-Null
    $inputVideo = Get-SourceFromManifest $case $outputRootPath
    $outputVideo = Join-Path $caseRoot "enhanced_ffmpeg.mp4"
    $caseParams = $colorParams.color_params.$case
    if (-not $caseParams) {
        throw "Missing color params for $case"
    }

    $brightness = Format-Float ([double]$caseParams.brightness)
    $contrast = Format-Float ([double]$caseParams.contrast)
    $saturation = Format-Float ([double]$caseParams.saturation)
    $gamma = Format-Float ([double]$caseParams.gamma)
    $unsharpAmount = Format-Float ([double]$caseParams.unsharp_luma_amount)
    $filter = "eq=brightness=$brightness`:contrast=$contrast`:saturation=$saturation`:gamma=$gamma,unsharp=5:5:$unsharpAmount`:3:3:0.12"

    & $ffmpeg -y -hide_banner -loglevel error -i $inputVideo -map 0:v:0 -map 0:a? -vf $filter -c:v libx264 -pix_fmt yuv420p -crf 18 -preset veryfast -c:a copy -movflags +faststart $outputVideo
    if ($LASTEXITCODE -ne 0) {
        throw "FFmpeg enhancement failed for $case"
    }

    $sourceProbe = Get-VideoProbe $inputVideo $ffprobe
    $enhancedProbe = Get-VideoProbe $outputVideo $ffprobe
    $result = [PSCustomObject]@{
        case = $case
        input_video = $inputVideo
        output_video = $outputVideo
        filter = $filter
        source_probe = $sourceProbe
        enhanced_probe = $enhancedProbe
    }
    $results += $result
    Write-Output "ROUTE3B_FFMPEG_OUTPUT=$outputVideo"
    Write-Output "ROUTE3B_FFMPEG_FILTER=$filter"
}

$reportPath = Join-Path $outputRootPath "ffmpeg_enhance_report.json"
[PSCustomObject]@{
    status = "PASS"
    ffmpeg = $ffmpeg
    ffprobe = $ffprobe
    results = $results
} | ConvertTo-Json -Depth 12 | Set-Content -Encoding UTF8 -LiteralPath $reportPath
Write-Output "ROUTE3B_FFMPEG_REPORT=$reportPath"
