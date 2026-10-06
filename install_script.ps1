#Write-Output "Creating Python virtual environment for CVG data viewer"

#cd ~

#Write-Output "Creating virtual directory"

#mkdir -p Virtual_Enviornment

#cd ~/Virtual_Enviornment

#Write-Output "Creating python virtual enviornment : Image_Processing_Venv"

#python -m venv ~/Virtual_Enviornment/Image_Processing_Venv

#.\Virtual_Enviornment\Image_Processing_Venv\Scripts\Activate.ps1

Write-Output "Creating Python virtual environment for CVG data viewer"

$venvRoot = Join-Path $HOME "Virtual_Enviornment"
$venvPath = Join-Path $venvRoot "Image_Processing_Venv"
$workPath = "D:\WorkFolder\CVG_Data_Viewer"
New-Item -ItemType Directory -Path $venvRoot -Force | Out-Null

Write-Output "Creating python virtual environment : Image_Processing_Venv"
python -m venv $venvPath

& (Join-Path $venvPath "Scripts\Activate.ps1")

Write-Output "Going to working dir : $workPath"
cd $workPath

Write-Output "Installing requirements"
python -m pip install --upgrade pip
python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
