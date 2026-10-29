"""Landing e HTML seguem no motor de codigo, mesmo com termos de arte."""
import unittest
import pickle_agente as pa


class RotaWebTest(unittest.TestCase):
    def test_landing_com_assets_nao_vai_para_arte(self):
        self.assertFalse(pa.para_ponte("Refine a landing page com logo, imagens e assets"))
        self.assertFalse(pa.para_ponte("Ajuste o contraste do banner em HTML/CSS"))

    def test_continuacao_herda_codigo_web(self):
        self.assertIsNone(pa.rota_ponte("Pode continuar", ["Crie uma landing com logo do KaniCode"]))

    def test_arte_no_photo_permanece_na_ponte(self):
        self.assertTrue(pa.para_ponte("Crie um flyer no Photo com logo"))
        self.assertTrue(pa.para_ponte("Abra o site no navegador"))
