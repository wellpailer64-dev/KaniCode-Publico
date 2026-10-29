"""Plugin Kanivete do KaniCode: o KaniCode (software independente) enxerga e comanda o app KANIVETE.

  py -3.13 kanivete.py estado [--porta 9222]       app aberto? portas do modo agente, páginas, versão instalada
  py -3.13 kanivete.py apis [--porta 9222]         APIs que a página expõe agora (VKN, KNV, SDK, VE3DAPI, KE_API...)
  py -3.13 kanivete.py js "<código>" [--porta P]   roda JS na janela principal (aceita async) e devolve o valor
  py -3.13 kanivete.py abrir                       abre o KANIVETE em modo agente SÓ se não estiver aberto (nunca fecha)
  py -3.13 kanivete.py mapa <termo>                procura no mapa geral do KANIVETE (ferramentas, arquivos, API, testes)
  py -3.13 kanivete.py guia                        onde estão os guias (CLAUDE.md, MAPA.md, modo agente...)

Portas: 9222 = app do Pailer (ele trabalha nele ao vivo: nada de clique simulado; recarregar só com o ok dele);
9333 = app de teste (APPDATA/TEMP em D:/kanivete_testes). Sem o KANIVETE aberto, `estado` sai com código 1.
"""
import argparse, json, os, subprocess, sys, time, urllib.request

AQUI = os.path.dirname(os.path.realpath(__file__))
# <DESENVOLVIMENTOS EM PYTHON>/PLUGGINS KANIVETE/kanicode/plugins/kanivete → <DESENVOLVIMENTOS EM PYTHON>/CANIVETE DO PAILER
sys.path.insert(0, os.path.dirname(os.path.dirname(AQUI)))   # locais.py do KaniCode
import locais
CODIGO = locais.KANIVETE
EXE = os.path.join(CODIGO, "dist", "CaniveteDoPailer", "CaniveteDoPailer.exe")
APIS = ["VKN", "KNV", "SDK", "SKN", "VE3DAPI", "LUX_API", "KE_API", "VEFILA_API", "VEMIX_API", "VEMO_API", "VEPS_API", "ATA_API",
        "KANI_TELA", "VE"]
GUIAS = [("Notas para o agente (comece aqui)", "CLAUDE.md"), ("Mapa geral: ferramentas → arquivos, API, testes", "Instructions/MAPA.md"),
         ("Modo agente (CDP, segurança)", "Instructions/modo-agente.md"), ("Editar vídeo pelo app", "Instructions/agente/guia-edicao.md"),
         ("Arte no Photo (KNV)", "Instructions/agente/design-photo-kanivete.md"), ("Vetor (VKN)", "Instructions/vetor-kanivete.md"),
         ("Slider (SDK)", "Instructions/slider-kanivete.md"), ("Kanivete Encoder", "Instructions/agente/mapa-kanivete-encoder.md")]


def _vivo(porta):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/json/version", timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _paginas(porta):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/json", timeout=2) as r:
            return [p for p in json.loads(r.read()) if p.get("type") == "page"]
    except Exception:
        return []


def _versao():
    try:
        return open(os.path.join(os.path.dirname(EXE), "version.txt"), encoding="utf-8").read().strip()
    except OSError:
        return None


def estado(porta=None):
    portas = [porta] if porta else [9222, 9333]
    saida = {"instalado": os.path.isfile(EXE), "versao": _versao(), "codigo": CODIGO, "portas": {}}
    for p in portas:
        v = _vivo(p)
        if v:
            saida["portas"][p] = {"uso": "app do Pailer" if p == 9222 else "app de teste" if p == 9333 else "outro",
                                  "paginas": [x.get("title") or x.get("url") for x in _paginas(p)][:6]}
    saida["aberto"] = bool(saida["portas"])
    return saida


def js(codigo, porta=9222):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{porta}")
        try:
            pgs = [p for c in nav.contexts for p in c.pages if "index.html" in p.url] or [p for c in nav.contexts for p in c.pages]
            if not pgs:
                raise SystemExit("não achei a janela principal do KANIVETE")
            expr = codigo if codigo.lstrip().startswith(("(", "async", "function")) else f"async () => ({codigo})"
            return pgs[0].evaluate(expr)
        finally:
            nav.close()   # só a conexão: o app continua aberto


def apis(porta=9222):
    return js("() => Object.fromEntries(" + json.dumps(APIS) + ".map(n => [n, (0, eval)('typeof ' + n) !== 'undefined']))", porta)


def abrir():
    if _vivo(9222):
        return "o KANIVETE já está aberto (não abri outro)"
    if not os.path.isfile(EXE):
        raise SystemExit(f"não achei o KANIVETE instalado em {EXE}")
    subprocess.Popen([EXE, "--agente"], cwd=os.path.dirname(EXE), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(60):
        time.sleep(1)
        if _vivo(9222):
            return "abri o KANIVETE (modo agente, porta 9222)"
    raise SystemExit("o KANIVETE não respondeu depois de 1 minuto")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["estado", "apis", "js", "abrir", "mapa", "guia"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--porta", type=int)
    ap.add_argument("--curto", action="store_true")
    a = ap.parse_args()
    if a.cmd == "estado":
        e = estado(a.porta)
        if "--curto" in sys.argv:   # uma linha (Configurações › Plugins › Verificar conexão)
            print(("aberto · " + " · ".join(f"{p} {v['uso']}" for p, v in e["portas"].items()) if e["aberto"] else "fechado")
                  + (f" · v{e['versao']}" if e["versao"] else ""))
        else:
            print(json.dumps(e, ensure_ascii=False, indent=1))
        return 0 if e["aberto"] else 1
    if a.cmd == "apis":
        print(json.dumps(apis(a.porta or 9222), ensure_ascii=False)); return 0
    if a.cmd == "js":
        if not a.arg:
            print('uso: kanivete.py js "<código>" [--porta 9222]'); return 2
        r = js(a.arg, a.porta or 9222)
        print(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)); return 0
    if a.cmd == "abrir":
        print(abrir()); return 0
    if a.cmd == "mapa":
        return subprocess.call([sys.executable, os.path.join(CODIGO, "tools", "mapa_geral.py"), "--busca", a.arg or ""], cwd=CODIGO)
    for nome, rel in GUIAS:
        print(f"{nome}: {os.path.join(CODIGO, rel)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
