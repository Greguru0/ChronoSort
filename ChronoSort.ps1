# I think a rebrand is due. Thanks ChatGPT:
# ChronoSort: Time-Sorted Shit v1.0
# Picscrape v3.0 > FileScrape 2.0 > ChronoSort: Time-Sorted Shit v1.0

# FileScrape v2.0
# 08/21/2023

# Changelog:
# Forked Picscrape v3.0 > FileScrape 2.0
# Updated 08/21/2023
# Changelog v2.0
# Entirely rewritten. Mostly everything is modularized into functions. The output log is much cleaner. There is an error log now.
# The way the script handles looping through the file system should be far more optimized. Instead of looping multiple times, it will only loop once then save things to an array.
# Progress Bars for everything have been added.
# Basically the changelog below (v1.2 can be disregarded. Most of it is irrelevant, now.)
# Fuck Powershell.
# Fuck GPT
# GPT is a Godsend.
# I don't know why. But the values were NOT returning properly in the Import-Source-Files function. They work just before return, then they all break. I think this is something fundamental with Powershell I simply do not understand. Whatever, calling the log at the end from within that function seems to work. Fuck Powershell.


# Changelog V 1.2
# Handle file properties better using Get-AllProperties function. This should allow for more versatile file organization.
# Pretty format with GPT.
# Gives the user the choice to show a date range of files found and shows them

# Things to do:
# Additional function to allow for only checking for existing files, delete, organize, and rename files.
# Give the user an option to power off when finished.

##############

# Set error handling preference
set-psdebug -trace 0
$ErrorActionPreference = "Continue"

# Bypass Execution Policy if not already set
if (-Not (Get-ExecutionPolicy -Scope Process) -eq 'Bypass') {
    Set-ExecutionPolicy Bypass -Scope Process -Force
}

