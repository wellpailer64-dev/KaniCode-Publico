"""Painel Projeto: arquivos, alterações ao vivo e edição com conferência de versão.

Caminhos relativos à raiz, conferidos para não sair dela.
"""
import os, subprocess
import hashlib
import re
import threading
import time

_GRAVAR_TRAVA = threading.Lock()
PASTA_SAIDAS = os.path.normcase(os.path.realpath("D:/kanivete_testes"))

IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache", ".idea", ".vs"}
MAX_LER = 400_000
_SEM_JANELA = 0x08000000   # CREATE_NO_WINDOW


def _git(raiz, *args, timeout=8):
    r = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=raiz, capture_output=True, timeout=timeout,
                       creationflags=_SEM_JANELA)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def raiz(pasta):
    """Projeto mais próximo pelos marcadores locais; Git e pasta são alternativas."""
    atual = os.path.realpath(pasta)
    while True:
        if any(os.path.isfile(os.path.join(atual, n)) for n in ("kanivete.json", "pyproject.toml", "package.json")) or os.path.exists(os.path.join(atual, ".git")):
            return atual
        pai = os.path.dirname(atual)
        if pai == atual:
            break
        atual = pai
    try:
        t = _git(pasta, "rev-parse", "--show-toplevel", timeout=4)
        if t and t.strip():
            return os.path.normpath(t.strip())
    except Exception:
        pass
    return os.path.normpath(pasta)


def _dentro(base, rel):
    alvo = os.path.realpath(os.path.join(base, rel or ""))
    b = os.path.realpath(base)
    if os.path.normcase(alvo) != os.path.normcase(b) and not os.path.normcase(alvo).startswith(os.path.normcase(b) + os.sep):
        raise ValueError("fora do projeto")
    return alvo


def _status(base):
    """{caminho relativo com /: letra} — M alterado, A novo no índice, ? novo, D apagado, R renomeado"""
    saida = _git(base, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".")
    prefixo = (_git(base, "rev-parse", "--show-prefix") or "").strip()
    if saida is None:
        return None
    st, partes, i = {}, saida.split("\0"), 0
    while i < len(partes):
        p = partes[i]
        i += 1
        if len(p) < 4:
            continue
        x, y, arq = p[0], p[1], p[3:]
        if x == "R" or x == "C":
            i += 1   # o nome antigo vem depois
        letra = "?" if x == "?" else "D" if "D" in (x, y) else "A" if x == "A" else "R" if x == "R" else "M"
        if prefixo and not arq.startswith(prefixo):
            continue
        st[arq[len(prefixo):]] = letra
    return st


def arvore(pasta, sub=""):
    """itens de uma pasta (pastas primeiro), com a marca do git e se há alteração dentro (pastas)"""
    base = raiz(pasta)
    alvo = _dentro(base, sub)
    st = _status(base) or {}
    pre = (sub.replace("\\", "/").strip("/") + "/") if sub else ""
    itens = []
    try:
        with os.scandir(alvo) as it:
            for e in it:
                if e.name in IGNORAR:
                    continue
                rel = pre + e.name
                d = e.is_dir(follow_symlinks=False)
                marca = st.get(rel, "")
                if d and not marca:
                    marca = "•" if any(k.startswith(rel + "/") for k in st) else ""
                itens.append({"n": e.name, "rel": rel, "d": d, "st": marca})
    except OSError as ex:
        return {"ok": False, "erro": str(ex)}
    itens.sort(key=lambda x: (not x["d"], x["n"].lower()))
    return {"ok": True, "raiz": base, "nome": os.path.basename(base) or base, "sub": pre, "itens": itens}


def alteracoes(pasta):
    """arquivos alterados em relação ao último commit, com +/− linhas, ramo e quantos commits à frente"""
    base = raiz(pasta)
    st = _status(base)
    if st is None:
        return {"ok": False, "erro": "Esta pasta não é um repositório git.", "raiz": base}
    num = {}
    for linha in (_git(base, "diff", "HEAD", "--relative", "--numstat", "--", ".") or "").splitlines():
        p = linha.split("\t")
        if len(p) == 3:
            num[p[2]] = (int(p[0]) if p[0].isdigit() else 0, int(p[1]) if p[1].isdigit() else 0)
    itens = []
    for arq, letra in sorted(st.items()):
        mais, menos = num.get(arq, (0, 0))
        if letra == "?" or (letra == "A" and not _git(base, "rev-parse", "--verify", "HEAD")):
            try:
                with open(os.path.join(base, arq), "rb") as f:
                    dados = f.read(MAX_LER)
                mais = 0 if b"\0" in dados else dados.count(b"\n") + (1 if dados and not dados.endswith(b"\n") else 0)
            except OSError:
                pass
        itens.append({"arq": arq, "st": letra, "mais": mais, "menos": menos})
    ramo = (_git(base, "branch", "--show-current") or "").strip() or "(sem ramo)"
    frente = (_git(base, "rev-list", "--count", "@{u}..HEAD") or "").strip()
    return {"ok": True, "raiz": base, "ramo": ramo, "frente": int(frente) if frente.isdigit() else None, "itens": itens,
            "mais": sum(i["mais"] for i in itens), "menos": sum(i["menos"] for i in itens)}


