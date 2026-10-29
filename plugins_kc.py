"""Plugins do KaniCode: pastas com um `kanicode.json` (nome, cor, descrição, comando de linha e verificação).

Onde procura: `<kanicode>/plugins/*` e as pastas de plugin do PC (`D:/Kanivete/Plugins/*`, as mesmas do KANIVETE; um plugin
pode servir aos dois, com `kanivete.json` e `kanicode.json` lado a lado). Ligado/desligado fica em `<dados>/plugins.json`.
Plugin ligado entra numa linha das instruções do Claude (`linha_prompt`), com o comando para usar sem o KANIVETE, e cada
plugin vira um grupo no lobo Plugins do cérebro (perfil_cerebro._fonte_plugins: para que serve, comandos, quem chama).

kanicode.json:
  {"nome": "Pandalab", "sigla": "Pl", "cor": "#7AD0FF", "descricao": "...", "icone": "icone.png",
   "cli": "panda.py", "serve": "para que serve (texto longo)", "guia": "caminho do guia",
   "comandos": [{"cmd": "demandas --status abertas", "faz": "lista os cards"}],   # texto simples também vale
   "chamado_por": ["quem usa: Claude, ferramenta da Kani X, módulo Y..."],
   "verificar": ["quem"], "prompt": true}   # prompt false: já está nas instruções fixas; roda `py -3.13 <cli> quem`; código 0 = conectado (a saída vira o detalhe)
"""
import json, os, subprocess, sys
from pathlib import Path

from dados_app import pasta_dados

AQUI = Path(os.path.abspath(__file__)).parent
_CURTO = Path(AQUI.anchor) / "Kanivete" / "Plugins" / "kanicode"   # o caminho curto da junção, sem espaços, quando é a mesma pasta
if _CURTO.is_dir() and _CURTO.samefile(AQUI):
    AQUI = _CURTO
PASTAS = [AQUI / "plugins", Path(AQUI.anchor) / "Kanivete" / "Plugins"]
MANIFESTO = "kanicode.json"


def _estado_arq():
    return pasta_dados() / "plugins.json"


def _estado():
    try:
        return json.loads(_estado_arq().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gravar_estado(e):
    p = _estado_arq()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def _python():
    exe = sys.executable
    return exe.replace("pythonw.exe", "python.exe")


def listar():
    """plugins encontrados (o mesmo id em duas pastas: vale a primeira)"""
    est, vistos, saida = _estado(), set(), []
    for base in PASTAS:
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            m = d / MANIFESTO
            if d.name in vistos or not m.is_file():
                continue
            try:
                info = json.loads(m.read_text(encoding="utf-8"))
            except Exception as e:
                info = {"nome": d.name, "erro": f"kanicode.json ilegível: {e}"}
            vistos.add(d.name)
            cli = info.get("cli")
            cmds = [c if isinstance(c, dict) else {"cmd": str(c), "faz": ""} for c in info.get("comandos") or []]
            saida.append({
                "id": d.name, "nome": info.get("nome") or d.name, "sigla": info.get("sigla") or d.name[:2].title(),
                "cor": info.get("cor") or "#B6F23A", "descricao": info.get("descricao") or "", "pasta": str(d),
                "icone": str(d / info["icone"]) if info.get("icone") and (d / info["icone"]).is_file() else "",
                "cli": str(d / cli) if cli else "", "comandos": cmds, "serve": info.get("serve") or info.get("descricao") or "",
                "chamado_por": info.get("chamado_por") or [], "guia": info.get("guia") or "",
                "verificar": info.get("verificar") or [], "erro": info.get("erro", ""),
                "ligado": est.get(d.name, {}).get("ligado", True),
                "tambem_kanivete": (d / "kanivete.json").is_file(), "prompt": info.get("prompt", True),
            })
    return saida


def logo(pid):
    """o ícone do plugin como data URL (a janela não lê arquivos fora da pasta ui)"""
    import base64, mimetypes
    p = achar(pid)
    if not p["icone"]:
        return ""
    tipo = mimetypes.guess_type(p["icone"])[0] or "image/png"
    return f"data:{tipo};base64," + base64.b64encode(Path(p["icone"]).read_bytes()).decode()


def achar(pid):
    for p in listar():
        if p["id"] == pid:
            return p
    raise ValueError(f"plugin não encontrado: {pid}")


def ligar(pid, ligado):
    achar(pid)
    e = _estado()
    e.setdefault(pid, {})["ligado"] = bool(ligado)
    _gravar_estado(e)
    return achar(pid)


def verificar(pid, prazo=20):
    """roda a verificação do plugin (ex.: `panda.py quem`): {conectado, detalhe}"""
    p = achar(pid)
    if not p["cli"] or not p["verificar"]:
        return {"id": pid, "conectado": None, "detalhe": "sem verificação"}
    try:
        r = subprocess.run([_python(), p["cli"], *p["verificar"]], cwd=p["pasta"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=prazo,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return {"id": pid, "conectado": False, "detalhe": "não respondeu a tempo"}
    except Exception as e:
        return {"id": pid, "conectado": False, "detalhe": str(e)}
    txt = (r.stdout or r.stderr or "").strip().splitlines()
    detalhe = txt[-1][:200] if txt else ""
    try:   # panda.py quem devolve JSON: mostra só o nome
        j = json.loads(detalhe)
        detalhe = " · ".join(str(j[k]) for k in ("nome", "email", "modo") if j.get(k))
    except Exception:
        pass
    return {"id": pid, "conectado": r.returncode == 0, "detalhe": detalhe}


def linha_prompt():
    """uma linha por plugin ligado, para as instruções do Claude (curta: entra em todo passo)"""
    partes = []
    for p in listar():
        if p["ligado"] and p["cli"] and p["prompt"] and not p["erro"]:
            cli = p["cli"].replace("\\", "/")
            ex = "; ".join(c["cmd"] for c in p["comandos"][:4])
            partes.append(f"{p['nome']}: `py -3.13 \"{cli}\" ...`" + (f" ({ex})" if ex else ""))
    return ("\nPlugins do KaniCode (Configurações › Plugins; guia de cada um no cérebro, lobo Plugins): " + " | ".join(partes)) if partes else ""


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for p in listar():
        print(("●" if p["ligado"] else "○"), p["id"], "-", p["nome"], "|", p["cli"])
    print(linha_prompt())
