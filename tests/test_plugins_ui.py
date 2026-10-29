"""Configurações > Plugins na tela real (navegador headless isolado, ponte simulada, sem Pandalab real)."""
from pathlib import Path
import os, unittest
import test_layout as layout
sync_playwright = layout.sync_playwright


@unittest.skipUnless(sync_playwright, 'Playwright opcional não instalado')
class PluginsUITest(unittest.TestCase):
    setUpClass = classmethod(lambda cls: __import__('test_conexoes_ui').ConexoesUITest.setUpClass.__func__(cls))

    def setUp(self):
        layout.LayoutTest.setUp(self)
        self.page.evaluate('''() => {
          window.plugTeste = [{id:'pandalab',nome:'Pandalab',sigla:'Pl',cor:'#7AD0FF',descricao:'<b>x</b> demandas',pasta:'D:/p',icone:'D:/p/icone.png',
            cli:'D:/p/panda.py',comandos:[{cmd:'demandas --status abertas',faz:'lista'}],serve:'serve <i>x</i>',chamado_por:['Kani'],guia:'',verificar:['quem'],erro:'',ligado:true,tambem_kanivete:true,prompt:true},
            {id:'kanibrowser',nome:'KaniBrowser',sigla:'Kb',cor:'#F0A01C',descricao:'navegador',pasta:'D:/k',icone:'',cli:'D:/k/kb.py',
            comandos:[],serve:'',chamado_por:[],guia:'',verificar:[],erro:'',ligado:false,tambem_kanivete:true,prompt:false}];
          window.plugChamadas = [];
          const anterior = window.pywebview.api;
          window.pywebview.api = new Proxy({}, {get:(_, nome) => {
            if (!nome.startsWith('plugins_')) return anterior[nome];
            return async (...a) => { plugChamadas.push({nome, a});
              if (nome === 'plugins_listar') return plugTeste;
              if (nome === 'plugins_logo') return 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="#f60"/></svg>');
              if (nome === 'plugins_verificar') return {id:a[0], conectado:true, detalhe:'pailer'};
              if (nome === 'plugins_ligar') { const p = plugTeste.find(x => x.id === a[0]); p.ligado = a[1]; return p; }
              return true; };
          }});
        }''')

    def test_abre_lista_verifica_e_liga(self):
        p = self.page
        p.evaluate('window.kaniPluginsAbrir()')
        p.wait_for_selector('#plugins-dlg .plugin', state='visible')
        self.assertTrue(p.locator('#plugins-dlg').is_visible())
        self.assertEqual(p.locator('#plugins-lista .plugin').count(), 2)
        self.assertEqual(p.locator('#plugins-lista i').count(), 0)   # texto escapado
        p.wait_for_selector('.plugin img.plugin-logo', state='visible')   # logo no lugar da sigla
        self.assertEqual(p.locator('.plugin').first.locator('.plugin-sigla').count(), 0)
        p.wait_for_function("document.querySelector('.plugin.conectado .plugin-situacao')?.textContent.includes('pailer')")
        p.locator('.plugin').nth(1).locator('.plugin-chave').click()
        p.wait_for_function("plugChamadas.some(c => c.nome === 'plugins_ligar' && c.a[0] === 'kanibrowser' && c.a[1] === true)")
        p.wait_for_function("document.getElementById('plugins-resumo').textContent.includes('2 ligados')")
        caixa = p.locator('#plugins-dlg').bounding_box()
        self.assertGreater(caixa['width'], 300)
        os.makedirs('D:/kanivete_testes/kanicode_prints', exist_ok=True)
        p.screenshot(path='D:/kanivete_testes/kanicode_prints/plugins.png')
        p.locator('#plugins-fechar').click()
        self.assertFalse(p.locator('#plugins-dlg').is_visible())


if __name__ == '__main__':
    unittest.main()
