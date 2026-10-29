"""Antes de abrir o KaniCode ao público: o que está no git (e no histórico) não pode ter credencial nem dado pessoal.

Só lê o repositório (git ls-files / git log); não abre perfis, cérebro nem contas reais.
"""
import os, re, subprocess, unittest

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SEGREDO = re.compile(r"(sk-ant-[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9]{32,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}"
                     r"|xox[bp]-[A-Za-z0-9-]{10,}|GOCSPX-[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY|[a-z0-9]{20}\.supabase\.co)")
# Fake usado nos testes de limpeza: não é credencial.
SIMULADOS = ("chave-real",)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@(gmail|googlemail|hotmail|outlook|yahoo)\.com")
ARQ_PROIBIDOS = re.compile(r"(^|/)(client_secret[^/]*\.json|\.env|token[^/]*\.json|credenciais[^/]*|_credenciais\.py|contas/.*|"
                           r"memory/.*|MEMORY\.md|.*\.sqlite3?|.*\.db)$", re.I)


def git(*a):
    return subprocess.run(["git", *a], cwd=AQUI, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def rastreados():
    return [f for f in git("ls-files").splitlines() if f]


def texto(f):
    try:
        with open(os.path.join(AQUI, f), "rb") as h:
            b = h.read()
    except OSError:
        return ""
    return "" if b"\0" in b[:4096] else b.decode("utf-8", "replace").replace("\r\n", "\n")


class Publicacao(unittest.TestCase):
    def test_sem_credencial_na_arvore(self):
        achados = [f for f in rastreados() if SEGREDO.search(texto(f))]
        self.assertEqual(achados, [])

    def test_sem_credencial_no_historico(self):
        adicionadas = [l for l in git("log", "--all", "-p", "--format=", "--no-color", "-U0").splitlines() if l.startswith("+")]
        achados = [l[:40] for l in adicionadas if SEGREDO.search(l)]
        self.assertEqual(achados, [])

    def test_sem_arquivo_sensivel_no_historico(self):
        todos = set(git("log", "--all", "--name-only", "--format=").split("\n")) | set(rastreados())
        self.assertEqual(sorted(f for f in todos if f and ARQ_PROIBIDOS.search(f)), [])

    def test_sem_email_pessoal(self):
        achados = [f for f in rastreados() if EMAIL.search(texto(f).replace("'@gmail.com'", ""))]
        self.assertEqual(achados, [])

    def test_gitignore_cobre_segredos(self):
        ign = texto(".gitignore")
        for p in ("client_secret", ".env"):
            self.assertIn(p, ign)

    def test_build_so_empacota_rastreados(self):
        # --others incluiria no zip arquivo local não rastreado (ex.: anotação pessoal na pasta)
        cod = texto("construir.py")
        m = re.search(r'def arquivos_app\(\):(.*?)\n\n', cod, re.S)
        self.assertIsNotNone(m)
        self.assertNotIn("--others", m.group(1))

    def test_filtro_simulado_nao_confunde(self):
        for s in SIMULADOS:
            self.assertIsNone(SEGREDO.search(s))


if __name__ == "__main__":
    unittest.main()
