"""Onde ficam as coisas FORA do KaniCode: plugins do PC e o KANIVETE (código e instalado).

Antes cada módulo calculava pelo lugar do próprio arquivo (".." / "pandalab", três pastas acima + "CANIVETE DO PAILER");
no KaniCode.exe o código mora em <programa>/app e essas contas erram. Aqui fica a regra única:
- PLUGINS: KANICODE_PLUGINS ou <disco>/Kanivete/Plugins (a junção para PLUGGINS KANIVETE).
- KANIVETE: KANIVETE_CODIGO ou a pasta do código do KANIVETE (ao lado da do KaniCode, ou o caminho conhecido do PC).
"""
import os
from pathlib import Path

_AQUI = os.path.dirname(os.path.realpath(__file__))
_DISCO = os.path.splitdrive(_AQUI)[0] or "D:"
PLUGINS = os.environ.get("KANICODE_PLUGINS") or os.path.join(_DISCO + os.sep, "Kanivete", "Plugins")


def _kanivete():
    for c in (os.environ.get("KANIVETE_CODIGO"),
              os.path.join(os.path.dirname(os.path.dirname(_AQUI)), "CANIVETE DO PAILER"),   # código ao lado (pasta de desenvolvimento)
              os.path.join(_DISCO + os.sep, "01 - ALL IN CLOUD - HD PAILER", "DESENVOLVIMENTOS EM PYTHON", "CANIVETE DO PAILER")):
        if c and os.path.isdir(c):
            return c
    return os.path.join(_DISCO + os.sep, "01 - ALL IN CLOUD - HD PAILER", "DESENVOLVIMENTOS EM PYTHON", "CANIVETE DO PAILER")


KANIVETE = _kanivete()
KANIVETE_EXE = os.path.join(KANIVETE, "dist", "CaniveteDoPailer", "CaniveteDoPailer.exe")
KANIVETE_MODELOS = os.path.join(KANIVETE, "dist", "CaniveteDoPailer", "modelos_ia")


def plugin(nome, *partes):
    """caminho dentro de um plugin do PC: plugin('pandalab', 'panda.py')"""
    return os.path.join(PLUGINS, nome, *partes)


def plugin_p(nome, *partes):
    return Path(plugin(nome, *partes))
