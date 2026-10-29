"""Acordo entre modelos, revisões, reservas e ponte do Colab, sem agentes ou app reais."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import colab
import fios
import kanicode


def proposta():
    return {'acao': 'propor', 'contrato': 'GET /api/itens retorna [{id,nome}]. Interface chama essa rota.',
            'tarefas': [{'aba': '1', 'titulo': 'API', 'arquivos': ['api.py']},
                        {'aba': '2', 'titulo': 'Interface', 'arquivos': ['ui/index.html', 'ui/site.css']}]}


class PlanoTest(unittest.TestCase):
    def test_aprovacao_dos_dois_e_integracao(self):
        s = colab.atualizar(colab.criar('1', '2', 'Site'), '1', proposta())
        with self.assertRaises(ValueError):
            colab.atualizar(s, '1', {'acao': 'executar', 'revisao': 1})
        for aba in ('1', '2'):
            s = colab.atualizar(s, aba, {'acao': 'aprovar', 'revisao': 1})
        s = colab.atualizar(s, '1', {'acao': 'executar', 'revisao': 1})
        self.assertEqual(s['fase'], 'execucao')
        with self.assertRaises(ValueError):
            colab.atualizar(s, '1', {'acao': 'finalizar', 'evidencia': 'cedo demais'})
        for aba in ('1', '2'):
            s = colab.atualizar(s, aba, {'acao': 'concluir_tarefa', 'evidencia': 'Sintaxe e teste da parte passaram'})
        self.assertEqual(s['fase'], 'integracao')
        s = colab.atualizar(s, '1', {'acao': 'finalizar', 'evidencia': 'Frontend consultou a API real no teste conjunto'})
        self.assertEqual(s['fase'], 'concluido')

    def test_revisao_invalida_aprovacoes(self):
        s = colab.atualizar(colab.criar('1', '2', 'Site'), '1', proposta())
        s = colab.atualizar(s, '2', {'acao': 'aprovar', 'revisao': 1})
        novo = colab.atualizar(s, '1', proposta())
        self.assertEqual(novo['aprovacoes'], [])
        self.assertEqual(s['aprovacoes'], ['2'])
        with self.assertRaises(ValueError):
            colab.atualizar(novo, '2', {'acao': 'aprovar', 'revisao': 1})

    def test_reservas_e_caminhos(self):
        for arq in ('API.PY', './api.py', '../fora.py', 'D:/fora.py', 'ui/*'):
            p = proposta(); p['tarefas'][1]['arquivos'] = [arq]
            with self.subTest(arq=arq), self.assertRaises(ValueError):
                colab.atualizar(colab.criar('1', '2', 'Site'), '1', p)
        p = proposta(); p['tarefas'][0]['arquivos'] = ['ui']
        with self.assertRaises(ValueError):
            colab.atualizar(colab.criar('1', '2', 'Site'), '1', p)

    def test_fio_colab_e_bidirecional(self):
        lista, _ = fios.criar([], '1', '2', 'colab')
        self.assertTrue(fios.achar(lista, '2', '1', 'comando'))
        self.assertIn('aba 1', fios.contexto('2', lista, {}))
        self.assertIsNone(fios.achar(lista, '3', '1', 'comando'))


class PonteTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='D:/kanivete_testes')
        self.addCleanup(self.temp.cleanup)
        p = patch.object(kanicode, 'ESTADO', str(Path(self.temp.name) / 'estado.json'))
        p.start(); self.addCleanup(p.stop)
        self.app = kanicode.App.__new__(kanicode.App)
        self.app._abas = {a: SimpleNamespace(pasta=self.temp.name, quem=q, ocupada=Mock(return_value=False))
                          for a, q in [('1', 'claude'), ('2', 'codex')]}
        self.app._para_janela = Mock()
        self.app._colab_enviar = Mock()
        self.f = self.app.colab_criar('1', '2', 'Site com API')

    def chamar(self, de, dados):
        return self.app.colab_atualizar(de, '2' if de == '1' else '1', dados)

    def test_plano_dispara_parceiro_e_continua_integracao(self):
        self.chamar('1', proposta())
        for a in ('1', '2'):
            self.chamar(a, {'acao': 'aprovar', 'revisao': 1})
        self.chamar('1', {'acao': 'executar', 'revisao': 1})
        self.assertEqual(self.app._colab_enviar.call_args.args[0], '2')
        self.app._abas['1'].ocupada.return_value = True
        self.chamar('1', {'acao': 'concluir_tarefa', 'evidencia': 'API testada'})
        self.app._abas['1'].ocupada.return_value = False
        self.chamar('2', {'acao': 'concluir_tarefa', 'evidencia': 'Interface testada'})
        self.assertEqual(self.app.colab_consultar(self.f['id'])['fase'], 'integracao')
        self.assertEqual(self.app._colab_enviar.call_args.args[0], '1')

    def test_integracao_espera_coordenador_terminar(self):
        self.chamar('1', proposta())
        for a in ('1', '2'):
            self.chamar(a, {'acao': 'aprovar', 'revisao': 1})
        self.chamar('1', {'acao': 'executar', 'revisao': 1})
        self.chamar('1', {'acao': 'concluir_tarefa', 'evidencia': 'API pronta'})
        self.app._abas['1'].ocupada.return_value = True
        with patch.object(kanicode.threading, 'Timer') as timer:
            self.chamar('2', {'acao': 'concluir_tarefa', 'evidencia': 'Interface pronta'})
            self.assertTrue(timer.return_value.start.called)
            self.assertEqual(self.app._colab_enviar.call_args.args[0], '2')
            self.app._abas['1'].ocupada.return_value = False
            timer.call_args.args[1]()
        self.assertEqual(self.app._colab_enviar.call_args.args[0], '1')

    def test_aviso_com_parceiro_ocupado_e_erro_sem_fio(self):
        self.app._abas['2'].ocupada.return_value = True
        r = self.app.fio_chamar('1', '2', 'colab', json.dumps({'acao': 'avisar', 'texto': 'API pronta'}))
        self.assertEqual(json.loads(r)['diario'][-1]['texto'], 'API pronta')
        self.assertEqual(self.app._colab_enviar.call_count, 0)
        self.assertTrue(self.app.fio_chamar('3', '2', 'colab', '{}').startswith('ERRO:'))
        self.assertTrue(self.app.fio_chamar('1', '2', 'colab', '[]').startswith('ERRO:'))

    def test_colab_nao_confunde_fio_antigo_e_recusa_troca_de_projeto(self):
        lista = self.app.fios()
        reverso, _ = fios.criar([], '2', '1', 'comando')
        self.app._fios_gravar(reverso + lista)
        self.assertEqual(self.chamar('2', {'acao': 'avisar', 'texto': 'Acordo recebido'})['diario'][-1]['aba'], '2')
        self.app._abas['2'].pasta = 'D:/outro_projeto'
        with self.assertRaises(ValueError):
            self.chamar('1', proposta())

    def test_falha_disparo_nao_deixa_execucao_falsa(self):
        self.chamar('1', proposta())
        for a in ('1', '2'):
            self.chamar(a, {'acao': 'aprovar', 'revisao': 1})
        self.app._colab_enviar.side_effect = RuntimeError('motor indisponível')
        with self.assertRaises(ValueError):
            self.chamar('1', {'acao': 'executar', 'revisao': 1})
        self.assertEqual(self.app.colab_consultar(self.f['id'])['fase'], 'planejamento')



class AutoColabTest(unittest.TestCase):
    def setUp(self):
        import threading
        self.temp = tempfile.TemporaryDirectory(dir='D:/kanivete_testes')
        self.addCleanup(self.temp.cleanup)
        for chave, valor in [('ESTADO', str(Path(self.temp.name) / 'estado.json')), ('DADOS', self.temp.name)]:
            p = patch.object(kanicode, chave, valor)
            p.start(); self.addCleanup(p.stop)
        self.app = kanicode.App.__new__(kanicode.App)
        self.app._abas = {'1': kanicode._Aba('1', 'codex')}
        self.app._abas['1'].pasta = self.temp.name
        self.app._abas['1'].ajudante_ativo = 'codex'
        self.app._fechadas, self.app._aba_ativa = {}, '1'
        self.app._local = threading.local()
        self.app._para_janela = Mock()
        self.app._colab_enviar = Mock()

    def dados(self):
        return {'acao': 'iniciar_auto', 'objetivo': 'Site', 'contrato': 'API e interface com testes',
                'tarefas': [{'aba': 'chamador', 'titulo': 'API', 'arquivos': ['api.py']},
                            {'aba': 'chamado', 'titulo': 'Interface, entregar resumo e testes', 'arquivos': ['ui/site.js']}]}

    def iniciar(self):
        return self.app.fio_chamar('1', 'auto', 'colab', json.dumps(self.dados()))

    def test_desligado_por_padrao_persistencia_e_bloqueio(self):
        self.assertFalse(self.app.auto_colab())
        self.assertIn('desligado', self.iniciar())
        self.assertEqual(len(self.app._abas), 1)
        self.app.auto_colab(True)
        self.assertTrue(kanicode.App.__new__(kanicode.App).auto_colab())
        self.assertIn('AUTO-COLAB LIGADO', self.app._fios_contexto())
        self.app.auto_colab(False)
        self.assertNotIn('AUTO-COLAB LIGADO', self.app._fios_contexto())

    def test_chamador_ocupado_cria_outro_modelo_sem_trocar_aba(self):
        self.app.auto_colab(True)
        s = json.loads(self.iniciar())
        self.assertEqual(s['fase'], 'execucao')
        self.assertEqual(s['coordenador'], '1')
        self.assertEqual(s['membros'], ['1', '2'])
        self.assertEqual(self.app._abas['2'].quem, 'claude')
        self.assertEqual(self.app._abas['2'].pasta, self.temp.name)
        self.assertEqual(self.app._aba_ativa, '1')
        self.assertEqual(s['tarefas'][1]['titulo'], self.dados()['tarefas'][1]['titulo'])
        self.assertEqual(self.app._colab_enviar.call_args.args[0], '2')
        self.assertIn('Chamado', self.app._colab_enviar.call_args.args[1])
        self.assertIn('já participa', self.iniciar())
        self.assertEqual(len(self.app._abas), 2)

    def test_chamado_nao_delega_nao_propoe_e_nao_comanda(self):
        self.app.auto_colab(True)
        s = json.loads(self.iniciar())
        self.assertIn('não pode delegar', self.app.fio_chamar('2', 'auto', 'colab', json.dumps(self.dados())))
        with self.assertRaisesRegex(ValueError, 'somente o Chamador'):
            colab.atualizar(colab.criar('1', '2', 'Site'), '2', proposta())
        self.assertIn('não comanda', self.app.fio_chamar('2', '1', 'enviar', 'mude tudo'))
        f = self.app.fios()[0]
        self.assertIn('Chamado: obedeça exatamente', colab.contexto('2', f, s))
        self.assertNotIn('AUTO-COLAB LIGADO', self.app._na_aba('2', self.app._fios_contexto)())

    def test_plano_invalido_ou_mesmo_modelo_nao_cria_aba(self):
        self.app.auto_colab(True)
        for alteracao in ('modelo', 'sobreposicao', 'fora', 'membro'):
            d = self.dados()
            if alteracao == 'modelo': d['quem'] = 'codex'
            if alteracao == 'sobreposicao': d['tarefas'][1]['arquivos'] = ['API.PY']
            if alteracao == 'fora': d['tarefas'][1]['arquivos'] = ['../fora.py']
            if alteracao == 'membro': d['tarefas'][1]['aba'] = '3'
            with self.subTest(alteracao=alteracao):
                self.assertTrue(self.app.fio_chamar('1', 'auto', 'colab', json.dumps(d)).startswith('ERRO:'))
                self.assertEqual(len(self.app._abas), 1)
                self.assertEqual(self.app.fios(), [])

    def test_desligar_preserva_entregas_e_integracao(self):
        self.app.auto_colab(True)
        self.iniciar()
        self.app.auto_colab(False)
        self.app.colab_atualizar('1', '2', {'acao': 'concluir_tarefa', 'evidencia': 'API testada'})
        self.app._abas['1'].ajudante_ativo = None
        s = self.app.colab_atualizar('2', '1', {'acao': 'concluir_tarefa', 'evidencia': 'Interface testada'})
        self.assertEqual(s['fase'], 'integracao')
        self.assertEqual(self.app._colab_enviar.call_args.args[0], '1')
        with self.assertRaises(ValueError):
            self.app.colab_atualizar('2', '1', {'acao': 'finalizar', 'evidencia': 'teste'})
        s = self.app.colab_atualizar('1', '2', {'acao': 'finalizar', 'evidencia': 'Integração testada'})
        self.assertEqual(s['fase'], 'concluido')

    def test_ferramenta_kani_usa_o_mesmo_canal(self):
        import kani_modo
        self.app.auto_colab(True)
        self.app._abas['1'].quem = 'kani'
        with patch.object(fios, 'APP', self.app):
            resposta = kani_modo._executar('chat_colab', {'para': 'auto', 'dados': self.dados()}, self.temp.name)
        self.assertEqual(json.loads(resposta)['fase'], 'execucao')
        self.assertEqual(self.app._abas['2'].quem, 'claude')

    def test_falha_ao_disparar_mantem_plano_retomavel(self):
        self.app.auto_colab(True)
        self.app._colab_enviar.side_effect = ValueError('modelo sem sessão')
        self.assertTrue(self.iniciar().startswith('ERRO:'))
        f = self.app.fios()[0]
        s = self.app.colab_consultar(f['id'])
        self.assertEqual(s['fase'], 'planejamento')
        self.app._colab_enviar.side_effect = None
        s = self.app.colab_atualizar('1', '2', {'acao': 'executar', 'revisao': 1})
        self.assertEqual(s['fase'], 'execucao')

if __name__ == '__main__':
    unittest.main()
