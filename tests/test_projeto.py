"""Projeto ativo e edição em pastas sintéticas do D, sem contas ou commits."""
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import projeto
import kanicode


class ProjetoTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir="D:/kanivete_testes", prefix="painel_projeto_")
        self.addCleanup(tmp.cleanup)
        self.pasta = Path(tmp.name)
        self.a = self.pasta / "primeiro"
        self.b = self.pasta / "segundo"
        for p in (self.a, self.b):
            p.mkdir()
            (p / "kanivete.json").write_text('{}', encoding='utf-8')
            (p / "codigo.py").write_bytes(b'print(1)\r\n')
        self.arquivo = self.a / "codigo.py"

    def test_gravar_conserva_texto_e_recusa_conflito(self):
        r = projeto.ler(str(self.a), 'codigo.py')
        dados = dict(raiz=str(self.a), versao=r['versao'], texto='print(2)\r\n')
        self.assertTrue(projeto.salvar(str(self.a), 'codigo.py', dados)['ok'])
        self.assertEqual(self.arquivo.read_bytes(), b'print(2)\r\n')
        self.assertTrue(projeto.salvar(str(self.a), 'codigo.py', dados)['conflito'])
        self.assertEqual(self.arquivo.read_bytes(), b'print(2)\r\n')
        dados['raiz'] = str(self.b)
        self.assertFalse(projeto.salvar(str(self.a), 'codigo.py', dados)['ok'])

    def test_recusa_fora_da_raiz_binario_codificacao_e_corte(self):
        for nome, conteudo in [('bin.dat', b'abc\0'), ('latin.txt', b'caf\xe9'), ('grande.txt', b'x' * (projeto.MAX_LER + 1))]:
            (self.a / nome).write_bytes(conteudo)
            leitura = projeto.ler(str(self.a), nome)
            self.assertFalse(leitura.get('editavel', False))
            self.assertFalse(projeto.salvar(str(self.a), nome, dict(raiz=str(self.a), versao=leitura.get('versao'), texto='novo'))['ok'])
        with self.assertRaises(ValueError):
            projeto.salvar(str(self.a), '../segundo/codigo.py', dict(raiz=str(self.a), texto='inválido'))

    def test_reconhece_workdir_arquivos_comando_e_raiz_do_plugin(self):
        (self.b / 'ui').mkdir()
        with patch.object(projeto, 'PASTA_SAIDAS', ''):
            for entrada in [dict(workdir=str(self.b)), dict(file_path=str(self.b / 'ui' / 'novo.js')),
                            dict(changes=[dict(path=str(self.b / 'codigo.py'))]),
                            dict(command='Set-Location -LiteralPath "' + str(self.b) + '"')]:
                self.assertEqual(projeto.pasta_observada(entrada, str(self.a)), str(self.b))
        with patch.object(projeto, 'PASTA_SAIDAS', ''):
            entrada = dict(code='await tools.exec_command({workdir: "' + str(self.b).replace('\\', '\\\\') + '"})')
            self.assertEqual(projeto.pasta_observada(entrada, str(self.a)), str(self.b))
        self.assertIsNone(projeto.pasta_observada(dict(workdir='D:/kanivete_testes'), str(self.a)))
        self.assertIsNone(projeto.pasta_observada(dict(path='https://exemplo/arquivo'), str(self.a)))

    def test_ponte_segue_operacao_por_aba_e_recusa_salvar_em_outro_projeto(self):
        aba = SimpleNamespace(id='1')
        app = SimpleNamespace(_ctx=lambda: aba, _pasta=lambda: str(self.a), _pend={},
                              _janela=Mock(), janela_diagnostico=Mock())
        with patch.object(projeto, 'PASTA_SAIDAS', ''), patch.dict('sys.modules', movel=Mock()):
            kanicode.App._para_janela(app, dict(t='ferr', entrada=dict(workdir=str(self.b))))
        contexto = kanicode.App.projeto(app, 'contexto')
        self.assertEqual(contexto['raiz'], str(self.b))
        self.assertIn('codigo.py', [i['rel'] for i in kanicode.App.projeto(app, 'arvore')['itens']])
        dados = dict(contexto, texto='print(3)', versao=projeto.ler(str(self.a), 'codigo.py')['versao'])
        dados['raiz'] = str(self.a)
        self.assertFalse(kanicode.App.projeto(app, 'salvar', 'codigo.py', dados)['ok'])
        self.assertEqual(self.arquivo.read_bytes(), b'print(1)\r\n')
        aba = SimpleNamespace(id='2')
        self.assertEqual(kanicode.App.projeto(app, 'contexto')['raiz'], str(self.a))

    def test_sem_git_acompanha_modificado_novo_e_apagado(self):
        monitor = projeto.Acompanhamento(str(self.a))
        self.arquivo.write_text('print(2)\n', encoding='utf-8')
        novo = self.a / 'novo.py'
        novo.write_text('novo\n', encoding='utf-8')
        self.assertEqual({i['arq']: i['st'] for i in monitor.alteracoes()['itens']}, {'codigo.py': 'M', 'novo.py': '?'})
        self.assertIn('+print(2)', monitor.diff('codigo.py')['texto'])
        self.arquivo.unlink()  # somente o arquivo sintético desta fixture no D
        self.assertEqual({i['arq']: i['st'] for i in monitor.alteracoes()['itens']}['codigo.py'], 'D')

    def test_git_de_pasta_pai_fica_restrito_ao_plugin_sem_commits(self):
        git = lambda *a: subprocess.run(['git', '-C', str(self.pasta), *a], capture_output=True, check=True)
        git('init', '-q')
        git('add', '.')
        self.arquivo.write_text('print(4)\n', encoding='utf-8')
        self.assertEqual(projeto.raiz(str(self.a)), str(self.a))
        itens = projeto.alteracoes(str(self.a))['itens']
        self.assertTrue(any(i['arq'] == 'codigo.py' for i in itens))
        self.assertFalse(any('segundo' in i['arq'] for i in itens))
        self.assertIn('+print(4)', projeto.diff(str(self.a), 'codigo.py')['texto'])


if __name__ == '__main__':
    unittest.main()

