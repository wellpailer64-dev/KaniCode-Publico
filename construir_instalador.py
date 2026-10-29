"""Empacota a release completa num instalador EXE com o IExpress do Windows."""
import argparse
from pathlib import Path
import os
import shutil
import subprocess
import zipfile


def preparar(pacote, pasta, versao):
    pacote, pasta = Path(pacote).resolve(), Path(pasta).resolve()
    with zipfile.ZipFile(pacote) as z:
        if "KaniCode/KaniCode.exe" not in z.namelist():
            raise ValueError("O ZIP nao contem o aplicativo completo")
    pasta.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pacote, pasta / "pacote.zip")
    (pasta / "instalar.cmd").write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"\r\nexit /b %errorlevel%\r\n', encoding="ascii")
    script = r'''$ErrorActionPreference = 'Stop'
$base = if (Test-Path -LiteralPath 'D:\') { 'D:\Kanivete\Aplicativos' } else { Join-Path $env:LOCALAPPDATA 'KaniCode' }
$destino = Join-Path $base 'VERSAO'
New-Item -ItemType Directory -Path $destino -Force | Out-Null
Expand-Archive -LiteralPath (Join-Path $PSScriptRoot 'pacote.zip') -DestinationPath $destino -Force
Start-Process -FilePath (Join-Path $destino 'KaniCode\KaniCode.exe')
'''
    (pasta / "instalar.ps1").write_text(script.replace("VERSAO", versao), encoding="utf-8-sig")
    exe = pasta.parent / ("KaniCode-" + versao + "-Setup.exe")
    sed = """[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=EXE
FriendlyName=KaniCode
AppLaunched=instalar.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[SourceFiles]
SourceFiles0=PASTA
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
[Strings]
FILE0="pacote.zip"
FILE1="instalar.cmd"
FILE2="instalar.ps1"
""".replace("EXE", str(exe)).replace("PASTA", str(pasta) + "\\")
    configuracao = pasta / "instalador.sed"
    configuracao.write_text(sed, encoding="utf-8")
    return configuracao, exe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pacote", required=True)
    ap.add_argument("--versao", required=True)
    a = ap.parse_args()
    if not __import__('re').fullmatch(r"[0-9]+(?:\.[0-9]+){2}", a.versao):
        raise ValueError("Versao invalida")
    sed, exe = preparar(a.pacote, Path(a.pacote).resolve().parent / "instalador", a.versao)
    subprocess.run([str(Path(os.environ["WINDIR"]) / "System32/iexpress.exe"), "/N", "/Q", str(sed)], check=True, timeout=600)
    if not exe.is_file() or exe.stat().st_size < 10000:
        raise ValueError("IExpress nao gerou o instalador")
    print(exe)


if __name__ == "__main__":
    main()
