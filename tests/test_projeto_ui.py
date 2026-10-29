"""Painel Projeto no layout real; arquivos sintéticos e Git isolado sem commits."""
import os, sys, unittest
import test_layout as layout
from test_conexoes_ui import ConexoesUITest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import projeto

import shutil, subprocess, tempfile


def _repo_de_teste():
    """repositório git próprio com uma alteração conhecida (antes usava o git real e dependia do que estava mudado)"""
    base = "D:/kanivete_testes" if os.path.isdir("D:/kanivete_testes") else None
    raiz = tempfile.mkdtemp(prefix="projeto_ui_", dir=base)
    os.makedirs(os.path.join(raiz, "kanicode", "ui"))
    for rel, txt in (("kanicode/projeto.py", "def a():\n    return 1\n"), ("kanicode/ui/movel.js", "// movel\n")):
        with open(os.path.join(raiz, rel), "w", encoding="utf-8") as f:
            f.write(txt)
    git = lambda *a: subprocess.run(["git", "-C", raiz, *a], check=True, capture_output=True)
    git("init", "-q")
    git("add", "-A")
    # Sem commits: o índice fornece a referência do repositório sintético.
    with open(os.path.join(raiz, "kanicode", "projeto.py"), "a", encoding="utf-8") as f:
        f.write("\ndef b():\n    return 2\n")
    return raiz


