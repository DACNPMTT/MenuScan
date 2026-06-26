param(
    [string]$OutputRoot = "$PSScriptRoot\dataset"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$fixturePath = Join-Path $PSScriptRoot "fixture_samples.json"
$fixtureData = Get-Content -Raw -Encoding UTF8 -Path $fixturePath | ConvertFrom-Json

$assetDir = Join-Path $OutputRoot "assets"
New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
Get-ChildItem -Path $assetDir -File -Filter "ocr-*" | Remove-Item -Force

$fontTitle = New-Object System.Drawing.Font "Arial", 24, ([System.Drawing.FontStyle]::Bold)
$fontBody = New-Object System.Drawing.Font "Arial", 16, ([System.Drawing.FontStyle]::Regular)
$fontSmall = New-Object System.Drawing.Font "Arial", 12, ([System.Drawing.FontStyle]::Regular)
$black = [System.Drawing.Brushes]::Black
$gray = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(115, 115, 115))

function Test-ObjectProperty {
    param(
        [object]$Object,
        [string]$Name
    )

    return $null -ne $Object.PSObject.Properties[$Name]
}

function Get-ObjectPropertyOrDefault {
    param(
        [object]$Object,
        [string]$Name,
        [object]$DefaultValue
    )

    if (Test-ObjectProperty -Object $Object -Name $Name) {
        return $Object.PSObject.Properties[$Name].Value
    }

    return $DefaultValue
}

function Get-ObjectArrayProperty {
    param(
        [object]$Object,
        [string]$Name
    )

    if (-not (Test-ObjectProperty -Object $Object -Name $Name)) {
        return @()
    }

    $value = $Object.PSObject.Properties[$Name].Value
    if ($null -eq $value) {
        return @()
    }

    return @($value)
}

function New-TextPng {
    param(
        [string]$FileName,
        [string]$Title,
        [string[]]$Lines,
        [int]$ColumnCount = 1,
        [bool]$LowQuality = $false,
        [bool]$Skewed = $false,
        [bool]$Dense = $false
    )

    $width = 1200
    $lineHeight = if ($Dense) { 28 } else { 42 }
    $top = 100
    $rowCount = if ($ColumnCount -le 1) {
        $Lines.Length
    } else {
        [Math]::Ceiling($Lines.Length / $ColumnCount)
    }
    $height = [Math]::Max(850, $top + ($rowCount * $lineHeight) + 100)

    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

    if ($Skewed) {
        $graphics.TranslateTransform(38, -18)
        $graphics.RotateTransform(3.5)
    }

    $brush = if ($LowQuality) { $gray } else { $black }
    $bodyFont = if ($Dense) { $fontSmall } else { $fontBody }
    $graphics.DrawString($Title, $fontTitle, $brush, 44, 32)

    $lefts = @(54, 620, 900)
    for ($i = 0; $i -lt $Lines.Length; $i++) {
        $column = if ($ColumnCount -le 1) { 0 } else { $i % $ColumnCount }
        $row = if ($ColumnCount -le 1) { $i } else { [Math]::Floor($i / $ColumnCount) }
        $x = $lefts[$column]
        $y = $top + ($row * $lineHeight)
        $graphics.DrawString($Lines[$i], $bodyFont, $brush, $x, $y)
    }

    if ($LowQuality) {
        $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(235, 235, 235)), 1
        for ($x = 0; $x -lt $width; $x += 37) {
            $graphics.DrawLine($pen, $x, 0, $x + 140, $height)
        }
        $pen.Dispose()
    }

    $path = Join-Path $assetDir $FileName
    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
}

function Write-AsciiBytes {
    param(
        [System.IO.Stream]$Stream,
        [string]$Text
    )

    $bytes = [System.Text.Encoding]::ASCII.GetBytes($Text)
    $Stream.Write($bytes, 0, $bytes.Length)
}

