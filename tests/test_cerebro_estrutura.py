"""Centro do cérebro e núcleo pessoal: fatos sintéticos e vínculos explícitos no D."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_cerebro_projetos as projetos
import perfil_cerebro as c


def preparar_pessoal(base):
    perfil = Path(base) / "perfil"
    perfil.mkdir(exist_ok=True)
    (perfil / "usuario.json").write_text(json.dumps({"nome": "Wellington Pailer", "apelido": "Pailer"}), encoding="utf-8")
    projeto = c.guardar("Projeto de exemplo", "Projeto confirmado para a fixture.", tipo="project", area="dev",
                       certeza="verificado", origem="fixture", forcar=True)["chave"]
    pessoa = c.guardar("Ana de exemplo", "Colega de projeto; vínculo confirmado apenas na fixture.",
                      tipo="vinculo", certeza="pailer", origem="fixture", ligar=[projeto], forcar=True)["chave"]
    c.guardar("Forma de trabalhar", "Prefere explicações diretas.", tipo="feedback", area="eu",
              certeza="pailer", origem="fixture", forcar=True)
    c.guardar("Personalidade confirmada", "Característica declarada na fixture.", tipo="personalidade",
              certeza="pailer", origem="fixture", forcar=True)
    c.guardar("Conhecimento pessoal", "Conhecimento confirmado na fixture.", tipo="conhecimento", area="eu",
              certeza="pailer", origem="fixture", forcar=True)
    return projeto, pessoa


class EstruturaPessoalTest(unittest.TestCase):
    setUp = projetos.ProjetosTest.setUp
    tearDown = projetos.ProjetosTest.tearDown

    def test_centro_e_pessoa_sao_entidades_distintas(self):
        preparar_pessoal(self.tmp.name)
        d = c.ler()
        self.assertEqual(d["centro"]["titulo"], "KaniCode Brain")
        self.assertEqual(d["identidade"], {"nome": "Wellington Pailer", "ref": "perfil:dados"})
        self.assertEqual(next(a["nome"] for a in d["areas"] if a["id"] == "eu"), "Wellington Pailer")
        grupos = {n["grupo"] for n in d["nos"] if n["area"] == "eu"}
        self.assertTrue({"identidade", "caracteristicas", "jeito", "conhecimentos", "vinculos"} <= grupos)

    def test_vinculo_se_liga_a_pessoa_e_ao_projeto_declarado(self):
        projeto, pessoa = preparar_pessoal(self.tmp.name)
        d = c.ler()
        ids = {n["chave"]: n["id"] for n in d["nos"]}
        pares = {frozenset((a, b)) for a, b, forte, peso in d["ligas"] if forte == 1}
        self.assertIn(frozenset((ids[pessoa], ids["perfil:dados"])), pares)
        self.assertIn(frozenset((ids[pessoa], ids[projeto])), pares)
        self.assertEqual(sum(n["tipo"] == "vinculo" for n in d["nos"]), 1)

    def test_contato_comercial_nao_vira_vinculo_pessoal(self):
        preparar_pessoal(self.tmp.name)
        ref = c.guardar("Fornecedor de exemplo", "Contato comercial; não é declaração de vínculo pessoal.",
                        tipo="contato", area="clientes", certeza="verificado", origem="fixture", forcar=True)["chave"]
        self.assertEqual(c._achar(ref)["area"], "clientes")
        self.assertNotEqual(c._achar(ref)["grupo"], "vinculos")

    def test_autoria_nao_retira_protecao_do_nucleo_pessoal(self):
        _, pessoa = preparar_pessoal(self.tmp.name)
        c.classificar(pessoa, ["geral"], "referencia", "fixture", "verificado", agente="kani")
        self.assertEqual(c._achar(pessoa)["area"], "eu")
        import cerebro_motor as motor
        with patch.object(motor, "_IDX", {"assinatura": None, "d": None}):
            r = motor.buscar("Ana de exemplo", modo="lexical", agente="codex", profundidade=0, marcar=False)
        self.assertFalse(any(n["chave"] == pessoa for n in r))


if __name__ == "__main__":
    unittest.main()
