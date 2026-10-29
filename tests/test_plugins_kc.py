"""Plugins do KaniCode (plugins_kc.py): achar pelo kanicode.json, ligar/desligar em dados de teste e a linha das instruções."""
import json, os, sys, tempfile, unittest
from pathlib import Path

os.environ["KANICODE_TESTE"] = "1"
os.environ["KANICODE_DADOS_TESTE"] = tempfile.mkdtemp(dir="D:/kanivete_testes", prefix="kc_plugins_")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import plugins_kc


class TestPlugins(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(dir="D:/kanivete_testes", prefix="kc_plugpastas_"))
        p = self.base / "demo"
        p.mkdir()
        (p / "demo.py").write_text("import sys; print('{\"nome\": \"teste\"}'); sys.exit(0)", encoding="utf-8")
        (p / "kanicode.json").write_text(json.dumps({"nome": "Demo", "cli": "demo.py", "comandos": ["listar"],
                                                     "verificar": ["quem"]}), encoding="utf-8")
        (self.base / "sem_manifesto").mkdir()
        q = self.base / "fixo"
        q.mkdir()
        (q / "kanicode.json").write_text(json.dumps({"nome": "Fixo", "cli": "x.py", "prompt": False}), encoding="utf-8")
        self.antes = plugins_kc.PASTAS
        plugins_kc.PASTAS = [self.base]

    def tearDown(self):
        plugins_kc.PASTAS = self.antes
        plugins_kc._estado_arq().unlink(missing_ok=True)

    def test_lista_so_com_manifesto(self):
        self.assertEqual([p["id"] for p in plugins_kc.listar()], ["demo", "fixo"])

    def test_ligar_e_prompt(self):
        self.assertIn("Demo", plugins_kc.linha_prompt())
        self.assertNotIn("Fixo", plugins_kc.linha_prompt())   # prompt false
        plugins_kc.ligar("demo", False)
        self.assertFalse(plugins_kc.achar("demo")["ligado"])
        self.assertEqual(plugins_kc.linha_prompt(), "")
        self.assertTrue(str(plugins_kc._estado_arq()).startswith(os.environ["KANICODE_DADOS_TESTE"]))

    def test_lobo_plugins_no_cerebro(self):
        import perfil_cerebro as pc
        nos = list(pc._fonte_plugins())
        self.assertEqual([n["chave"] for n in nos], ["plugins:indice", "plugin:demo", "plugin:demo:cmd:0", "plugin:fixo"])
        self.assertTrue(all(n["area"] == "plugins" for n in nos))
        self.assertEqual(nos[1]["grupo_plugin"], "plugin_demo")
        self.assertIn("Como usar", nos[1]["texto"])
        self.assertIn("Quem chama", nos[1]["texto"])
        self.assertEqual(pc.GRUPOS["plugin_demo"], "Demo")

    def test_verificar(self):
        r = plugins_kc.verificar("demo")
        self.assertTrue(r["conectado"])
        self.assertEqual(r["detalhe"], "teste")


if __name__ == "__main__":
    unittest.main()