def diff(pasta, arq):
    """diferença unificada de um arquivo (novo = tudo entra)"""
    base = raiz(pasta)
    caminho = _dentro(base, arq)
    st = (_status(base) or {}).get(arq.replace("\\", "/"), "")
    if st == "?" or (st == "A" and not _git(base, "rev-parse", "--verify", "HEAD")):
        texto = ler(pasta, arq)
        if not texto.get("ok") or texto.get("binario"):
            return {"ok": True, "binario": True, "texto": ""}
        linhas = texto["texto"].splitlines()
        return {"ok": True, "texto": f"@@ -0,0 +1,{len(linhas)} @@\n" + "\n".join("+" + l for l in linhas)}
    t = _git(base, "diff", "HEAD", "--no-color", "-U3", "--", arq)
    if t is None:
        return {"ok": False, "erro": "git diff falhou"}
    if "Binary files" in t[:400] and "@@" not in t:
        return {"ok": True, "binario": True, "texto": ""}
    corpo = t[t.find("@@"):] if "@@" in t else t
    return {"ok": True, "texto": corpo[:MAX_LER], "cortado": len(corpo) > MAX_LER, "existe": os.path.exists(caminho)}


def ler(pasta, arq):
    base = raiz(pasta)
    caminho = _dentro(base, arq)
    try:
        tam = os.path.getsize(caminho)
        with open(caminho, "rb") as f:
            dados = f.read(MAX_LER)
    except OSError as ex:
        return {"ok": False, "erro": str(ex)}
    if b"\0" in dados:
        return {"ok": True, "binario": True, "tam": tam, "texto": ""}
    try:
        texto = dados.decode("utf-8")
        editavel = tam <= MAX_LER
    except UnicodeDecodeError:
        texto, editavel = dados.decode("utf-8", "replace"), False
    return {"ok": True, "texto": texto, "tam": tam, "cortado": tam > MAX_LER,
            "caminho": caminho, "editavel": editavel, "versao": hashlib.sha256(dados).hexdigest()}



def salvar(pasta, arq, dados):
    """Só grava texto completo UTF-8 se o arquivo ainda tiver a versão lida."""
    base = raiz(pasta)
    if os.path.normcase(os.path.realpath(dados.get("raiz", ""))) != os.path.normcase(os.path.realpath(base)):
        return {"ok": False, "erro": "O projeto mudou. Volte ao projeto de origem para salvar."}
    caminho = _dentro(base, arq)
    texto = dados.get("texto")
    if not isinstance(texto, str) or len(texto.encode("utf-8")) > MAX_LER:
        return {"ok": False, "erro": "Texto inválido ou grande demais para este editor."}
    with _GRAVAR_TRAVA:
        atual = ler(base, arq)
        if not atual.get("editavel") or atual.get("versao") != dados.get("versao"):
            return {"ok": False, "conflito": True, "erro": "O arquivo mudou no disco. Seu texto foi mantido; copie-o antes de recarregar."}
        with open(caminho, "r+b") as f:
            original = f.read()
            if hashlib.sha256(original).hexdigest() != dados.get("versao"):
                return {"ok": False, "conflito": True, "erro": "O arquivo mudou no disco. Seu texto foi mantido."}
            f.seek(0)
            f.write(texto.encode("utf-8"))
            f.truncate()
    return ler(base, arq)


def pasta_observada(entrada, pasta):
    """Reconhece caminhos explícitos das ferramentas, sem varrer disco ou interpretar a resposta."""
    if not isinstance(entrada, dict):
        return None
    candidatos = []
    for c in entrada.get("changes") or []:
        if isinstance(c, dict):
            candidatos.append((c.get("path"), True))
    for k in ("file_path", "notebook_path", "path", "caminho"):
        candidatos.append((entrada.get(k), True))
    for k in ("workdir", "cwd", "directory", "pasta"):
        candidatos.append((entrada.get(k), False))
    cmd = str(entrada.get("command") or entrada.get("cmd") or "")
    codigo = str(entrada.get("code") or "")
    try:
        import json
        objeto = json.loads(codigo)
        if isinstance(objeto, dict):
            encontrada = pasta_observada(objeto, pasta)
            if encontrada:
                return encontrada
    except (ValueError, TypeError):
        pass
    for m in re.finditer(r"[\"']?(?:workdir|cwd)[\"']?\s*:\s*[\"']([^\"'\r\n]+)[\"']", codigo):
        candidatos.append((m[1].replace("\\\\", "\\"), False))
    cmd += "\n" + codigo
    for m in re.finditer(r"(?:\b(?:cd|pushd|Set-Location|Push-Location)\s+(?:-LiteralPath\s+|-Path\s+)?)(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|]+))", cmd, re.I):
        candidatos.append((next(v for v in m.groups() if v), False))
    for m in re.finditer(r"[\"']([a-z]:[\\/][^\"'\r\n]+)[\"']", cmd, re.I):
        if not m[1].lower().endswith((".exe", ".dll", ".bat", ".cmd")):
            candidatos.append((m[1], not os.path.isdir(m[1])))
    for nome, arquivo in candidatos:
        if not isinstance(nome, str) or not nome or "://" in nome:
            continue
        alvo = os.path.realpath(os.path.join(pasta, nome))
        if arquivo:
            alvo = os.path.dirname(alvo)
        if not os.path.isdir(alvo):
            continue
        # Saídas e caches dos testes não são o projeto em edição.
        if PASTA_SAIDAS and (os.path.normcase(alvo) == PASTA_SAIDAS or os.path.normcase(alvo).startswith(PASTA_SAIDAS + os.sep)):
            continue
        if os.path.dirname(alvo) == alvo:
            continue
        base = raiz(alvo)
        origem = os.path.realpath(pasta)
        if base == alvo and (alvo == origem or alvo.startswith(origem + os.sep)):
            return raiz(origem)
        return base
    return None


