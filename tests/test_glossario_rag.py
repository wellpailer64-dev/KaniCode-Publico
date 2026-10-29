"""Glossário compartilhado entre escuta e RAG; dados e saídas isolados no D."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_cerebro_projetos as projetos
import glossario as g
import perfil_cerebro as c

FONTE_GLOSSARIO = c._fonte_glossario


class EscutaGlossarioTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="D:/kanivete_testes")
        self.addCleanup(self.temp.cleanup)
        p = patch.object(g, "ARQ", str(Path(self.temp.name) / "extra.json"))
        p.start()
        self.addCleanup(p.stop)

    def test_termos_acentos_plural_e_idempotencia(self):
        texto = "O rague usa um grafo com vertices, arestas e clusters."
        esperado = "O RAG usa um grafo com vértices, arestas e clusters."
        self.assertEqual(g.corrigir(texto), esperado)
        self.assertEqual(g.corrigir(esperado), esperado)
        self.assertEqual(g.corrigir("vertice e vértices, grafo e grafos, cluster e clusters"),
                         "vértice e vértices, grafo e grafos, cluster e clusters")

    def test_rack_contextual_sem_mudar_hardware_ou_palavras_parecidas(self):
        for texto in ("Salvar as habilidades no rack do KaniCode.", "Nosso rack de conhecimento.", "Consultar o rack do cérebro."):
            self.assertIn("RAG", g.corrigir(texto))
        for texto in ("O rack de servidores está cheio.", "Organize os equipamentos no rack.",
                      "O KaniCode monitora o rack do servidor.", "O rack está quente.", "O gráfico mostra o tracking."):
            self.assertEqual(g.corrigir(texto), texto)

    def test_nomes_existentes_e_regras_pessoais_continuam(self):
        self.assertEqual(g.corrigir("Cane, abre o Poto Canivete no Cani Code"),
                         "Kani, abre o Photo Kanivete no KaniCode")
        Path(g.ARQ).write_text(json.dumps([[r"\bapelido\b", "Nome Pessoal"]]), encoding="utf-8")
        self.assertEqual(g.corrigir("apelido e rague"), "Nome Pessoal e RAG")


class VerticesGlossarioTest(unittest.TestCase):
    setUp = projetos.ProjetosTest.setUp
    tearDown = projetos.ProjetosTest.tearDown

    def habilitar(self):
        p = patch.object(c, "_fonte_glossario", FONTE_GLOSSARIO)
        p.start()
        self.patches.append(p)
        c._MEM.update(chave=None)

    def test_tipo_grupo_definicoes_e_ligacoes(self):
        self.habilitar()
        d = c.ler()
        nos = [n for n in d["nos"] if n.get("termo_glossario")]
        self.assertEqual({n["titulo"] for n in nos}, {"RAG", "Grafo", "Vértices", "Arestas", "Clusters"})
        for n in nos:
            self.assertEqual((n["tipo"], n["grupo"], n["area"]), ("glossario", "glossario", "dev"))
            self.assertEqual(n["ambitos"], ["kanicode"])
            self.assertTrue(n["texto"] and n["arquivo"])
        self.assertEqual(d["grupos"]["glossario"], "Glossário")
        self.assertTrue(any(l[2] == 1 for l in d["ligas"]))
        self.assertFalse(c._candidatos({"nos": nos}, c.time.time()))

    def test_busca_rag_recupera_termo(self):
        self.habilitar()
        import cerebro_motor as motor
        with patch.object(motor, "_IDX", {"assinatura": None, "d": None}):
            r = motor.buscar("RAG", modo="lexical", agente="codex", tipo="glossario",
                              ambito="kanicode", profundidade=0, marcar=False)
        self.assertTrue(any(n["chave"] == "glossario:rag" for n in r))

    def test_atualizar_fonte_invalida_cache(self):
        destino = Path(self.tmp.name) / "termos.json"
        dados = json.loads(Path(g.ARQ_TERMOS).read_text(encoding="utf-8"))
        destino.write_text(json.dumps(dados), encoding="utf-8")
        with patch.object(g, "ARQ_TERMOS", str(destino)):
            self.habilitar()
            primeiro = c.ler()
            self.assertIn("vértices", g.corrigir("vertices"))
            dados["termos"][0]["definicao"] = "Definição de RAG conferida para o teste."
            destino.write_text(json.dumps(dados), encoding="utf-8")
            st = destino.stat()
            os.utime(destino, (st.st_atime, st.st_mtime + 2))
            self.assertIsNot(primeiro, c.ler())
            self.assertIn("conferida para o teste", c._achar("glossario:rag")["texto"])


if __name__ == "__main__":
    unittest.main()
