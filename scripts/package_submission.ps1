$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destination = Join-Path $root "output/Steam_Review_Analysis_Submission.zip"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$stream = [System.IO.File]::Open($destination, [System.IO.FileMode]::Create)
$archive = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create)

try {
    $rootFiles = @(
        "README.md", "SUBMISSION_CHECKLIST.md", "project_metadata.json",
        "requirements.txt", "requirements-local.txt", "requirements-dashboard.txt"
    )
    foreach ($relative in $rootFiles) {
        $source = Join-Path $root $relative
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive, $source, $relative.Replace("\", "/"),
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }

    $directoryMap = @{
        "src" = "src"; "sql" = "sql"; "scripts" = "scripts";
        "dashboard" = "dashboard"; "tests" = "tests";
        "output/pdf" = "output/pdf"; "output/figures" = "output/figures";
        "output/results" = "output/results"
    }
    foreach ($key in $directoryMap.Keys) {
        $sourceRoot = Join-Path $root $key
        Get-ChildItem -LiteralPath $sourceRoot -Recurse -File |
            Where-Object { $_.Extension -ne ".pyc" -and $_.FullName -notmatch "__pycache__" } |
            ForEach-Object {
                $suffix = $_.FullName.Substring($sourceRoot.Length).TrimStart("\", "/")
                $entry = ($directoryMap[$key].TrimEnd("/") + "/" + $suffix).Replace("\", "/")
                [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                    $archive, $_.FullName, $entry,
                    [System.IO.Compression.CompressionLevel]::Optimal
                ) | Out-Null
            }
    }

    foreach ($tool in @("tools/build_report.py", "tools/local_reference_analysis.py")) {
        $source = Join-Path $root $tool
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive, $source, $tool, [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}
finally {
    $archive.Dispose()
    $stream.Dispose()
}

Get-Item $destination | Select-Object FullName, Length, LastWriteTime
