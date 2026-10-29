"""Monta o KaniCode.exe (PyInstaller): dist/KaniCode/{KaniCode.exe, _internal/, app/, versao.txt}.

  py -3.13 construir.py [--versao 0.1.7] [--zip] [--saida D:/pasta]

- O exe é o lançador (lancador.py): Python 3.13 + bibliotecas. O código do KaniCode vai em app/ como .py (o git ls-files,
  sem testes nem android), então os caminhos (__file__, ui/, modelos/, plugins/) ficam iguais aos da pasta do código.
- Bibliotecas: as de terceiros que algum .py do KaniCode (ou dos plugins ao lado) importa, mais a biblioteca padrão
  inteira (os plugins rodam pelo mesmo exe e podem importar qualquer coisa dela). Módulos do KaniCode NÃO são congelados:
  congelados, o __file__ deles apontaria para _internal e a janela não acharia ui/.
- Fora: torch/whisper (só a leitura de vídeo usa; > 1 GB) e o que só os testes usam.
Tudo no disco D (build/ e dist/ dentro desta pasta, ignorados pelo git).
"""
import argparse, ast, glob, importlib.util, os, shutil, subprocess, sys, zipfile
from pathlib import Path

AQUI = os.path.dirname(os.path.abspath(__file__))
FORA_DO_APP = ("tests/", "android/", ".github/", "lancador.py", "construir.py")
FORA = {"PyInstaller", "torch", "whisper", "torchvision", "torchaudio", "tensorflow", "matplotlib", "IPython", "jupyter", "pytest", "sympy",
        "scipy.tests", "numpy.tests", "pandas", "tkinter.test", "PyQt5", "PyQt6", "PySide2", "PySide6"}
STD_FORA = {"antigravity", "this", "idlelib", "turtledemo", "lib2to3", "ensurepip", "test", "pydoc_data", "tkinter", "turtle",
            "__phello__", "_testcapi", "_testinternalcapi", "_testbuffer", "_testmultiphase", "_testsinglephase",
            "_testimportmultiple", "_testclinic", "_testconsole", "_xxtestfuzz", "_ctypes_test", "xxsubtype", "xxlimited",
            "xxlimited_35", "_xxsubinterpreters", "_xxinterpchannels", "_xxinterpqueues", "_tkinter", "_testlimitedcapi",
            "_testclinic_limited", "_scproxy", "_curses", "_curses_panel", "curses", "readline", "_gdbm", "_dbm", "dbm.gnu",
            "dbm.ndbm", "grp", "pwd", "posix", "fcntl", "termios", "resource", "syslog", "_posixsubprocess", "_posixshmem",
            "nis", "spwd", "crypt", "ossaudiodev", "_crypt", "_uuid", "_android_support", "_apple_support", "_ios_support"}
COM_DADOS = ["webview", "playwright", "openwakeword", "kokoro_onnx", "onnx_asr", "onnxruntime", "clr_loader", "pythonnet",
             "tinytuya", "_sounddevice_data", "_soundfile_data", "pywebpush", "py_vapid", "qrcode", "comtypes", "pycaw",
             "tokenizers", "phonemizer", "espeakng_loader", "language_tags", "segments", "csvw", "certifi"]


def arquivos_app():
    r = subprocess.run(["git", "ls-files", "--cached"], cwd=AQUI, capture_output=True, text=True, encoding="utf-8", check=True)
    import conhecimento_fontes
    conhecimento_fontes.validar_publico(conhecimento_fontes.ler(Path(AQUI) / "habilidades_registro.json"))
    arquivos = [f for f in r.stdout.splitlines() if f and not f.startswith(FORA_DO_APP) and os.path.isfile(os.path.join(AQUI, f))]
    conhecimento_fontes.validar_pacote(arquivos)
    return arquivos


