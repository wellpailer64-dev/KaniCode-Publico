"""KaniCode.exe como Python (lancador.py) e caminhos de fora (locais.py), sem montar o exe."""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import locais


def _rodar(*args):
    return subprocess.run([sys.executable, str(RAIZ / "lancador.py"), *args], capture_output=True, text=True,
                          encoding="utf-8", timeout=60, cwd=str(RAIZ))


class LancadorTest(unittest.TestCase):
    def test_c_m_e_script(self):
        self.assertEqual(_rodar("-u", "-X", "utf8", "-c", "import sys; print('oi', sys.argv[1:])", "a").stdout.strip(), "oi ['a']")
        with tempfile.TemporaryDirectory(dir="D:/kanivete_testes") as t:
            s = Path(t) / "s.py"
            s.write_text("import sys; print(__name__, sys.argv[1:]); sys.exit(3)", encoding="utf-8")
            r = _rodar(str(s), "x", "y")
            self.assertEqual(r.stdout.strip(), "__main__ ['x', 'y']")
            self.assertEqual(r.returncode, 3)

    def test_locais(self):
        self.assertTrue(locais.PLUGINS.lower().endswith(os.path.join("kanivete", "plugins")))
        self.assertTrue(locais.KANIVETE_EXE.endswith("CaniveteDoPailer.exe"))
        self.assertEqual(locais.plugin("pandalab", "panda.py"), os.path.join(locais.PLUGINS, "pandalab", "panda.py"))


if __name__ == "__main__":
    unittest.main()