PASTA = _repo_de_teste() if shutil.which("git") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@unittest.skipUnless(layout.sync_playwright, 'Playwright opcional não instalado')
class ProjetoUITest(unittest.TestCase):
    setUpClass = classmethod(ConexoesUITest.setUpClass.__func__)
    setUp = layout.LayoutTest.setUp

    def tearDown(self):
        self.assertEqual(self.erros, [])

    def ligar(self):
        p = self.page
        f = {"arvore": projeto.arvore, "diff": projeto.diff, "ler": projeto.ler, "buscar": projeto.buscar}
        def ponte(acao, arq='', dados=None):
            base = getattr(self, 'pasta_ativa', PASTA)
            if acao == 'contexto':
                return dict(ok=True, aba='teste', raiz=base, nome=os.path.basename(base))
            if acao == 'salvar':
                return projeto.salvar(base, arq, dados)
            return projeto.alteracoes(base) if acao == 'alteracoes' else f[acao](base, arq)
        p.expose_function('pjReal', ponte)
        p.evaluate('''() => { const anterior=pywebview.api;
          pywebview.api=new Proxy(anterior,{get:(alvo,nome)=>nome==='projeto' ? (a,b,c)=>window.pjReal(a,b||'',c) : alvo[nome]}); }''')

    def test_editar_salvar_e_conflito_preserva_rascunho(self):
        p = self.page
        self.ligar()
        p.click('#proj-trilho')
        p.wait_for_function('window.kcProjeto.P.contexto !== null')
        p.evaluate("kcProjeto.abrir('kanicode/projeto.py')")
        p.wait_for_selector('#pj-editar', state='visible')
        p.click('#pj-editar')
        p.wait_for_selector('#pj-editor', state='visible')
        p.fill('#pj-editor', 'print("manual")\n')
        p.screenshot(path='D:/kanivete_testes/projeto_editor.png')
        p.locator('#pj-editor').press('Control+s')
        p.wait_for_selector('#pj-editor', state='hidden')
        caminho = os.path.join(PASTA, 'kanicode', 'projeto.py')
        with open(caminho, encoding='utf-8') as f:
            self.assertEqual(f.read(), 'print("manual")\n')
        p.click('#pj-editar')
        p.fill('#pj-editor', 'meu rascunho')
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write('mudou por fora\n')
        p.click('#pj-salvar')
        p.wait_for_function("document.getElementById('pj-aviso').textContent.includes('mudou no disco')")
        self.assertEqual(p.input_value('#pj-editor'), 'meu rascunho')
        with open(caminho, encoding='utf-8') as f:
            self.assertEqual(f.read(), 'mudou por fora\n')
        p.click('#pj-cancelar')
        p.wait_for_selector('#pj-editor', state='hidden')

    def test_troca_automatica_e_rascunho_durante_troca(self):
        p = self.page
        tmp = tempfile.TemporaryDirectory(dir='D:/kanivete_testes', prefix='projeto_troca_')
        self.addCleanup(tmp.cleanup)
        outra = tmp.name
        with open(os.path.join(outra, 'outro.py'), 'w', encoding='utf-8') as f:
            f.write('print("outro")\n')
        self.ligar()
        p.click('#proj-trilho')
        p.wait_for_function('window.kcProjeto.P.contexto !== null')
        p.evaluate("kcProjeto.abrir('kanicode/projeto.py')")
        p.wait_for_selector('#pj-editar', state='visible')
        p.click('#pj-editar')
        p.fill('#pj-editor', 'rascunho conservado')
        self.pasta_ativa = outra
        p.evaluate('kcProjeto.atualizar()')
        self.assertEqual(p.input_value('#pj-editor'), 'rascunho conservado')
        p.click('#pj-salvar')
        p.wait_for_function("document.getElementById('pj-aviso').textContent.includes('projeto mudou')")
        self.assertEqual(p.input_value('#pj-editor'), 'rascunho conservado')
        p.click('#pj-cancelar')
        p.wait_for_selector('#pj-corpo .pj-it[data-rel="outro.py"]')
        self.assertEqual(p.locator('#pj-contexto').text_content(), outra)
        self.assertEqual(p.locator('#pj-corpo .pj-it[data-rel="kanicode"]').count(), 0)
        p.locator('#pj-corpo .pj-it[data-rel="outro.py"]').click()
        p.wait_for_function("document.getElementById('pj-codigo').textContent.includes('outro')")
        with open(os.path.join(outra, 'outro.py'), 'w', encoding='utf-8') as f:
            f.write('print("atualizado")\n')
        p.evaluate('kcProjeto.atualizar()')
        p.wait_for_function("document.getElementById('pj-codigo').textContent.includes('atualizado')")

    def test_arvore_alteracoes_e_diff(self):
        p = self.page
        self.ligar()
        p.click('#proj-trilho')
        p.wait_for_selector('#proj-painel .pj-it', state='visible')
        self.assertTrue(p.locator('#proj-painel').is_visible())
        self.assertFalse(p.locator('#atv-lista').is_visible())   # a seção Atividades some
        p.locator('#pj-corpo .pj-it.dir', has_text='kanicode').first.click()
        p.wait_for_selector('#pj-corpo .pj-it[data-rel="kanicode/projeto.py"]')
        p.screenshot(path=r'D:\kanivete_testes\projeto_arquivos.png')
        p.click('.pj-abas button[data-aba="alt"]')
        p.wait_for_selector('#pj-corpo .pj-ramo')
        n = p.locator('#pj-corpo .pj-it').count()
        self.assertEqual(n, len(projeto.alteracoes(PASTA)['itens']))
        p.locator('#pj-corpo .pj-it[data-rel="kanicode/projeto.py"]').click()
        p.wait_for_selector('#pj-codigo .pj-l.mais')
        self.assertTrue(p.locator('#pj-ver').is_visible())
        p.set_viewport_size({'width': 500, 'height': 740})
        p.screenshot(path=r'D:\kanivete_testes\projeto_diff.png')
        p.set_viewport_size({'width': 1200, 'height': 740})
        p.screenshot(path=r'D:\kanivete_testes\projeto_largo.png')
        p.click('#pj-citar')
        self.assertIn('kanicode/projeto.py', p.input_value('#texto'))
        p.click('#pj-voltar')
        p.click('.pj-abas button[data-aba="arq"]')
        p.fill('#pj-filtro', 'movel.js')
        p.wait_for_selector('#pj-corpo .pj-it[data-rel="kanicode/ui/movel.js"]')
        p.click('#atv-trilho')
        self.assertFalse(p.locator('#proj-painel').is_visible())


def tearDownModule():
    if os.path.basename(PASTA).startswith("projeto_ui_"):
        shutil.rmtree(PASTA, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
