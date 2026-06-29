$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destination = Join-Path $root "output/Steam_Review_Analysis_Submission.zip"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$stream = [System.IO.File]::Open($destination, [System.IO.FileMode]::Create)
$archive = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create)

function Add-EntryFromFileShared {
    param(
        [System.IO.Compression.ZipArchive]$Archive,
        [string]$Source,
        [string]$EntryName
    )
    $entry = $Archive.CreateEntry($EntryName.Replace("\", "/"), [System.IO.Compression.CompressionLevel]::Optimal)
    $entryStream = $entry.Open()
    $fileStream = [System.IO.File]::Open($Source, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $fileStream.CopyTo($entryStream)
    }
    finally {
        $fileStream.Dispose()
        $entryStream.Dispose()
    }
}

try {
    $rootFiles = @(
        "README.md", "SUBMISSION_CHECKLIST.md", "project_metadata.json",
        "requirements.txt", "requirements-local.txt", "requirements-dashboard.txt",
        "requirements-spark.txt", "runtime.txt"
    )
    foreach ($relative in $rootFiles) {
        $source = Join-Path $root $relative
        Add-EntryFromFileShared -Archive $archive -Source $source -EntryName $relative
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
                Add-EntryFromFileShared -Archive $archive -Source $_.FullName -EntryName $entry
            }
    }

    $finalWord = "output/docx/Steam_Review_Analysis_Final_Report_LargeFont.docx"
    $source = Join-Path $root $finalWord
    Add-EntryFromFileShared -Archive $archive -Source $source -EntryName $finalWord

    foreach ($tool in @("tools/build_report.py", "tools/build_word_report.py", "tools/local_reference_analysis.py")) {
        $source = Join-Path $root $tool
        Add-EntryFromFileShared -Archive $archive -Source $source -EntryName $tool
    }
}
finally {
    $archive.Dispose()
    $stream.Dispose()
}

Get-Item $destination | Select-Object FullName, Length, LastWriteTime