function New-PageJpegBytes {
    param([string]$PageText)

    $width = 1240
    $height = 1600
    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

    $y = 58
    $lines = $PageText -split "`n"
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $font = if ($i -eq 0) { $fontTitle } else { $fontBody }
        $graphics.DrawString($lines[$i], $font, $black, 56, $y)
        $y += if ($i -eq 0) { 54 } else { 38 }
    }

    $memoryStream = New-Object System.IO.MemoryStream
    $bitmap.Save($memoryStream, [System.Drawing.Imaging.ImageFormat]::Jpeg)
    $bytes = $memoryStream.ToArray()

    $memoryStream.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()

    return $bytes
}

function New-SimplePdf {
    param(
        [string]$FileName,
        [string[]]$Pages
    )

    $pageImages = @()
    foreach ($page in $Pages) {
        $pageImages += ,(New-PageJpegBytes -PageText $page)
    }

    $pageWidth = 612
    $pageHeight = 792
    $imageWidth = 1240
    $imageHeight = 1600
    $objectCount = 2 + ($pageImages.Count * 3)
    $memoryStream = New-Object System.IO.MemoryStream
    $offsets = @{}

    Write-AsciiBytes -Stream $memoryStream -Text "%PDF-1.4`n"

    $offsets[1] = $memoryStream.Position
    Write-AsciiBytes -Stream $memoryStream -Text "1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n"

    $kids = New-Object System.Collections.Generic.List[string]
    for ($i = 0; $i -lt $pageImages.Count; $i++) {
        $pageObjectNumber = 3 + ($i * 3)
        $kids.Add("$pageObjectNumber 0 R")
    }

    $offsets[2] = $memoryStream.Position
    Write-AsciiBytes -Stream $memoryStream -Text "2 0 obj`n<< /Type /Pages /Kids [$($kids -join ' ')] /Count $($pageImages.Count) >>`nendobj`n"

    for ($i = 0; $i -lt $pageImages.Count; $i++) {
        $pageObjectNumber = 3 + ($i * 3)
        $contentObjectNumber = $pageObjectNumber + 1
        $imageObjectNumber = $pageObjectNumber + 2
        $imageName = "Im$i"
        $contentStream = "q $pageWidth 0 0 $pageHeight 0 0 cm /$imageName Do Q"
        $contentLength = [System.Text.Encoding]::ASCII.GetByteCount($contentStream)

        $offsets[$pageObjectNumber] = $memoryStream.Position
        Write-AsciiBytes -Stream $memoryStream -Text "$pageObjectNumber 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 $pageWidth $pageHeight] /Resources << /XObject << /$imageName $imageObjectNumber 0 R >> >> /Contents $contentObjectNumber 0 R >>`nendobj`n"

        $offsets[$contentObjectNumber] = $memoryStream.Position
        Write-AsciiBytes -Stream $memoryStream -Text "$contentObjectNumber 0 obj`n<< /Length $contentLength >>`nstream`n$contentStream`nendstream`nendobj`n"

        $imageBytes = $pageImages[$i]
        $offsets[$imageObjectNumber] = $memoryStream.Position
        Write-AsciiBytes -Stream $memoryStream -Text "$imageObjectNumber 0 obj`n<< /Type /XObject /Subtype /Image /Width $imageWidth /Height $imageHeight /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length $($imageBytes.Length) >>`nstream`n"
        $memoryStream.Write($imageBytes, 0, $imageBytes.Length)
        Write-AsciiBytes -Stream $memoryStream -Text "`nendstream`nendobj`n"
    }

    $xrefStart = $memoryStream.Position
    Write-AsciiBytes -Stream $memoryStream -Text "xref`n0 $($objectCount + 1)`n"
    Write-AsciiBytes -Stream $memoryStream -Text "0000000000 65535 f `n"
    for ($objectNumber = 1; $objectNumber -le $objectCount; $objectNumber++) {
        Write-AsciiBytes -Stream $memoryStream -Text ("{0:0000000000} 00000 n `n" -f $offsets[$objectNumber])
    }
    Write-AsciiBytes -Stream $memoryStream -Text "trailer`n<< /Root 1 0 R /Size $($objectCount + 1) >>`nstartxref`n$xrefStart`n%%EOF`n"

    [System.IO.File]::WriteAllBytes((Join-Path $assetDir $FileName), $memoryStream.ToArray())
    $memoryStream.Dispose()
}

