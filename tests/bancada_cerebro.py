"""Bancada publica com dados sinteticos; nao consulta o cerebro particular do usuario.

Execute: py -3.13 tests/bancada_cerebro.py
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_cerebro_motor

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_cerebro_motor.MotorTest)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if resultado.wasSuccessful() else 1)
