"""Fontes de conhecimento isoladas: pessoal nunca vira vanilla; plugin depende da instalacao."""
import json
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import conhecimento_fontes as f
import perfil_cerebro as c


class FontesTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="fontes_", dir="D:/kanivete_testes"))

    def test_nucleo_publico_sem_programas_externos(self):
        registro = f.ler(Path(c.__file__).parent / "habilidades_registro.json")
        f.validar_publico(registro)
        self.assertNotIn("demandas_panda", registro["ferramentas"])

    def test_migracao_aditiva_idempotente(self):
        with patch.object(f, "pasta_dados", return_value=self.base):
            destino = f.preservar_legado({"ferramentas": {"pessoal": {"procedimento": "meu fluxo"}}})
            antes = destino.read_bytes()
            f.preservar_legado({"ferramentas": {"outra": {}}})
            self.assertEqual(destino.read_bytes(), antes)
            self.assertIn("meu fluxo", destino.read_text())

    def test_catalogo_nao_ensina_plugin_ausente(self):
        with patch.object(f, "instalados", return_value={}):
            nos = list(c._fonte_ferramentas_kani())
        self.assertTrue(nos)
        self.assertFalse(any(n.get("plugin_id") for n in nos))
        self.assertNotIn("kani:ferramenta:rodar_js_kanivete", {n["chave"] for n in nos})
        self.assertNotIn("kani:ferramenta:demandas_panda", {n["chave"] for n in nos})

    def test_plugin_instalado_tem_origem_propria(self):
        with patch.object(f, "instalados", return_value={"kanivete": {"nome": "Kanivete"}}):
            nos = list(c._fonte_ferramentas_kani())
        no = next(n for n in nos if n["chave"] == "kani:ferramenta:rodar_js_kanivete")
        self.assertEqual(no["camada"], "plugin")
        self.assertEqual(no["plugin_id"], "kanivete")

    def test_registro_vem_do_diretorio_do_plugin(self):
        (self.base / "conhecimento.json").write_text(json.dumps({"interfaces": {"demo": {"procedimento": "procedimento do plugin"}}}))
        self.assertEqual(list(f.registros_plugins({})), [])
        r = list(f.registros_plugins({"demo": {"pasta": str(self.base)}}))
        self.assertEqual(r[0][:2], ("demo", "demo"))

    def test_registro_pessoal_fora_do_publico(self):
        local = self.base / "cerebro"; local.mkdir()
        (local / "conhecimento_pessoal.json").write_text(json.dumps({"registro_anterior_v1": {"interfaces": {"meu": {"procedimento": "meu fluxo"}}}}))
        with patch.object(c, "DADOS", str(self.base)), patch.object(f, "instalados", return_value={}):
            r = list(c._fonte_conhecimento_pessoal())
        self.assertEqual(r[0]["camada"], "pessoal")
        self.assertTrue(r[0]["fonte"].startswith(str(self.base)))

    def test_validacao_publica_recusa_mistura_e_caminhos(self):
        for registro in [
            {"versao": 2, "camada": "vanilla", "ferramentas": {"demandas_panda": {"categoria": "kanicode_vanilla"}}},
            {"versao": 2, "camada": "vanilla", "texto": "D:/pessoal/cliente"}]:
            with self.assertRaises(ValueError): f.validar_publico(registro)

    def test_pacote_recusa_dados_mesmo_rastreados(self):
        for arquivo in ['cerebro/neuronios.json', 'perfil/usuario.json', 'client_secret_exemplo.json', 'estado.db']:
            with self.assertRaises(ValueError): f.validar_pacote([arquivo])
        f.validar_pacote(['perfil_cerebro.py', 'plugins/kanivete/conhecimento.json'])

    def test_instalador_embute_pacote_completo(self):
        import zipfile
        import construir_instalador as instalador
        pacote = self.base / 'app.zip'
        with zipfile.ZipFile(pacote, 'w') as z:
            z.writestr('KaniCode/KaniCode.exe', b'exe simulado')
            z.writestr('KaniCode/_internal/python313.dll', b'biblioteca simulada')
        sed, exe = instalador.preparar(pacote, self.base / 'saida', '0.1.1')
        self.assertEqual(exe.name, 'KaniCode-0.1.1-Setup.exe')
        self.assertIn('IEXPRESS', sed.read_text())
        script = (self.base / 'saida/instalar.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('Expand-Archive', script)
        self.assertIn('Start-Process', script)
        self.assertTrue((self.base / 'saida/pacote.zip').is_file())

    def test_visitante_nao_le_aprendizado_pessoal_sobre_o_app(self):
        import cerebro_motor as motor
        no = {'camada':'pessoal','ambitos':['kanicode'],'area':'dev'}
        perm = {'ler':['kanicode'],'camadas':['vanilla','plugin']}
        self.assertFalse(motor._visivel(no, perm))
        no['camada'] = 'vanilla'
        self.assertTrue(motor._visivel(no, perm))
