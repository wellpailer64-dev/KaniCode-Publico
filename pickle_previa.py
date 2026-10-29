"""Pr?via est?tica da c?pia de c?digo, somente em loopback e no navegador interno."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading

_SERVIDORES = {}
_TRAVA = threading.Lock()


class _Pagina(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_head(self):
        raiz = Path(self.directory).resolve()
        alvo = Path(self.translate_path(self.path)).resolve()
        if not alvo.is_relative_to(raiz):
            self.send_error(403)
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(403)
        return None


def servir(pasta):
    raiz = Path(pasta).resolve()
    if not raiz.is_dir():
        raise ValueError("Pasta da pr?via n?o existe")
    with _TRAVA:
        if raiz not in _SERVIDORES:
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Pagina, directory=str(raiz)))
            servidor.daemon_threads = True
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
            _SERVIDORES[raiz] = servidor
        return "http://127.0.0.1:" + str(_SERVIDORES[raiz].server_port) + "/"


def abrir(copia, arquivos):
    raiz = Path(copia).resolve()
    candidatos = [Path(a) for a in arquivos if Path(a).name == "index.html"]
    if not candidatos:
        return None
    pagina = (raiz / candidatos[0]).resolve()
    if not pagina.is_relative_to(raiz) or not pagina.is_file():
        raise ValueError("P?gina fora da c?pia ou inexistente")
    url = servir(pagina.parent)
    ponte = Path("D:/Kanivete/Plugins/kanibrowser/kb.py")
    r = subprocess.run([sys.executable, str(ponte), "--onde", "kanicode", "--sem-foto", "abrir", url],
                       capture_output=True, text=True, encoding="utf-8", timeout=45,
                       creationflags=0x08000000 if sys.platform == "win32" else 0)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    return url