[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") > $null

$oReturn = [System.Windows.Forms.Messagebox]::Show(@"
ChronoSort`n`nThis script is designed to scrape or import files (primarily pictures) from a source directory and organize them into a destination directory based on the date the pictures were taken. `n`nIt allows the user to specify file types to include in the import. `nIt aims to handle duplicate files by checking their hash values (MD5) and will avoid overwriting files with the same name. `n`n It will generate filenames that follow the ISO 8601 date format and include a unique identifier (e.g., "(1)", "(2)", etc.) and a letter, if necessary to reduce any filename conflicts.`n`nLatest Release: 08-21-2023`n-G
"@
, "ChronoSort", 0, 64)

################### Dbug Code:

function High-Light-Message {
    param ($DBUGmessage)
    $originalColors = $host.ui.rawui.BackgroundColor, $host.ui.rawui.ForegroundColor
	Write-Host ""
    $host.ui.rawui.BackgroundColor = "Black"
    $host.ui.rawui.ForegroundColor = "Red"
    Write-Host "Line $($MyInvocation.ScriptLineNumber): $DBUGmessage"
	pause
    $host.ui.rawui.BackgroundColor, $host.ui.rawui.ForegroundColor = $originalColors
	Write-Host ""
	#High-Light-Message -DBUGmessage "Some Text"
}

# The above is old code for debugging. It's useless. It's a fun way to highlight output, but. Whatever.
######################

Function Initialize-Variables {
    [string]$duplicate_Import_Log = ""
    [int]$stepTotal = 0
    [int]$stepNumber = 0
    [int]$successful = 0
    [int]$total_duplicate_count = 0
    [int]$duplicate_group_count = 0
    [hashtable]$folderFileCounts = @{}
    [string]$global:startTime = "`nProcess started: $(Get-Date)`n"
    Write-Host $startTime
    return $stepTotal, $stepNumber, $startTime, $successful, $total_duplicate_count, $duplicate_group_count, $folderFileCounts
}

Function Initialize-Files {
$errorLog = "$pwd\ChronoSort_ERROR-LOG.txt"
$importLog = "$pwd\ChronoSort_Log.txt"

    if (!(Test-Path $importLog)) {
        New-Item $importLog > $null
    }

return $importLog, $errorLog
}

Function Set-SourceDialog {
	Write-Host "`nSelect a Source Folder."
    [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null
    $objForm = New-Object System.Windows.Forms.FolderBrowserDialog
    $objForm.Rootfolder = "Desktop"
    $objForm.Description = "Select Source"
    $Show = $objForm.ShowDialog()

    If ($Show -eq "OK") {
        $source = $objForm.SelectedPath
        Write-Host "Source set to: $source"
		return $source
    }
    Else {
        Write-Host "`nOperation cancelled by user."
		pause
		exit
    }

# USAGE
$source = Set-SourceDialog
Write-Host Source set to: $source
}

Function Set-DestinationDialog {
	Write-Host "`nSelect a Destination Folder."
    [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null
    $objForm = New-Object System.Windows.Forms.FolderBrowserDialog
    $objForm.Rootfolder = "Desktop"
    $objForm.Description = "Select Destination"
    $Show = $objForm.ShowDialog()

    If ($Show -eq "OK") {
        $destination = $objForm.SelectedPath
        Write-Host "Destination set to: $destination"
		return $destination
    }
    Else {
        Write-Host "`nOperation cancelled by user."
		pause
        exit
    }

# USAGE
$destination = Set-Destination-Dialog
Write-Host Destination set to: $destination
}

function Get-UserChoice-FileTypes {
	# Prompts user for Filetypes
	Write-Host "Please enter which filetypes to use. Delimited by spaces. (e.g., jpg jpeg nef mp4 mp3 txt avi): "
	$userinput = (Read-Host).Trim() -split ' ' | Select-Object -Unique
	write-host $($extensions -join ', ')
	return $userinput

# USAGE
$extensions = Get-UserChoice-FileTypes
}

function Search-SourceFiles {
    param (
        [string[]]$extensions
    )

	[System.Collections.ArrayList]$sourceFiles = @()
	Get-ChildItem -Path $source -Recurse -File | Where-Object { $extensions -contains $_.Extension.TrimStart('.') }| % {
		[void]$sourceFiles.Add($_)
		Write-Progress -Activity "Step 1: Part A - Searching for files in $source" -Status $_.Directory -CurrentOperation ("Files found: {0:N0}" -f $MyFiles.Count) -PercentComplete -1
	}

    $sourceExtensionCount = @{}
    foreach ($ext in $extensions) {
        $sourceExtensionCount[$ext] = ($sourceFiles | Where-Object { $_.Extension -eq ".$ext" }).Count
    }
    $sourceTotal = $sourceFiles.Count

    Write-Host " "
    Write-Host "----------------------SOURCE----------------------"
    foreach ($ext in $extensions) {
        Write-Host "$($sourceExtensionCount[$ext]) .$ext files in $source"
    }
    Write-Host "$sourceTotal Total Files in $source"
    Write-Host " "

	if ($sourceTotal -eq 0) {
		$oReturn = [System.Windows.Forms.Messagebox]::Show(@"
	There are no files in $source. Exiting.
"@
, "ChronoSort", 0, 64)
	exit
	}

    return $sourceFiles, $sourceTotal
}

function Get-DestinationFiles {
    param (
        [string[]]$extensions
    )

		[System.Collections.ArrayList]$destinationFiles = @()
	Get-ChildItem -Path $destination -Recurse -File | Where-Object { $extensions -contains $_.Extension.TrimStart('.') }| % {
		[void]$destinationFiles.Add($_)
		Write-Progress -Activity "Step 1: Part B - Searching for files in $destination" -Status $_.Directory -CurrentOperation ("Files found: {0:N0}" -f $destinationFiles.Count) -PercentComplete -1
	}

    $destinationExtensionCount = @{}
    foreach ($ext in $extensions) {
        $destinationExtensionCount[$ext] = ($destinationFiles | Where-Object { $_.Extension -eq ".$ext" }).Count
    }

    $destinationTotal = $destinationFiles.Count
    Write-Host " "
    Write-Host "----------------------DESTINATION----------------------"
    foreach ($ext in $extensions) {
        Write-Host "$($destinationExtensionCount[$ext]) .$ext files in $destination"
    }
    Write-Host "$destinationTotal Total Files in $destination"
    Write-Host " "

    return $destinationFiles
}

function Get-UserChoice-Duplicates {
	param (
	[int]$sourceTotal
	)
    $message = "`nPlanning to copy $sourceTotal files from $source to $destination`n`nDo you want the script to check for duplicate files? (This will use an MD5 hash value for validation)`n"
    $choices = @("&Yes (Slower)", "&No (Faster)", "&Cancel")
    $result = $Host.UI.PromptForChoice("", $message, $choices, 1)
    switch ($result) {
        0 { $checkDuplicates = $true; $stepTotal += 1 }
        1 { $checkDuplicates = $false }
        2 { Write-Host "Goodbye"; Pause; Exit }
    }
if ($checkDuplicates) {Write-Host "`nDuplicate handling logic will be performed."} else {Write-Host "`nDuplicates will be skipped during the import."}

return $checkDuplicates, $stepTotal
}

Function Import-Source-Files {
    param (
        $destinationHashDictionary,
        $startTime
    )

    $successful = [int]0
    $total_duplicate_count = [int]0
    $duplicate_group_count = [int]0
    $folderFileCounts = @{}
    $totalFiles = $sourceFiles.Count
    $currentProgress = 0
    $duplicate_Import_Log = ""
    $match = $False
	if ($destinationHashDictionary -eq $null) {
    $destinationHashDictionary = @{}  # Define an empty hash table
}

    Write-Host "`n`nStarting Import Process . . ."
    Start-Sleep -Seconds 3

    foreach ($file in $sourceFiles) {
        if ($destinationHashDictionary -ne $null) {$sourceHash = Get-Hash -FilePath $($file.FullName)}  # Replace with your hash calculation function
		$match = $False
		$percentComplete = ($currentProgress / $totalFiles) * 100
		$progressStatus = "Importing $currentProgress of $totalFiles.         $total_duplicate_count Duplicates Found."
		Write-Progress -Activity "Importing . . ." -Status $progressStatus -PercentComplete $percentComplete
		$currentProgress++

        # Check if the sourceHash exists in the destinationHashDictionary
		if ($sourceHash -ne $null -and $destinationHashDictionary.ContainsKey($sourceHash)) {
			$duplicate_group_count++
			$files = $destinationHashDictionary[$sourceHash] -join "`n|___"
			$dupe_output = "`nGroup: $($duplicate_group_count)`n$($destinationHashDictionary[$sourceHash].Count) total.`n$($file.FullName) [$sourceHash]`n|___$files"
			$duplicate_Import_Log += $dupe_output
			$total_duplicate_count += $($destinationHashDictionary[$sourceHash].Count)
		
			$match = $True
			continue  # Exit the loop once you've found a match
		}


        if (-not $match) {
            $outputname, $outputPath = Rename-File -sourceFilePath $file.FullName -destinationPath $destination

            if (-not (Test-Path -Path "$outputPath" -PathType Leaf)) {
                New-Item -Path $outputPath -ItemType Directory 2>$null
            }

            if (-not (Test-Path -Path "$outputPath\$outputName" -PathType Leaf)) {
            } else {
                $extension = [System.IO.Path]::GetExtension($outputName)
                $basename = [System.IO.Path]::GetFileNameWithoutExtension($outputName)
                $renameCounter = 1
                Write-Host "$basename already Exists! . . . . . Renaming . . . . . . ."

                while (Test-Path -Path "$outputPath\$outputName" -PathType Leaf) {
                    $outputName = "${basename}($renameCounter)$extension"
                    $renameCounter++
                }
            }

            #Write-Host "Copying $($file.FullName) to $outputPath\$outputName"
            Copy-Item -Path $file.FullName -Destination "$outputPath\$outputName" -Force
            $successful++

            if ($folderFileCounts.ContainsKey($outputPath)) {
                $folderFileCounts[$outputPath]++
            } else {
                $folderFileCounts[$outputPath] = 1
            }
        }
    }

	# Had to put the Output-Log function call here. I don't know why. But it works, now. Fuck Powershell.
    Output-Log -importLog $importLog -duplicate_Import_Log $duplicate_Import_Log -duplicate_group_count $duplicate_group_count -folderFileCounts $folderFileCounts -successful $successful -total_duplicate_count $total_duplicate_count -StartTime $startTime

	# Everything breaks when it's returned... WHY!? Fuck Powershell.
	#return $successful, $duplicate_Import_Log, $duplicate_group_count, $total_duplicate_count, $folderFileCounts
}

function Get-AllExtendedProperties {
    param (
        [string]$FilePath
    )
    $Folder = Split-Path -Parent -Path $FilePath
    $File = Split-Path -Leaf -Path $FilePath
    $Shell = New-Object -COMObject Shell.Application
    $ShellFolder = $Shell.NameSpace($Folder)
    $ShellFile = $ShellFolder.ParseName($File)
    $allProperties = @{}
    for ($File = 0; $File -lt 500; $File++) {
        $propertyName = $ShellFolder.GetDetailsOf($null, $File)
        if ($propertyName) {
            $propertyValue = $ShellFolder.GetDetailsOf($ShellFile, $File)
            $allProperties[$propertyName] = $propertyValue
        }
    }

    return $allProperties
}

function Rename-File {
    param (
        [string]$sourceFilePath,
        [string]$destinationPath
    )
    $allExtendedProperties = Get-AllExtendedProperties -FilePath $sourceFilePath
	$desiredCreationDate = $allExtendedProperties['Media Created']
	if (-not $desiredCreationDate -or $desiredCreationDate -eq 'Unknown') {
		$desiredCreationDate = $allExtendedProperties['Date Taken']
	}
	if (-not $desiredCreationDate -or $desiredCreationDate -eq 'Unknown') {
		$desiredCreationDate = $allExtendedProperties['Date Modified']
	}
	$desiredCreationDate = ($desiredCreationDate -split ' ')[0]
	$desiredCreationDate = $desiredCreationDate -replace '\s+|[^i\p{IsBasicLatin}/]|[^\x20-\x7E/]', ''
    $dateTime = [DateTime]::MinValue
    [void][DateTime]::TryParse($desiredCreationDate, [ref]$dateTime)
    if ($dateTime -eq [DateTime]::MinValue) {
        $dateTime = [DateTime]::Now
		Write-Host "Something really weird happened to this file . . . Using today's date"
    }
    $year = $dateTime.Year
    $month = $dateTime.Month
    $day = $dateTime.Day
    $monthAlpha = Get-Culture | ForEach-Object { $_.DateTimeFormat.GetMonthName($month) }
    $outputPath = Join-Path -Path $destinationPath -ChildPath "$year"
	# UNCOMMENT FOR SORTING INTO MONTH FOLDER $outputPath = Join-Path -Path $destinationPath -ChildPath "$year\$monthAlpha"
	# UNCOMMENT FOR SORTING INTO DAY $outputPath = Join-Path -Path $destinationPath -ChildPath "$year\$monthAlpha\$day"
    $extension = (Get-Item $sourceFilePath).Extension.TrimStart('.')
	$outputname = "$year-$month-$day.$extension"
    return $outputName, $outputPath
}

function Get-Hash($filePath) {
    $hashValue = certutil -hashfile $filePath MD5 | Select-Object -Index 1
    return $hashValue
}

Function Set-Hash-Array {
	param ($destinationFiles)
	Write-Host "Hashing . . ."
	$hashDictionary = @{}
	$totalFiles = $destinationFiles.Count
	$currentFile = 0

	foreach ($file in $destinationFiles) {
		$currentFile++
		$destinationHash = Get-Hash -FilePath $($file.FullName)
		$HashDictionary[$DestinationHash] += @($file.FullName)

		$percentComplete = ($currentFile / $totalFiles) * 100
		$progressStatus = "Hashing file $currentFile of $totalFiles"
		Write-Progress -Activity "Hashing . . ." -Status $progressStatus -PercentComplete $percentComplete
	}

	return $HashDictionary
#USAGE
$destinationHashDictionary = Set-Hash-Array $destinationFiles
}

Function Output-Log {
    param (
        [string]$importLog,
        [string]$duplicate_Import_Log,
        [int]$duplicate_group_count,
        [hashtable]$folderFileCounts,
        [int]$successful,
        [int]$total_duplicate_count,
		[string]$startTime
    )
	# Output Log
	Write-Host "Finished at $(Get-Date)"
    $output = "***********SUMMARY************`n"
    $output += "$global:startTime"
	$output += "Process finished: $(Get-Date)`n"
    $output += "Successfully imported: $($successful) of $($sourceTotal) total files.`n`n"
	$output += "Imported into the following directories: "

	foreach ($folder in $folderFileCounts.Keys) {
		$count = $folderFileCounts[$folder]
		Write-Host "$($folder): $count"
		$output += "`n[$count] $($folder)"
		}

    # Output log if duplicates are checked.
	if ($checkDuplicates) {
	$output += "`n`nDuplicate Scan done: $(Get-Date)`n"
	$output += "Total duplicate files found from Source: " + $duplicate_group_count.ToString() + "`n"
	$output += "Total duplicate files: " + $total_duplicate_count.ToString() + "`n"
	$output += "$duplicate_Import_Log`n"
	}
	$output += "`n*************END**************`n`n`n"
    # Read the existing content of the log file, if any
    $existingContent = Get-Content -Path $importLog -Raw
    # Write the updated content (output + existing content) back to the log file
    $output + $existingContent | Set-Content -Path $importLog

    Write-Host "`nLog file saved to: $importLog"
	Write-Host "`n`nHave a great day!`n`n"
    start notepad $importLog
	pause
	exit
}

function Log-Error {
    param (
        [string]$errorLog
    )
    $host.ui.rawui.BackgroundColor = "Black"
    $host.ui.rawui.ForegroundColor = "Red"
    Write-Host "`nDamn it! An error occurred!`n`n"
    $timestamp = Get-Date
    $errorMessage = "[$timestamp]`nERROR: $_.Exception.Message `r`n`nScript:  $($_.InvocationInfo.ScriptName) `r`nLine:  $($_.InvocationInfo.ScriptLineNumber) `r`nPosition:  $($_.InvocationInfo.PositionMessage) `r`nStackTrace:  $($_.Exception.StackTrace) `r`n`n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!`r`n"
    Write-Host $errorMessage
    # Read the existing content of the log file
    $existingContent = Get-Content -Path $errorLog -Raw
    # Combine the new error message with the existing content and write to the log file
    ($errorMessage + $existingContent) | Set-Content -Path $errorLog -Force
}

function I_LOVE_KARENA! {
    try {
		$importLog, $errorLog = Initialize-Files
		$startTime, $stepTotal, $stepNumber = Initialize-Variables
		$source = Set-SourceDialog
		$destination = Set-DestinationDialog
		$global:startTime
		$extensions = Get-UserChoice-FileTypes
		$sourceFiles, $sourceTotal = Search-SourceFiles -extensions $extensions
		$destinationFiles = Get-DestinationFiles -extensions $extensions
		$checkDuplicates, $stepTotal = Get-UserChoice-Duplicates -sourceTotal $sourceTotal
		if ($checkDuplicates) {$destinationHashDictionary = Set-Hash-Array $destinationFiles}
		$successful, $duplicate_Import_Log, $duplicate_group_count, $total_duplicate_count, $folderFileCounts = Import-Source-Files -destinationHashDictionary $destinationHashDictionary -StartTime $startTime

		pause
		exit

# Apparently this breaks the fuck out of this script. Instead I moved it to inside the Import-Source-Files function and it works...
# Output-Log -importLog $importLog -duplicate_Import_Log $duplicate_Import_Log -duplicate_group_count $duplicate_group_count -folderFileCounts $folderFileCounts -successful $successful -total_duplicate_count $total_duplicate_count

	}
    catch {
		Write-Host "An Error was found. Fuck you Powershell."
		pause
		Log-Error -errorLog $errorLog
		[Console]::ResetColor()
		$host.ui.rawui.ForegroundColor = "Yellow"
		start notepad $errorLog
		Write-Host "`nPress ENTER to exit..."
		do {
			$key = [System.Console]::ReadKey($true)
		} while ($key.Key -ne "Enter")
		[Console]::ResetColor()
        exit
    }
}
I_LOVE_KARENA!
