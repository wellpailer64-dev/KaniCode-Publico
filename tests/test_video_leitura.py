"""Cenas, folha, trechos, cache e fala sincronizada sobre vídeos sintéticos no D."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_download as video
import video_leitura as leitura


def criar_video(ffmpeg, destino, cores=("red", "blue", "lime", "red")):
    cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    for cor in cores:
        cmd += ["-f", "lavfi", "-i", f"color=c={cor}:s=160x90:r=10:d=1"]
    cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000"]
    entradas = "".join(f"[{i}:v]" for i in range(len(cores)))
    cmd += ["-filter_complex", entradas + f"concat=n={len(cores)}:v=1:a=0[v]",
            "-map", "[v]", "-map", f"{len(cores)}:a", "-t", str(len(cores)),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(destino)]
    subprocess.run(cmd, capture_output=True, check=True, timeout=45, creationflags=video.NO_WINDOW)


class VideoLeituraTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir="D:/kanivete_testes")
        cls.base = Path(cls.temp.name)
        cls.ffmpeg = video._motor()._resolver_ffmpeg_exe()
        cls.origem = cls.base / "cenas.mp4"
        criar_video(cls.ffmpeg, cls.origem)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp_caso = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(self.temp_caso.cleanup)
        self.saida = Path(self.temp_caso.name)

    def analisar(self, **opcoes):
        args = {"acao": "analisar", "arquivo": str(self.origem), "destino": str(self.saida), "transcricao": "nao"}
        args.update(opcoes)
        r = video.executar(**args)
        self.assertTrue(r["ok"], r)
        return r

    def test_cenas_deduplica_mantem_cores_e_gera_folha(self):
        r = self.analisar()
        self.assertEqual(r["metodo"], "cenas")
        self.assertFalse(r["avisos"], r)
        self.assertEqual(len(r["quadros"]), 3, r)
        canais = []
        for q in r["quadros"]:
            with Image.open(q["arquivo"]) as img:
                medias = ImageStat.Stat(img.convert("RGB")).mean
                canais.append(medias.index(max(medias)))
        self.assertEqual(canais, [0, 2, 1])
        with Image.open(r["folha"]) as img:
            self.assertGreaterEqual(img.width, 900)
            img.verify()
        self.assertIn("00:00:01", Path(r["leitura"]).read_text(encoding="utf-8"))

    def test_trecho_uniforme_tempos_absolutos_e_fim_validado(self):
        r = self.analisar(inicio=1, fim=3, metodo="uniforme", quantidade=2)
        self.assertEqual([q["segundo"] for q in r["quadros"]], [1.5, 2.5])
        for op in ({"inicio": -1}, {"inicio": float("nan")}, {"inicio": 3, "fim": 2},
                   {"fim": 99}, {"inicio": 4}, {"quantidade": 0}, {"refazer": "false"}):
            resultado = video.executar("analisar", arquivo=str(self.origem), destino=str(self.saida), **op)
            self.assertFalse(resultado["ok"], op)

    def test_cache_reaproveita_confere_arquivos_e_refazer(self):
        primeiro = self.analisar()
        with patch.object(leitura, "_tempos", side_effect=AssertionError("não deve extrair novamente")):
            segundo = self.analisar()
        self.assertTrue(segundo["cache"])
        self.assertEqual(primeiro["folha"], segundo["folha"])
        Path(primeiro["folha"]).write_bytes(b"corrompida")
        reparado = self.analisar()
        self.assertFalse(reparado["cache"])
        self.assertNotEqual(reparado["folha"], primeiro["folha"])
        forcado = self.analisar(refazer=True)
        self.assertFalse(forcado["cache"])
        self.assertNotEqual(forcado["folha"], reparado["folha"])

    def test_cache_invalida_video_alterado_e_preserva_resultado_anterior(self):
        origem = self.saida / "mutavel.mp4"
        origem.write_bytes(self.origem.read_bytes())
        primeiro = self.analisar(arquivo=str(origem))
        anterior = Path(primeiro["folha"]).read_bytes()
        criar_video(self.ffmpeg, origem, ("white", "black", "blue", "lime"))
        segundo = self.analisar(arquivo=str(origem))
        self.assertFalse(segundo["cache"])
        self.assertNotEqual(segundo["folha"], primeiro["folha"])
        self.assertEqual(Path(primeiro["folha"]).read_bytes(), anterior)

    def test_fala_sincronizada_e_cache_independente_dos_quadros(self):
        segmentos = [{"inicio": 1.1, "fim": 2.9, "texto": "Veja este detalhe na tela."}]
        modelo = self.saida / "small.pt"
        modelo.write_bytes(b"modelo simulado")
        with patch.object(leitura, "_modelo_local", return_value=(modelo, ["modelo", 1])), \
             patch.object(leitura, "_transcrever", return_value=segmentos) as transcrever:
            primeiro = self.analisar(inicio=1, fim=3, metodo="uniforme", quantidade=2, transcricao="auto")
            segundo = self.analisar(inicio=1, fim=3, metodo="uniforme", quantidade=3, transcricao="auto")
        transcrever.assert_called_once()
        self.assertTrue(segundo["transcricao"]["cache"])
        self.assertEqual(primeiro["transcricao"]["status"], "concluida")
        self.assertIn("detalhe", primeiro["quadros"][0]["fala"])
        dados = json.loads(Path(primeiro["transcricao"]["arquivo"]).read_text(encoding="utf-8"))
        self.assertEqual(dados["segmentos"], segmentos)
        self.assertIn("00:00:01.100", Path(primeiro["leitura"]).read_text(encoding="utf-8"))

    def test_falha_fala_nao_vira_sucesso_nem_cache_definitivo(self):
        with patch.object(leitura, "_modelo_local", return_value=(self.origem, ["simulado"])), \
             patch.object(leitura, "_transcrever", side_effect=RuntimeError("falha de áudio")) as transcrever:
            primeiro = self.analisar(transcricao="auto")
            segundo = self.analisar(transcricao="auto")
            exigido = video.executar("analisar", arquivo=str(self.origem), destino=str(self.saida), transcricao="sim")
        self.assertEqual(transcrever.call_count, 3)
        self.assertEqual(primeiro["transcricao"]["status"], "erro")
        self.assertFalse(segundo["cache"])
        self.assertFalse(exigido["ok"])
        self.assertIn("falha de áudio", primeiro["avisos"][0])

    def test_sem_modelo_nao_baixa_nada_e_sem_audio_nao_transcreve(self):
        with patch.object(leitura, "_modelo_local", return_value=(None, None)), \
             patch.object(leitura, "_transcrever") as transcrever:
            r = self.analisar(transcricao="auto")
            self.assertEqual(r["transcricao"]["status"], "indisponivel")
            transcrever.assert_not_called()
        mudo = self.saida / "mudo.mp4"
        subprocess.run([self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(self.origem),
                        "-an", "-c:v", "copy", str(mudo)], capture_output=True, check=True, timeout=20,
                       creationflags=video.NO_WINDOW)
        with patch.object(leitura, "_transcrever") as transcrever:
            r = self.analisar(arquivo=str(mudo), transcricao="auto")
        transcrever.assert_not_called()
        self.assertEqual(r["transcricao"]["status"], "sem_audio")

    def test_transcrever_recorta_audio_e_soma_inicio_sem_rede(self):
        modelo = Mock()
        modelo.transcribe.return_value = {"segments": [{"start": 0.1, "end": 0.8, "text": " Teste de fala. "}]}
        whisper = SimpleNamespace(load_model=Mock(return_value=modelo))
        with patch.dict(sys.modules, {"whisper": whisper}):
            segmentos = leitura._transcrever(self.origem, self.ffmpeg, 1, 2, self.origem, "pt", self.saida)
        self.assertEqual(segmentos, [{"inicio": 1.1, "fim": 1.8, "texto": "Teste de fala."}])
        amostras = modelo.transcribe.call_args.args[0]
        self.assertEqual(len(amostras), 16000)
        self.assertFalse(modelo.transcribe.call_args.kwargs["fp16"])

    def test_cli_analise_e_cache(self):
        args = {"acao": "analisar", "arquivo": str(self.origem), "destino": str(self.saida), "transcricao": "nao"}
        primeiro, segundo = video.chamar(args), video.chamar(args)
        self.assertTrue(primeiro["ok"], primeiro)
        self.assertTrue(segundo["ok"], segundo)
        self.assertTrue(segundo["cache"])
        self.assertEqual(primeiro["folha"], segundo["folha"])


if __name__ == "__main__":
    unittest.main()