function Get-ExpectedPrices {
    param([string[]]$Lines)

    $prices = New-Object System.Collections.Generic.List[string]
    $pricePattern = '(?:\$\d+(?:[.,]\d+)*|\d{4,}(?:[.,]\d+)*(?:\s?(?:VND|USD|EUR|d|D|\u0111|\u0110|K|k))?|\d+(?:[.,]\d+)+(?:\s?(?:VND|USD|EUR|d|D|\u0111|\u0110|K|k))?)'
    foreach ($line in $Lines) {
        foreach ($match in [System.Text.RegularExpressions.Regex]::Matches($line, $pricePattern)) {
            $prices.Add($match.Value)
        }
    }
    return @($prices)
}

$samples = @($fixtureData.image_samples)
foreach ($sample in $samples) {
    New-TextPng `
        -FileName $sample.file `
        -Title $sample.title `
        -Lines @($sample.lines) `
        -ColumnCount (Get-ObjectPropertyOrDefault -Object $sample -Name "column_count" -DefaultValue 1) `
        -LowQuality (Get-ObjectPropertyOrDefault -Object $sample -Name "low_quality" -DefaultValue $false) `
        -Skewed (Get-ObjectPropertyOrDefault -Object $sample -Name "skewed" -DefaultValue $false) `
        -Dense (Get-ObjectPropertyOrDefault -Object $sample -Name "dense" -DefaultValue $false)
}

$pdfSamples = @($fixtureData.pdf_samples)
foreach ($sample in $pdfSamples) {
    New-SimplePdf -FileName $sample.file -Pages @($sample.pages)
}

$groundTruthSamples = New-Object System.Collections.Generic.List[object]
foreach ($sample in $samples) {
    $text = @($sample.title) + @($sample.lines)
    $groundTruthSamples.Add([ordered]@{
        id = $sample.id
        file = "assets/$($sample.file)"
        mime_type = "image/png"
        language = "vi"
        tags = @($sample.tags)
        expected_column_count = Get-ObjectPropertyOrDefault -Object $sample -Name "column_count" -DefaultValue 1
        expected_text = ($text -join "`n")
        expected_lines = $text
        expected_prices = @(Get-ExpectedPrices -Lines @($sample.lines))
        items = @(Get-ObjectArrayProperty -Object $sample -Name "items")
    })
}

foreach ($sample in $pdfSamples) {
    $lines = @()
    foreach ($page in @($sample.pages)) {
        $lines += ($page -split "`n")
    }
    $groundTruthSamples.Add([ordered]@{
        id = $sample.id
        file = "assets/$($sample.file)"
        mime_type = "application/pdf"
        language = "vi"
        tags = @($sample.tags)
        expected_column_count = 1
        expected_text = ($lines -join "`n")
        expected_lines = $lines
        expected_prices = @(Get-ExpectedPrices -Lines $lines)
        items = @()
    })
}

$payload = [ordered]@{
    dataset_version = "menuscan-ocr-benchmark.v1"
    product_context = "foreign_visitor_in_vietnam"
    primary_source_language = "vi"
    target_language_example = "en"
    sample_count = $groundTruthSamples.Count
    license = "Synthetic MenuScan fixtures generated in-repo; no private or copyrighted menu data."
    generated_by = "doc/ocr-benchmark/generate_fixtures.ps1"
    fixture_source = "doc/ocr-benchmark/fixture_samples.json"
    samples = $groundTruthSamples
}

$json = $payload | ConvertTo-Json -Depth 8
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText((Join-Path $OutputRoot "ground_truth.json"), $json, $utf8NoBom)
