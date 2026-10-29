"""Entrada do KaniCode.exe (PyInstaller, construir.py).

O exe leva o Python 3.13 e as bibliotecas; o código do KaniCode vai junto como arquivos .py em `app/` (ao lado do exe),
igual à pasta do código: __file__, ui/, modelos/ e plugins/ continuam valendo sem mudança.
O KaniCode chama o próprio Python para rodar scripts (mcp_equipe.py, compromissos.py, panda.py dos plugins, `-m py_compile`...).
Congelado, sys.executable é este exe, então ele também se comporta como `python`:
  KaniCode.exe                      → abre o KaniCode (app/kanicode.py)
  KaniCode.exe script.py [args]     → roda o script, como `python script.py`
  KaniCode.exe -m modulo [args]     → como `python -m modulo`
  KaniCode.exe -c "código"          → como `python -c`
Opções do Python sem efeito aqui (-u, -B, -I, -E, -s, -X opção) são aceitas e ignoradas.
"""
import os, runpy, sys

APP = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)), "app")
_SEM_EFEITO = {"-u", "-B", "-I", "-E", "-s", "-S", "-O", "-OO", "-q"}


def _rodar_script(caminho, args):
    caminho = os.path.abspath(caminho)
    sys.argv = [caminho, *args]
    sys.path.insert(0, os.path.dirname(caminho))
    runpy.run_path(caminho, run_name="__main__")


def _religar_std():
    """exe sem console: o PyInstaller deixa sys.stdin/stdout/stderr = None, mas quem chamou pode ter passado canos
    (subprocess com capture_output, o servidor MCP por stdio). Religa nos canos herdados, se houver."""
    import ctypes, io, msvcrt
    k = ctypes.windll.kernel32
    for nome, num, modo in (("stdin", -10, "rb"), ("stdout", -11, "wb"), ("stderr", -12, "wb")):
        if getattr(sys, nome) is not None:
            continue
        h = k.GetStdHandle(num)
        if not h or h == -1 or k.GetFileType(h) == 0:   # sem cano/arquivo herdado
            continue
        try:
            fd = msvcrt.open_osfhandle(h, os.O_RDONLY if modo == "rb" else os.O_WRONLY)
            bruto = os.fdopen(fd, modo, buffering=0 if modo == "wb" else -1)
            setattr(sys, nome, io.TextIOWrapper(bruto if modo == "rb" else io.BufferedWriter(bruto), encoding="utf-8",
                                                errors="replace", line_buffering=modo == "wb", write_through=modo == "wb"))
            setattr(sys, "__" + nome + "__", getattr(sys, nome))
        except OSError:
            pass


def main():
    if getattr(sys, "frozen", False):
        os.environ.setdefault("PYTHONUTF8", "1")
        _religar_std()
    args = sys.argv[1:]
    while args and (args[0] in _SEM_EFEITO or args[0] == "-X" or args[0].startswith("-X")):
        args = args[2:] if args[0] == "-X" else args[1:]
    if args and args[0] == "-m" and len(args) > 1:
        sys.argv = [args[1], *args[2:]]
        sys.path.insert(0, os.getcwd())
        runpy.run_module(args[1], run_name="__main__", alter_sys=True)
    elif args and args[0] == "-c" and len(args) > 1:
        sys.argv = ["-c", *args[2:]]
        sys.path.insert(0, "")
        exec(compile(args[1], "<string>", "exec"), {"__name__": "__main__"})
    elif args and args[0].lower().endswith((".py", ".pyw")) and os.path.isfile(args[0]):
        _rodar_script(args[0], args[1:])
    else:
        # sem script (ou o próprio kanicode.py de um reinício): abre o KaniCode com o código de app/
        if args and os.path.basename(args[0]).lower() == "kanicode.py":
            args = args[1:]
        sys.path.insert(0, APP)
        os.chdir(APP)
        _rodar_script(os.path.join(APP, "kanicode.py"), args)


if __name__ == "__main__":
    main()
