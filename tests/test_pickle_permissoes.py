"""Permiss?es do agente OpenCode seguem o modo da conversa, inclusive nas continua??es."""
import json
import threading
import unittest
from unittest.mock import MagicMock, patch

import opencode_mvp
import pickle_agente


class PermissoesOpenCodeTest(unittest.TestCase):
    def conferir_modo(self, editar):
        sessao = MagicMock()
        sessao.atual.return_value = True
        sessao.meta = {"trabalho": "D:/kanivete_testes/copia_simulada"}
        parar = threading.Event()
        parar.set()
        with patch.object(opencode_mvp, "MODELO", "opencode/deepseek-v4.1-flash-free"), \
             patch.object(opencode_mvp, "executavel", return_value="opencode.exe"), \
             patch.object(opencode_mvp, "ambiente", return_value={}), \
             patch.object(pickle_agente, "Sessao", return_value=sessao), \
             patch.object(pickle_agente.subprocess, "Popen", side_effect=OSError("fim simulado")) as iniciar:
            pickle_agente.rodar("Pode continuar", "D:/kanivete_testes", lambda ev: None, parar=parar, editar=editar)
        cfg = json.loads(iniciar.call_args.kwargs["env"]["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(cfg["model"], "opencode/deepseek-v4.1-flash-free")
        self.assertEqual(cfg["permission"].get("edit", "deny"), "allow" if editar else "deny")
        self.assertEqual(cfg["permission"]["external_directory"], "deny")
        self.assertIn("DeepSeek", cfg["agent"]["kanicode-pickle"]["prompt"])

    def test_continuacao_em_execucao(self):
        self.conferir_modo(True)

    def test_planejar_sem_escrita(self):
        self.conferir_modo(False)
