"""Barra de progresso no KaniCode para qualquer ferramenta Python (mesma faixa do render e do download).

Dentro do script (não importa o KaniCode; sem ele aberto, não faz nada):
    sys.path.insert(0, r"D:/Kanivete/Plugins/kanicode"); from kc_progresso import Barra, acompanhar
    for f in acompanhar(arquivos, "Convertendo fotos"): ...
    with Barra("Gerando banners") as b:
        b(30, "banner 3 de 10")          # porcentagem e detalhe; b.passo(3, 10) também serve

Sem mexer no script: lê a porcentagem que ele já escreve (tqdm "45%|", "3/10", "[3/10]"):
    py -3.13 D:/Kanivete/Plugins/kanicode/kc_progresso.py [--titulo X] -- py -3.13 script.py args
A saída continua aparecendo e o código de saída é o do script.
"""
import json, os, re, socket, subprocess, sys, time

PORTA = 47613            # canal local do KaniCode (kanicode.PORTA)
INTERVALO = 0.5          # no máximo 2 sinais por segundo


def _mandar(item):
    try:
        with socket.create_connection(("127.0.0.1", PORTA), timeout=1) as s:
            s.sendall(("progresso " + json.dumps([item], ensure_ascii=False) + "\n").encode("utf-8"))
            return s.recv(8).strip() == b"ok"
    except OSError:
        return False


class Barra:
    def __init__(self, titulo, id=None):
        self.titulo = str(titulo)[:140]
        self.id = "ferramenta:" + (id or f"{self.titulo}:{os.getpid()}:{time.monotonic_ns()}")
        self.pct, self.detalhe = None, ""
        self._ultimo, self._fora = 0.0, 0.0
        self._enviar("ativo", forcar=True)

    def _enviar(self, estado, forcar=False):
        agora = time.monotonic()
        if not forcar and (agora - self._ultimo < INTERVALO or agora < self._fora):
            return
        self._ultimo = agora
        ok = _mandar({"id": self.id, "tipo": "ferramenta", "titulo": self.titulo, "pct": self.pct,
                      "estado": estado, "detalhe": self.detalhe[:240]})
        if not ok:
            self._fora = agora + 5      # KaniCode fechado: tenta de novo daqui a pouco, sem atrasar o script

    def __call__(self, pct=None, detalhe=None):
        if pct is not None:
            self.pct = max(0.0, min(100.0, float(pct)))
        if detalhe is not None:
            self.detalhe = str(detalhe)
        self._enviar("ativo")

    def passo(self, feito, total, detalhe=None):
        self(100 * feito / total if total else None, detalhe)

    def fim(self, estado="concluido", detalhe=None):
        if detalhe is not None:
            self.detalhe = str(detalhe)
        self._fora = 0
        self._enviar(estado, forcar=True)

    def __enter__(self):
        return self

    def __exit__(self, tipo, erro, _tb):
        if tipo is None:
            self.fim()
        elif issubclass(tipo, KeyboardInterrupt):
            self.fim("cancelado")
        else:
            self.fim("erro", f"{tipo.__name__}: {erro}")
        return False


def acompanhar(itens, titulo, total=None):
    """como o tqdm: passa os itens adiante e mostra quantos já foram"""
    if total is None:
        try:
            total = len(itens)
        except TypeError:
            total = None
    with Barra(titulo) as b:
        for i, item in enumerate(itens):
            yield item
            b.passo(i + 1, total, f"{i + 1} de {total}" if total else f"{i + 1} feitos")


_PCT = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d+)?)\s?%")
_FRACAO = re.compile(r"(?<![\d/.:-])(\d+)\s?/\s?(\d+)(?![\d/.:-])")


def ler_linha(linha):
    """porcentagem que a linha anuncia (a última), ou None"""
    achados = [float(m.group(1).replace(",", ".")) for m in _PCT.finditer(linha)]
    achados = [p for p in achados if p <= 100]
    if achados:
        return achados[-1]
    for m in reversed(list(_FRACAO.finditer(linha))):
        feito, total = int(m.group(1)), int(m.group(2))
        if 0 < total and feito <= total:
            return 100 * feito / total
    return None


def rodar(cmd, titulo):
    b = Barra(titulo)
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    except OSError as e:
        b.fim("erro", str(e))
        print(e, file=sys.stderr)
        return 127
    saida, resto = sys.stdout.buffer, b""
    try:
        while True:
            pedaco = p.stdout.read1(4096)
            if not pedaco:
                break
            saida.write(pedaco); saida.flush()
            partes = re.split(rb"[\r\n]", resto + pedaco)
            resto = partes.pop()
            for linha in partes:
                texto = linha.decode("utf-8", "replace").strip()
                if texto:
                    b(ler_linha(texto), texto)
            if resto:     # tqdm reescreve a mesma linha sem quebrar
                texto = resto.decode("utf-8", "replace").strip()
                pct = ler_linha(texto)
                if pct is not None:
                    b(pct, texto)
        cod = p.wait()
    except KeyboardInterrupt:
        p.terminate()
        b.fim("cancelado")
        return 130
    b.fim("concluido" if cod == 0 else "erro", None if cod == 0 else f"saiu com código {cod}: {b.detalhe}")
    return cod


def main(args):
    titulo = None
    if args[:1] == ["--titulo"]:
        titulo, args = args[1], args[2:]
    if args[:1] == ["--"]:
        args = args[1:]
    if not args:
        print(__doc__)
        return 2
    if not titulo:
        nomes = [a for a in args if a.endswith(".py")]
        titulo = os.path.basename(nomes[0] if nomes else args[0])
    return rodar(args, titulo)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
