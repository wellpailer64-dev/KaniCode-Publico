"""RAG no prompt e pr?via HTTP local sem executar c?digo do projeto."""
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch
import pickle_agente
import pickle_previa


class RagPreviaTest(unittest.TestCase):
    def test_rag_preserva_historico_e_planejamento(self):
        with patch("perfil_cerebro.ponto_de_partida", return_value="Identidade visual confirmada") as buscar:
            texto = pickle_agente._texto_prompt("crie a p?gina", [{"role": "user", "content": "anterior"}], False, False)
        buscar.assert_called_once_with("crie a p?gina", 1400, quem="pickle")
        self.assertIn("Identidade visual confirmada", texto)
        self.assertIn("anterior", texto)
        self.assertIn(pickle_agente._SO_LEITURA, texto)

    def test_rag_indisponivel_nao_interrompe(self):
        with patch("perfil_cerebro.ponto_de_partida", side_effect=RuntimeError("offline")):
            self.assertIn("pedido", pickle_agente._texto_prompt("pedido", [], False, True))

    def test_previa_local_e_ponte(self):
        pasta = Path(tempfile.mkdtemp(dir="D:/kanivete_testes", prefix="previa_"))
        (pasta / "landing").mkdir()
        (pasta / "landing/index.html").write_text("<h1>Teste</h1>", encoding="utf-8")
        with patch.object(pickle_previa.subprocess, "run") as executar:
            executar.return_value.returncode = 0
            url = pickle_previa.abrir(pasta, ["landing/index.html"])
        self.assertTrue(url.startswith("http://127.0.0.1:"))
        self.assertIn("kanicode", executar.call_args.args[0])
        self.assertIn("Teste", urllib.request.urlopen(url).read().decode())
        self.assertEqual(url, pickle_previa.servir(pasta / "landing"))
        servidor = pickle_previa._SERVIDORES.pop((pasta / "landing").resolve())
        servidor.shutdown()
        servidor.server_close()

    def test_caminho_externo_recusado(self):
        with self.assertRaises(ValueError):
            pickle_previa.abrir("D:/kanivete_testes/copia", ["../index.html"])
