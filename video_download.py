"""Vídeos por link, sem abrir o KANIVETE. Uso: video_download.py --help."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _motor():
    candidatos = [
        Path(os.environ["KANIVETE_RAIZ"]) if os.environ.get("KANIVETE_RAIZ") else None,
        Path(__import__("locais").KANIVETE),
    ]
    for raiz in candidatos:
        if raiz and (raiz / "Functions" / "videodownloader.py").is_file():
            spec = importlib.util.spec_from_file_location("_kanicode_video_motor", raiz / "Functions" / "videodownloader.py")
            motor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(motor)
            opts_base = motor._opts_base
            motor._opts_base = lambda **extra: opts_base(**{"cachedir": False, **extra})
            os.environ.setdefault("DENO_DIR", "D:/Kanivete/Cache/deno")
            motor._deno_path = lambda: str(raiz / "modelos_ia" / "deno.exe") if (raiz / "modelos_ia" / "deno.exe").is_file() else (shutil.which("deno") or "")
            return motor
    raise RuntimeError("Motor de download não localizado. Informe KANIVETE_RAIZ com a pasta do código do KANIVETE.")


def _pasta(destino, subpasta=""):
    pasta = Path(destino).expanduser() if destino else Path("D:/Kanivete/Downloads") / subpasta
    pasta = pasta.resolve()
    if pasta.drive.upper() != "D:":
        raise ValueError("Escolha uma pasta no disco D.")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _url(url):
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise ValueError("Informe um link HTTP ou HTTPS do vídeo.")
    return url


def _quadros(arquivo, destino, quantidade, inicio=0, fim=None, metodo="cenas",
             transcricao="nao", modelo="small", idioma="pt", refazer=False):
    import video_leitura
    origem = video_leitura.validar(arquivo, quantidade, inicio, fim, metodo, transcricao, modelo, idioma)
    if type(refazer) is not bool:
        raise ValueError("refazer deve ser verdadeiro ou falso.")
    motor = _motor()
    pasta = _pasta(destino, "Analises")
    return video_leitura.analisar(origem, pasta, motor, quantidade, inicio, fim, metodo,
                                 transcricao, modelo, idioma, refazer)


def executar(acao, url="", destino="", formato="mp4", qualidade="compativel", arquivo="", quantidade=8,
             inicio=0, fim=None, metodo="cenas", transcricao=None, modelo="small", idioma="pt", refazer=False):
    try:
        if acao in ("quadros", "analisar"):
            modo_fala = ("auto" if acao == "analisar" else "nao") if transcricao is None else transcricao
            return _quadros(arquivo, destino, quantidade, inicio, fim, metodo, modo_fala, modelo, idioma, refazer)
        if acao not in ("info", "baixar"):
            raise ValueError("Use info, baixar, quadros ou analisar.")
        _url(url)
        if formato not in ("mp4", "mp3") or qualidade not in ("compativel", "maxima"):
            raise ValueError("Formato ou qualidade inválidos.")
        motor = _motor()
        if acao == "info":
            info = motor.extrair_info_video(url)
            info.pop("thumbnail", None)
            return {"ok": True, "info": info}
        pasta = str(_pasta(destino))
        if formato == "mp3":
            final = motor.baixar_audio_mp3(url, pasta)
        else:
            final = motor.baixar_video_mp4(url, pasta, qualidade=qualidade)
        caminho = Path(final).resolve()
        if not caminho.is_file() or not caminho.stat().st_size:
            raise RuntimeError("Download terminou sem um arquivo válido.")
        return {"ok": True, "arquivo": str(caminho), "bytes": caminho.stat().st_size, "formato": formato}
    except Exception as e:
        return {"ok": False, "mensagem": str(e)[:1000]}


def chamar(argumentos):
    """Isola o yt-dlp: o motor original ajusta subprocess.Popen durante downloads."""
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--pedido-json"],
                           input=json.dumps(argumentos, ensure_ascii=False), capture_output=True, text=True,
                           encoding="utf-8", timeout=1800, creationflags=NO_WINDOW)
        resultado = json.loads(r.stdout)
        if r.returncode and resultado.get("ok"):
            raise RuntimeError("Processo de vídeo terminou com erro.")
        return resultado
    except Exception as e:
        return {"ok": False, "mensagem": str(e)[:1000]}


def main():
    if sys.argv[1:] == ["--pedido-json"]:
        try:
            resultado = executar(**json.load(sys.stdin))
        except Exception as e:
            resultado = {"ok": False, "mensagem": str(e)[:1000]}
    else:
        p = argparse.ArgumentParser(description=__doc__)
        p.add_argument("acao", choices=["info", "baixar", "quadros", "analisar"])
        p.add_argument("--url", default="")
        p.add_argument("--destino", default="")
        p.add_argument("--formato", choices=["mp4", "mp3"], default="mp4")
        p.add_argument("--qualidade", choices=["compativel", "maxima"], default="compativel")
        p.add_argument("--arquivo", default="")
        p.add_argument("--quantidade", type=int, default=8, help="Máximo de quadros (1 a 20)")
        p.add_argument("--inicio", type=float, default=0, help="Segundo inicial do trecho")
        p.add_argument("--fim", type=float, default=None, help="Segundo final do trecho")
        p.add_argument("--metodo", choices=["cenas", "uniforme"], default="cenas")
        p.add_argument("--transcricao", choices=["auto", "sim", "nao"], default=None)
        p.add_argument("--modelo", default="small", help="Nome de um modelo Whisper já instalado")
        p.add_argument("--idioma", default="pt", help="Código de idioma ou auto")
        p.add_argument("--refazer", action="store_true", help="Ignora o cache desta análise")
        resultado = executar(**vars(p.parse_args()))
    print(json.dumps(resultado, ensure_ascii=False))
    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
