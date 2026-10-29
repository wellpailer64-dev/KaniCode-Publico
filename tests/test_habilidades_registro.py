"""Registro explícito de habilidades e recuperação lexical no RAG, com dados isolados no D."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_cerebro_projetos as projetos
import perfil_cerebro as c

FONTE_KANI = c._fonte_ferramentas_kani


class RegistroHabilidadesTest(unittest.TestCase):
    setUp = projetos.ProjetosTest.setUp
    tearDown = projetos.ProjetosTest.tearDown

    def registro(self):
        def entrada(categoria, programa):
            return {"categoria": categoria, "programa": programa, "procedimento": "Baixar e analisar vídeos com folha, cenas e transcrição.",
                    "dependencias": ["Motor do KANIVETE instalado; não requer a janela aberta."], "limites": ["É uma amostragem."],
                    "origem": "Fonte conferida no teste", "certeza": "verificado", "agente": "codex",
                    "evidencia": "Teste sintético aprovado."}
        return {"politica": {"titulo": "KaniCode vanilla no RAG", "texto": "Registrar habilidades vanilla e separar funções de outros programas.",
                             "origem": "Pedido do Pailer", "certeza": "pailer", "agente": "codex"},
                "ferramentas": {"video_download": entrada("kanicode_vanilla", "KaniCode"),
                                "rodar_js_kanivete": entrada("kanivete", "KANIVETE"),
                                "abrir": entrada("programa_externo", "Explorer")}}

    def habilitar(self, registro=None):
        caminho = Path(self.tmp.name) / "habilidades_registro.json"
        caminho.write_text(json.dumps(self.registro() if registro is None else registro), encoding="utf-8")
        for nome, valor in (("REGISTRO_HABILIDADES", str(caminho)), ("_fonte_ferramentas_kani", FONTE_KANI)):
            p = patch.object(c, nome, valor)
            p.start()
            self.patches.append(p)
        c._MEM.update(chave=None)
        return caminho

    def test_separa_categoria_de_dependencia_e_agente_que_executa(self):
        self.habilitar()
        nos = {n["chave"]: n for n in c.ler()["nos"]}
        nativo = nos["kani:ferramenta:video_download"]
        self.assertEqual(nativo["ambitos"], ["kanicode"])
        self.assertEqual(nativo["categoria_habilidade"], "kanicode_vanilla")
        self.assertEqual(nativo["tipo"], "habilidade")
        self.assertEqual(nativo["finalidade"], "procedimento")
        self.assertIn("Motor do KANIVETE instalado", nativo["texto"])
        self.assertEqual(nos["kani:ferramenta:rodar_js_kanivete"]["ambitos"], ["kanivete"])
        self.assertEqual(nos["kani:ferramenta:abrir"]["ambitos"], ["pc"])
        self.assertEqual(nos["kani:ferramenta:abrir"]["programa"], "Explorer")
        self.assertEqual(nos["kani:ferramenta:responder"]["ambitos"], ["kani_local"])
        self.assertEqual(nos["habilidades:politica"]["finalidade"], "regra")

    def test_entrada_sem_origem_ou_categoria_valida_nao_inventa_registro(self):
        registro = self.registro()
        registro["ferramentas"]["video_download"].pop("origem")
        registro["ferramentas"]["abrir"]["categoria"] = "suposta"
        self.habilitar(registro)
        nos = {n["chave"]: n for n in c.ler()["nos"]}
        self.assertEqual(nos["kani:ferramenta:video_download"]["ambitos"], ["kani_local"])
        self.assertNotIn("categoria_habilidade", nos["kani:ferramenta:abrir"])

    def test_atualizar_registro_invalida_indice_derivado(self):
        caminho = self.habilitar()
        primeiro = c.ler()
        dados = self.registro()
        dados["ferramentas"]["video_download"]["procedimento"] = "Fluxo atualizado com detalhe confirmado."
        caminho.write_text(json.dumps(dados), encoding="utf-8")
        st = caminho.stat()
        os.utime(caminho, (st.st_atime, st.st_mtime + 2))
        segundo = c.ler()
        self.assertIsNot(primeiro, segundo)
        n = next(n for n in segundo["nos"] if n["chave"] == "kani:ferramenta:video_download")
        self.assertIn("Fluxo atualizado", n["texto"])

    def test_interface_projeto_e_recuperada_somente_no_kanicode(self):
        registro = self.registro()
        real = json.loads(Path(c.REGISTRO_HABILIDADES).read_text(encoding='utf-8'))
        registro['interfaces'] = {'painel_projeto': real['interfaces']['painel_projeto']}
        self.habilitar(registro)
        import cerebro_motor as motor
        with patch.object(motor, '_IDX', {'assinatura': None, 'd': None}):
            encontrados = motor.buscar('painel_projeto', modo='lexical', agente='codex', ambito='kanicode', profundidade=0, marcar=False)
            fora = motor.buscar('painel_projeto', modo='lexical', agente='codex', ambito='kanivete', profundidade=0, marcar=False)
        chave = 'kanicode:interface:painel_projeto'
        self.assertTrue(any(n['chave'] == chave for n in encontrados))
        self.assertFalse(any(n['chave'] == chave for n in fora))

    def test_programa_externo_nao_e_distribuido_como_vanilla(self):
        real = json.loads(Path(c.REGISTRO_HABILIDADES).read_text(encoding='utf-8'))
        self.assertNotIn('demandas_panda', real['ferramentas'])
        import conhecimento_fontes
        with patch.object(conhecimento_fontes, 'instalados', return_value={}):
            nos = list(FONTE_KANI())
        self.assertNotIn('kani:ferramenta:demandas_panda', {n['chave'] for n in nos})

    def test_auto_colab_recuperavel_so_no_kanicode(self):
        real = json.loads(Path(c.REGISTRO_HABILIDADES).read_text(encoding='utf-8'))
        registro = self.registro()
        registro['interfaces'] = {'auto_colab': real['interfaces']['auto_colab']}
        self.habilitar(registro)
        import cerebro_motor as motor
        with patch.object(motor, '_IDX', {'assinatura': None, 'd': None}):
            dentro = motor.buscar('auto_colab', modo='lexical', agente='codex', ambito='kanicode', profundidade=0, marcar=False)
            fora = motor.buscar('auto_colab', modo='lexical', agente='codex', ambito='kanivete', profundidade=0, marcar=False)
        chave = 'kanicode:interface:auto_colab'
        self.assertTrue(any(n['chave'] == chave for n in dentro))
        self.assertFalse(any(n['chave'] == chave for n in fora))

    def test_motor_rag_encontra_habilidade_no_ambito_correto(self):
        self.habilitar()
        import cerebro_motor as motor
        with patch.object(motor, "_IDX", {"assinatura": None, "d": None}):
            encontrados = motor.buscar("video_download", modo="lexical", agente="codex", ambito="kanicode",
                                        profundidade=0, marcar=False)
            fora = motor.buscar("video_download", modo="lexical", agente="codex", ambito="kanivete",
                                 profundidade=0, marcar=False)
        self.assertTrue(any(n["chave"] == "kani:ferramenta:video_download" for n in encontrados))
        self.assertFalse(any(n["chave"] == "kani:ferramenta:video_download" for n in fora))


if __name__ == "__main__":
    unittest.main()
