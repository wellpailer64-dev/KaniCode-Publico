"""Navegação do KaniCode Brain em Chromium isolado, sem dados pessoais reais."""
from pathlib import Path
import unittest
import test_layout as layout
import test_conexoes_ui as conexoes
import test_cerebro_projetos as projetos
from test_cerebro_estrutura import preparar_pessoal
import perfil_cerebro as c


@unittest.skipUnless(layout.sync_playwright, "Playwright não instalado")
class EstruturaCerebroUITest(unittest.TestCase):
    setUpClass = classmethod(conexoes.ConexoesUITest.setUpClass.__func__)

    def setUp(self):
        projetos.ProjetosTest.setUp(self)
        layout.LayoutTest.setUp(self)
        self.page.set_viewport_size({"width": 1280, "height": 860})
        self.projeto, self.pessoa = preparar_pessoal(self.tmp.name)
        dados = c.ler()
        self.page.expose_function("dadosEstrutura", lambda: dados)
        self.page.evaluate("""() => {
            const anterior=pywebview.api;
            pywebview.api=new Proxy(anterior,{get:(alvo,nome) =>
              nome==='cerebro_ler' ? (() => dadosEstrutura()) : alvo[nome]});
            const el=document.createElement('div');el.id='estrutura-teste';el.className='cerebro grande';
            document.body.appendChild(el);localStorage.setItem('cerebro-som','0');
        }""")
        codigo = (Path(__file__).resolve().parents[1] / "ui/cerebro.js").read_text(encoding="utf-8")
        codigo = codigo.replace("window.Cerebro = { montar, tocar };",
            "window.Cerebro = { montar, tocar, renderizarTeste: () => { C.auto=false; medir(); desenhar(performance.now()); }, pontosTeste: () => C.pts.map(p=>({titulo:p.titulo,tipo:p.tipo,area:p.area})), selecionarTeste: chave => { C.sel=C.pts.find(p=>p.no?.chave===chave); cartao(C.sel); } };")
        self.page.add_script_tag(content=codigo)
        self.page.evaluate("async () => Cerebro.montar(document.querySelector('#estrutura-teste'), {nome:'Nome antigo'})")

    def tearDown(self):
        projetos.ProjetosTest.tearDown(self)
        self.assertEqual(self.erros, [])

    def test_centro_nome_categorias_e_navegacao_de_conexoes(self):
        p = self.page
        pontos = p.evaluate("Cerebro.pontosTeste()")
        self.assertEqual(pontos[0]["titulo"], "KaniCode Brain")
        self.assertTrue(any(x["tipo"] == "area" and x["area"] == "eu" and x["titulo"] == "Wellington Pailer" for x in pontos))
        self.assertTrue(any(x["tipo"] == "grupo" and x["titulo"] == "Vínculos sociais" for x in pontos))
        p.evaluate("chave => Cerebro.selecionarTeste(chave)", self.pessoa)
        cartao = p.locator("#estrutura-teste .cer-cartao")
        self.assertIn("Ana de exemplo", cartao.inner_text())
        self.assertIn("Ligação registrada", cartao.inner_text())
        cartao.locator(f'[data-cer-conexao="{self.projeto}"]').click()
        self.assertEqual(cartao.locator(":scope > b").inner_text(), "Projeto de exemplo")
        p.evaluate("Cerebro.renderizarTeste()")
        p.screenshot(path="D:/kanivete_testes/cerebro_estrutura_projeto.png")
        p.evaluate("chave => Cerebro.selecionarTeste(chave)", self.pessoa)
        cartao.locator('[data-cer-conexao="perfil:dados"]').click()
        self.assertEqual(cartao.locator(":scope > b").inner_text(), "Wellington Pailer")
        p.evaluate("Cerebro.renderizarTeste()")
        p.screenshot(path="D:/kanivete_testes/cerebro_estrutura_pessoal.png")


if __name__ == "__main__":
    unittest.main()
