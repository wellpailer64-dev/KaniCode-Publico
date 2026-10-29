"""Download e quadros reais sobre HTTP local; integrações sem conta nem app do usuário."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_download as video


class ServidorSilencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class VideoDownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="D:/kanivete_testes")
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)

    def test_argumentos_invalidos_nao_carregam_motor(self):
        with patch.object(video, "_motor") as motor:
            for args in ({"acao": "apagar"}, {"acao": "baixar", "url": "file:///D:/video.mp4"},
                         {"acao": "baixar", "url": "https://site/video", "formato": "exe"},
                         {"acao": "quadros", "arquivo": "inexistente", "quantidade": 21}):
                self.assertFalse(video.executar(**args)["ok"])
            motor.assert_not_called()

    def test_destino_c_recusado_e_download_sem_arquivo_nao_confirma(self):
        motor = Mock()
        motor.baixar_video_mp4.return_value = str(self.pasta / "ausente.mp4")
        with patch.object(video, "_motor", return_value=motor):
            self.assertFalse(video.executar("baixar", url="https://site/video", destino="C:/proibido")["ok"])
            motor.baixar_video_mp4.assert_not_called()
            self.assertFalse(video.executar("baixar", url="https://site/video", destino=str(self.pasta))["ok"])

    def test_cli_invalida_retorna_json_e_codigo_de_erro(self):
        r = subprocess.run([sys.executable, "-X", "utf8", str(video.RAIZ / "video_download.py"),
                            "baixar", "--url", "invalido"], capture_output=True, text=True,
                           encoding="utf-8", timeout=20, creationflags=video.NO_WINDOW)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["ok"])
        self.assertFalse(video.chamar({"acao": "invalida"})["ok"])

    def test_integracao_kani_e_contexto_codex(self):
        import kani_modo
        import kani_etapas
        import codex_contexto
        for pedido in ("Baixe este link", "Analise este vídeo", "Assista https://site/video"):
            self.assertIn("video_download", kani_etapas.relevantes(pedido, kani_modo.FERRAMENTAS))
        with patch.object(video, "chamar", return_value={"ok": False, "mensagem": "bloqueado"}) as chamada:
            self.assertIn("video_download", kani_modo.FERRAMENTAS)
            self.assertTrue(kani_modo._executar("video_download", {"acao": "info"}, str(self.pasta)).startswith("NÃO FEITO:"))
            chamada.assert_called_once_with({"acao": "info"})
        with patch.object(codex_contexto.organizacao_pailer, "contexto", return_value=""):
            contexto = codex_contexto.preparar("analise este vídeo", str(self.pasta), True, True)
        self.assertIn("video_download.py", contexto)
        self.assertIn("quadros --arquivo", contexto)

    def test_mcp_esquema_e_despacho(self):
        # Extrai somente contrato e função: não inicializa streams nem canal de controle reais.
        arvore = ast.parse((video.RAIZ / "mcp_equipe.py").read_text(encoding="utf-8-sig"))
        contrato = next(n for n in arvore.body if isinstance(n, ast.Assign) and any(isinstance(a, ast.Name) and a.id == "FERRAMENTAS" for a in n.targets))
        ferramentas = ast.literal_eval(contrato.value)
        esquema = next(f for f in ferramentas if f["name"] == "video_download")
        self.assertEqual(esquema["inputSchema"]["properties"]["acao"]["enum"], ["info", "baixar", "quadros", "analisar"])
        funcao = next(n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "_chamar")
        respostas = []
        espaco = {"json": json, "_responder": lambda id_, r: respostas.append(r)}
        exec(compile(ast.Module(body=[funcao], type_ignores=[]), "<despacho_mcp>", "exec"), espaco)
        with patch.object(video, "chamar", return_value={"ok": True, "arquivo": "D:/video.mp4"}):
            espaco["_chamar"](1, "video_download", {"acao": "baixar", "url": "https://site/video"})
        self.assertFalse(respostas[-1]["isError"])
        with patch.object(video, "chamar", return_value={"ok": False, "mensagem": "indisponível"}):
            espaco["_chamar"](2, "video_download", {"acao": "info", "url": "https://site/video"})
        self.assertTrue(respostas[-1]["isError"])

    def test_download_real_info_mp4_mp3_e_quadros(self):
        ffmpeg = video._motor()._resolver_ffmpeg_exe()
        origem = self.pasta / "origem.mp4"
        subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                        "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(origem)],
                       capture_output=True, check=True, timeout=30, creationflags=video.NO_WINDOW)
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), partial(ServidorSilencioso, directory=str(self.pasta)))
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        url = f"http://127.0.0.1:{servidor.server_port}/origem.mp4"
        destino = self.pasta / "baixados"
        info = video.chamar({"acao": "info", "url": url})
        self.assertTrue(info["ok"], info)
        self.assertNotIn("thumbnail", info["info"])
        arquivos = []
        for formato in ("mp4", "mp4", "mp3"):
            r = video.chamar({"acao": "baixar", "url": url, "destino": str(destino), "formato": formato})
            self.assertTrue(r["ok"], r)
            self.assertGreater(r["bytes"], 0)
            self.assertEqual(Path(r["arquivo"]).suffix, "." + formato)
            arquivos.append(r["arquivo"])
        self.assertNotEqual(arquivos[0], arquivos[1])
        self.assertEqual(Path(arquivos[0]).read_bytes(), origem.read_bytes())
        r = video.chamar({"acao": "quadros", "arquivo": arquivos[0], "destino": str(destino), "quantidade": 3, "metodo": "uniforme"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(len(r["quadros"]), 3)
        self.assertEqual([q["segundo"] for q in r["quadros"]], sorted(q["segundo"] for q in r["quadros"]))
        for q in r["quadros"]:
            self.assertEqual(Path(q["arquivo"]).read_bytes()[:2], bytes.fromhex("ffd8"))
            self.assertTrue(0 < q["segundo"] < r["duracao"])


if __name__ == "__main__":
    unittest.main()
