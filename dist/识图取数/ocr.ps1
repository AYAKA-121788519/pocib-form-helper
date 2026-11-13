# Windows.Media.Ocr wrapper (system built-in OCR, nothing to install).
#
# Single image:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ocr.ps1 -Path x.png -Out y.json [-Lang zh-Hans-CN]
# Batch (one process, many images) - manifest is a JSON array of {id,path,lang}:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ocr.ps1 -Manifest m.json -Out y.json
#
# Output JSON: { ok, results:[{ id, ok, lang, width, height, lines:[{text,x,y,w,h,words:[...]}] }] }
param(
  [string]$Path,
  [string]$Manifest,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$Lang = "zh-Hans-CN"
)

$ErrorActionPreference = "Stop"

function Write-Result($obj) {
  $json = $obj | ConvertTo-Json -Depth 10 -Compress
  [System.IO.File]::WriteAllText($Out, $json, (New-Object System.Text.UTF8Encoding($false)))
}

try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null

  $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
      $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
      $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]

  function Await($op, $type) {
    $m = $asTaskGeneric.MakeGenericMethod($type)
    $t = $m.Invoke($null, @($op))
    $t.Wait(-1) | Out-Null
    $t.Result
  }

  $null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
  $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
  $null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
  $null = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]

  $engines = @{}
  function Get-Engine($tag) {
    if ($engines.ContainsKey($tag)) { return $engines[$tag] }
    $e = $null
    try { $e = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($tag)) } catch {}
    if ($null -eq $e) { $e = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages() }
    $engines[$tag] = $e
    return $e
  }

  function Recognize($fullPath, $tag, $id) {
    try {
      $full = (Resolve-Path -LiteralPath $fullPath).Path
      $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($full)) ([Windows.Storage.StorageFile])
      $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
      $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
      $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

      $engine = Get-Engine $tag
      if ($null -eq $engine) { return [pscustomobject]@{ id = $id; ok = $false; error = "no OCR engine" } }

      $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

      $lines = @()
      foreach ($ln in $result.Lines) {
        $words = @()
        $minX = [double]::MaxValue; $minY = [double]::MaxValue; $maxX = 0; $maxY = 0
        foreach ($w in $ln.Words) {
          $r = $w.BoundingRect
          $words += [pscustomobject]@{ text = $w.Text; x = [int]$r.X; y = [int]$r.Y; w = [int]$r.Width; h = [int]$r.Height }
          if ($r.X -lt $minX) { $minX = $r.X }
          if ($r.Y -lt $minY) { $minY = $r.Y }
          if (($r.X + $r.Width) -gt $maxX) { $maxX = $r.X + $r.Width }
          if (($r.Y + $r.Height) -gt $maxY) { $maxY = $r.Y + $r.Height }
        }
        if ($words.Count -eq 0) { $minX = 0; $minY = 0 }
        $lines += [pscustomobject]@{
          text  = $ln.Text
          x     = [int]$minX; y = [int]$minY
          w     = [int]($maxX - $minX); h = [int]($maxY - $minY)
          words = $words
        }
      }

      return [pscustomobject]@{
        id     = $id
        ok     = $true
        lang   = $engine.RecognizerLanguage.LanguageTag
        width  = [int]$decoder.PixelWidth
        height = [int]$decoder.PixelHeight
        lines  = $lines
      }
    }
    catch {
      return [pscustomobject]@{ id = $id; ok = $false; error = $_.Exception.Message }
    }
  }

  $results = @()
  if ($Manifest) {
    $items = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($it in $items) {
      $tag = if ($it.lang) { $it.lang } else { $Lang }
      $results += Recognize $it.path $tag $it.id
    }
  }
  else {
    $results += Recognize $Path $Lang "0"
  }

  Write-Result ([pscustomobject]@{ ok = $true; results = $results })
}
catch {
  Write-Result @{ ok = $false; error = $_.Exception.Message }
}
