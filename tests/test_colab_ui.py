"""Colab e mensagens integrais no Board, em Chromium isolado e com ponte simulada."""
from test_board_ui import BoardUiTest
import unittest


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(ColabUiTest(n) for n in (
        "test_codex_logs_e_texto_completo_sem_abrir_aba", "test_colab_criar_e_atualizar_sem_trocar_chat",
        "test_auto_colab_configuracao_persiste_e_informa_falha",
        "test_colab_execucao_abre_board_e_nao_reabre_no_diario",
        "test_colab_aguarda_fio_e_fecha_painel_ao_executar"))


class ColabUiTest(BoardUiTest):
    def test_colab_execucao_abre_board_e_nao_reabre_no_diario(self):
        p = self.page
        p.evaluate("""ABAS_T.lista.push({id:'3',quem:'codex',nome:'Outro trabalho'});
          KC_ABAS.lista = JSON.parse(JSON.stringify(ABAS_T.lista));
          KC_BOARD.estado.cards = {'1':{x:4000,y:3000,w:1000,h:860},
            '2':{x:12000,y:0,w:1000,h:860},'3':{x:50000,y:0,w:1000,h:860}};
          FIOS = [{id:'auto1',de:'1',para:'2',modo:'colab'}];
          kcEv({t:'fios',lista:FIOS});
          window.SAUTO = {membros:['1','2'],coordenador:'1',automatico:true,fase:'planejamento'};
          kcEv({t:'colab',id:'auto1',estado:{...SAUTO}});""")
        self.assertFalse(p.evaluate('KC_BOARD.estado.on'))
        p.evaluate("SAUTO.fase='execucao'; kcEv({t:'colab',id:'auto1',estado:{...SAUTO}})")
        self.assertTrue(p.locator('#board').is_visible())
        self.assertTrue(p.locator('.bd-fios').text_content().find('Colab') >= 0)
        for aba in ('1', '2'):
            r = p.locator('.bd-card[data-aba="' + aba + '"]').bounding_box()
            b = p.locator('#board').bounding_box()
            self.assertGreaterEqual(r['x'], b['x'])
            self.assertLessEqual(r['x'] + r['width'], b['x'] + b['width'] + 1)
        self.assertEqual(p.evaluate("KC_BOARD.estado.cards['3'].x"), 50000)
        self.assertEqual(p.evaluate('KC_ABAS.ativa'), '1')
        p.screenshot(path='D:/kanivete_testes/colab_board_automatico.png')
        p.evaluate("KC_BOARD.alternar(false); kcEv({t:'colab',id:'auto1',estado:{...SAUTO,diario:[{texto:'andamento'}]}})")
        self.assertFalse(p.evaluate('KC_BOARD.estado.on'))
        self.assertEqual(self.erros, [])

    def test_colab_aguarda_fio_e_fecha_painel_ao_executar(self):
        p = self.page
        p.evaluate("kcEv({t:'colab',id:'manual1',estado:{membros:['1','2'],fase:'execucao'}})")
        self.assertFalse(p.evaluate('KC_BOARD.estado.on'))
        p.evaluate("""FIOS = [{id:'manual1',de:'1',para:'2',modo:'colab'}];
          kcEv({t:'fios',lista:FIOS});""")
        self.assertTrue(p.evaluate('KC_BOARD.estado.on'))
        p.evaluate("KC_COLAB.abrir('1','2')")
        self.assertTrue(p.locator('.bd-colab').is_visible())
        p.evaluate("""kcEv({t:'colab',id:'manual2',estado:{membros:['1','2'],fase:'execucao'}});
          FIOS = [{id:'manual2',de:'1',para:'2',modo:'colab'}]; kcEv({t:'fios',lista:FIOS});""")
        self.assertFalse(p.locator('.bd-colab').is_visible())
        self.assertEqual(self.erros, [])

    def test_auto_colab_configuracao_persiste_e_informa_falha(self):
        p = self.page
        p.evaluate("""window.AUTO_TESTE = true; window.AUTO_FALHA = false;
          const antes = pywebview.api;
          pywebview.api = new Proxy(antes, {get: (alvo, nome) => nome === 'auto_colab' ? async on => {
            if (AUTO_FALHA) throw new Error('falha simulada');
            if (typeof on === 'boolean') AUTO_TESTE = on;
            return AUTO_TESTE;
          } : alvo[nome]});
          dispatchEvent(new Event('pywebviewready'));""")
        p.wait_for_function("document.querySelector('#auto-colab').getAttribute('aria-checked') === 'true'")
        p.click('#ferramentas-bt')
        bt = p.locator('#auto-colab')
        self.assertEqual(bt.get_attribute('role'), 'switch')
        self.assertIn('Ligado', bt.inner_text())
        bt.click()
        p.wait_for_function('AUTO_TESTE === false')
        self.assertEqual(bt.get_attribute('aria-checked'), 'false')
        self.assertIn('Desligado', bt.inner_text())
        p.evaluate('AUTO_FALHA = true')
        bt.click()
        p.wait_for_function("document.querySelector('#conversa').textContent.includes('Não deu para alterar o Auto-Colab.')")
        self.assertEqual(bt.get_attribute('aria-checked'), 'false')
        self.assertFalse(bt.is_disabled())
        p.evaluate("kcEv({t:'auto_colab',on:true})")
        self.assertEqual(bt.get_attribute('aria-checked'), 'true')
        p.screenshot(path='D:/kanivete_testes/auto_colab_config.png')
        self.assertEqual(self.erros, [])

    def test_codex_logs_e_texto_completo_sem_abrir_aba(self):
        p = self.page
        p.click('.aba-board')
        p.wait_for_selector('.bd-card[data-aba="2"] .msg')
        p.evaluate("""kcEv({t:'ajudante',quem:'codex',fase:'inicio',aba:'2'});
          kcEv({t:'codex_progresso',id:'x',texto:'A'.repeat(1600)+'FIM_INTEGRAL',aba:'2'});
          kcEv({t:'ajudante',quem:'codex',fase:'passo',texto:'executando teste',entrada:{command:'py -3.13 teste.py'},aba:'2'});
          kcEv({t:'ajudante',quem:'codex',fase:'passo',operacao:'fim',saida:'TESTE_PASSOU',ok:true,aba:'2'});""")
        p.wait_for_function("document.querySelector('.bd-card[data-aba=\"2\"] .bd-aovivo')?.textContent.includes('FIM_INTEGRAL')")
        p.wait_for_function("document.querySelector('.bd-card[data-aba=\"2\"] .bd-aovivo')?.textContent.includes('TESTE_PASSOU')")
        self.assertEqual(p.evaluate('KC_ABAS.ativa'), '1')
        self.assertIn('py -3.13 teste.py', p.locator('.bd-card[data-aba="2"] .bd-aovivo').inner_text())
        p.screenshot(path='D:/kanivete_testes/colab/board_logs.png')
        self.assertEqual(self.erros, [])

    def test_colab_criar_e_atualizar_sem_trocar_chat(self):
        p = self.page
        p.evaluate("""window.SCOLAB = {membros:['1','2'],coordenador:'1',objetivo:'Site de teste',fase:'planejamento',revisao:0,aprovacoes:[],tarefas:[],contrato:'',diario:[]};
          const anterior = pywebview.api;
          pywebview.api = new Proxy({}, {get:(_,nome) => async (...args) => {
            if(nome === 'colab_criar') { FIOS=[{id:'c1',de:'1',para:'2',modo:'colab'}]; kcEv({t:'fios',lista:FIOS}); return FIOS[0]; }
            if(nome === 'colab_consultar') return SCOLAB;
            if(nome === 'colab_planejar') { chamadas.push({nome,args}); return true; }
            return anterior[nome](...args);
          }}); void 0;""")
        p.click('.aba-board'); p.click('[data-acao="colab"]')
        p.fill('.colab-objetivo', 'Site de teste')
        p.click('.colab-criar')
        p.wait_for_function("chamadas.some(c=>c.nome==='colab_planejar')")
        p.evaluate("SCOLAB.fase='execucao'; SCOLAB.revisao=1; SCOLAB.aprovacoes=['1','2']; SCOLAB.diario=[{aba:'2',texto:'Interface pronta para API'}]; kcEv({t:'colab',id:'c1',estado:SCOLAB})")
        p.wait_for_function("document.querySelector('.colab-estado').textContent.includes('Interface pronta para API')")
        self.assertIn('Executando em paralelo', p.locator('.colab-estado').inner_text())
        self.assertEqual(p.evaluate('KC_ABAS.ativa'), '1')
        p.screenshot(path='D:/kanivete_testes/colab/colab_plano.png')
        self.assertEqual(self.erros, [])