def _imports(caminhos):
    mods = set()
    for f in caminhos:
        try:
            arv = ast.parse(open(f, encoding="utf-8-sig").read())
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for n in ast.walk(arv):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                mods.add(n.module.split(".")[0])
    return mods


def terceiros():
    """bibliotecas de fora importadas pelo KaniCode e pelos plugins ao lado (D:/Kanivete/Plugins/*)"""
    locais = {os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(AQUI, "**", "*.py"), recursive=True)}
    plugins = os.path.join(os.path.splitdrive(AQUI)[0] + os.sep, "Kanivete", "Plugins")
    fontes = [f for f in glob.glob(os.path.join(AQUI, "**", "*.py"), recursive=True) if "tests" not in f.split(os.sep)]
    for p in glob.glob(os.path.join(plugins, "*", "*.py")):
        if os.sep + "kanicode" + os.sep not in p:
            fontes.append(p)
            locais.add(os.path.splitext(os.path.basename(p))[0])
    std = set(sys.stdlib_module_names)
    saida = []
    for m in sorted(_imports(fontes) - locais - std - FORA):
        try:
            if importlib.util.find_spec(m):
                saida.append(m)
        except (ImportError, ValueError):
            pass
    return saida, locais


def biblioteca_padrao():
    saida = []
    for m in sorted(sys.stdlib_module_names):
        if m in STD_FORA or m.startswith("_test"):
            continue
        try:
            if importlib.util.find_spec(m):
                saida.append(m)
        except (ImportError, ValueError):
            pass
    return saida


def icone(destino):
    from PIL import Image
    Image.open(os.path.join(AQUI, "icone.png")).convert("RGBA").save(destino, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versao", default=None)
    ap.add_argument("--saida", default=os.path.join(AQUI, "dist"))
    ap.add_argument("--zip", action="store_true")
    a = ap.parse_args()
    versao = a.versao or open(os.path.join(AQUI, "versao.txt"), encoding="utf-8").read().strip()
    trabalho = os.path.join(AQUI, "build")
    os.makedirs(trabalho, exist_ok=True)
    ico = os.path.join(trabalho, "KaniCode.ico")
    icone(ico)
    ext, locais = terceiros()
    std = biblioteca_padrao()
    print(f"KaniCode {versao}: {len(ext)} bibliotecas de fora, {len(std)} módulos da biblioteca padrão")
    print("  de fora:", ", ".join(ext))
    args = [os.path.join(AQUI, "lancador.py"), "--name", "KaniCode", "--noconfirm", "--clean", "--windowed",
            "--icon", ico, "--distpath", a.saida, "--workpath", trabalho, "--specpath", trabalho,
            "--contents-directory", "_internal"]
    for m in ext + std:
        args += ["--hidden-import", m]
    for m in COM_DADOS:
        if importlib.util.find_spec(m):
            args += ["--collect-all", m]
    for m in FORA | (locais - set(ext) - set(std)):
        args += ["--exclude-module", m]
    os.environ.setdefault("PYINSTALLER_CONFIG_DIR", os.path.join(trabalho, "cache"))   # cache no D, não em C:/Users
    import PyInstaller.__main__
    PyInstaller.__main__.run(args)
    raiz = os.path.join(a.saida, "KaniCode")
    app = os.path.join(raiz, "app")
    shutil.rmtree(app, ignore_errors=True)
    for f in arquivos_app():
        dst = os.path.join(app, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(AQUI, f), dst)
    open(os.path.join(raiz, "versao.txt"), "w", encoding="utf-8").write(versao + "\n")
    open(os.path.join(app, "versao.txt"), "w", encoding="utf-8").write(versao + "\n")
    print("pronto:", raiz)
    if a.zip:
        z = os.path.join(a.saida, f"KaniCode-{versao}.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for pasta, _, nomes in os.walk(raiz):
                for n in nomes:
                    c = os.path.join(pasta, n)
                    zf.write(c, os.path.relpath(c, a.saida))
        print("zip:", z, f"{os.path.getsize(z) / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