class Acompanhamento:
    """Referência em memória para pastas sem Git; nunca grava no projeto."""
    def __init__(self, pasta):
        self.base = raiz(pasta)
        self.antes, self.cortado = self._foto()

    def _foto(self):
        foto, total, cortado = {}, 0, False
        prazo = time.monotonic() + 1.5
        for d, pastas, arquivos in os.walk(self.base):
            if time.monotonic() > prazo:
                return foto, True
            pastas[:] = [p for p in pastas if p not in IGNORAR and not os.path.islink(os.path.join(d, p))
                         and not os.path.isjunction(os.path.join(d, p))]
            for nome in arquivos:
                caminho = os.path.join(d, nome)
                if os.path.islink(caminho):
                    continue
                try:
                    if len(foto) >= 2000 or total >= 8_000_000:
                        return foto, True
                    if os.path.getsize(caminho) > MAX_LER:
                        cortado = True
                        continue
                    with open(caminho, 'rb') as f:
                        dados = f.read(MAX_LER + 1)
                    if len(dados) > MAX_LER:
                        cortado = True
                        continue
                    total += len(dados)
                    foto[os.path.relpath(caminho, self.base).replace('\\', '/')] = dados
                except OSError:
                    cortado = True
        return foto, cortado

    def alteracoes(self):
        atual, cortado = self._foto()
        itens = []
        for arq in sorted(self.antes.keys() | atual.keys()):
            a, b = self.antes.get(arq), atual.get(arq)
            if a == b or (cortado and b is None) or (self.cortado and a is None):
                continue
            diff = "" if b"\0" in (a or b"") or b"\0" in (b or b"") else self._diff(arq, b)
            itens.append(dict(arq=arq, st='?' if a is None else 'D' if b is None else 'M',
                              mais=sum(l.startswith('+') and not l.startswith('+++') for l in diff.splitlines()),
                              menos=sum(l.startswith('-') and not l.startswith('---') for l in diff.splitlines())))
        return dict(ok=True, raiz=self.base, ramo='Desde que este projeto foi acompanhado', frente=None, itens=itens,
                    mais=sum(i['mais'] for i in itens), menos=sum(i['menos'] for i in itens), cortado=cortado or self.cortado)

    def _diff(self, arq, atual):
        import difflib
        antes = self.antes.get(arq, b'')
        return ''.join(difflib.unified_diff(antes.decode('utf-8', 'replace').splitlines(True),
                                          (atual or b'').decode('utf-8', 'replace').splitlines(True),
                                          fromfile='antes/' + arq, tofile='agora/' + arq))

    def diff(self, arq):
        caminho = _dentro(self.base, arq)
        try:
            with open(caminho, 'rb') as f:
                dados = f.read(MAX_LER + 1)
        except FileNotFoundError:
            dados = b''
        if b'\0' in dados or b'\0' in self.antes.get(arq, b''):
            return dict(ok=True, binario=True, texto='')
        texto = self._diff(arq, dados)
        return dict(ok=True, texto=texto[:MAX_LER], cortado=len(texto) > MAX_LER)


def buscar(pasta, termo):
    """até 300 arquivos cujo caminho contém o termo (git ls-files + novos; sem git, varre a pasta)"""
    base = raiz(pasta)
    t = (termo or "").lower().replace("\\", "/").strip()
    if not t:
        return {"ok": True, "itens": []}
    lista = _git(base, "ls-files", "-z", "--cached", "--others", "--exclude-standard", timeout=10)
    if lista is not None:
        todos = [a for a in lista.split("\0") if a]
    else:
        todos = []
        for d, pastas, arqs in os.walk(base):
            pastas[:] = [p for p in pastas if p not in IGNORAR]
            rel = os.path.relpath(d, base).replace("\\", "/")
            todos += [(f if rel == "." else rel + "/" + f) for f in arqs]
            if len(todos) > 50_000:
                break
    st = _status(base) or {}
    achados = [a for a in todos if t in a.lower()]
    achados.sort(key=lambda a: (t not in a.rsplit("/", 1)[-1].lower(), len(a)))
    return {"ok": True, "itens": [{"rel": a, "st": st.get(a, "")} for a in achados[:300]], "total": len(achados)}
