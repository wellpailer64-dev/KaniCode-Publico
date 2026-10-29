"""Glossário da escuta: o Parakeet escreve os nomes do app como se fala ("Cane", "Kanye", "Poto Canivete"...).
Corrige o texto falado ANTES de ir para a conversa (Claude ou Kani), no PC (voz.py) e no celular (movel.py).
Palavras novas do Pailer: D:/Kanivete/KaniCode/glossario.json → [["regex", "troca"], ...] (vem antes das de fábrica).
"""
import json, os, re

from dados_app import pasta_dados
ARQ = str(pasta_dados() / "glossario.json")
ARQ_TERMOS = os.path.join(os.path.dirname(__file__), "glossario_termos.json")

_KV = r"[ck]a[nm]+i?[vb]e?t[ei]?s?"   # canivete, kanivete, canivet, kanivetes...
FABRICA = [
    # \s* = junto também: a escuta escreve "fotocanivete" numa palavra só (2026-10-21)
    (r"\b(?:poto|foto|fhoto|photo|fot)\s*" + _KV + r"\b", "Photo Kanivete"),
    (r"\bv[ií]deo\s*" + _KV + r"\b", "Vídeo Kanivete"),
    (r"\bvetor\s*" + _KV + r"\b", "Vetor Kanivete"),
    (r"\b(?:sound|saund)\s*" + _KV + r"\b", "Sound Kanivete"),
    (r"\b(?:slider|slaider)\s*" + _KV + r"\b", "Slider Kanivete"),
    (r"\b(?:lux|lucs|luks)\s*" + _KV + r"\b", "Lux Kanivete"),
    (r"\b" + _KV + r"\s+encoder\b", "Kanivete Encoder"),
    (r"\b(?:cani|kane|cane|kanye|cany|kani)\s*(?:browser|brauser|brouser)\b", "KaniBrowser"),
    (r"\b(?:cani|kane|cane|kanye|cany|kani)\s*(?:code|cod|cold)\b", "KaniCode"),
    (r"\b" + _KV + r"\b", "KANIVETE"),
    (r"\b(?:cane|kane|kanye|carni|cani|cany|kenny|câni|cáni|connie|conny|kaní)\b", "Kani"),
    (r"\bcloud\b", "Claude"),
]


def termos():
    """A mesma fonte serve à correção da fala e aos vértices do RAG."""
    try:
        with open(ARQ_TERMOS, encoding="utf-8") as f:
            dados = json.load(f)
        return [dict(t, origem=dados["origem"]) for t in dados["termos"]
                if isinstance(t, dict) and t.get("id") and t.get("termo") and t.get("definicao")]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def _corrigir_rack(texto):
    def trocar(m):
        antes = re.split(r"[.!?\n]", texto[:m.start()])[-1][-100:]
        depois = re.split(r"[.!?\n]", texto[m.end():])[0][:100]
        contexto = antes + " " + depois
        if re.search(r"\b(?:servidor(?:es)?|hardware|equipamentos?|switch|datacenter|prateleira|rede)\b", contexto, re.I):
            return m.group(0)
        if re.search(r"\b(?:kanicode|c[eé]rebro|mem[oó]ria|grafo|v[eé]rtices?|arestas?|clusters?|habilidades?|aprendizados?|conhecimento)\b", contexto, re.I):
            return "RAG"
        return m.group(0)
    return re.sub(r"\brack\b", trocar, texto, flags=re.I)


def _regras():
    extra = []
    try:
        with open(ARQ, encoding="utf-8") as f:
            extra = [tuple(x) for x in json.load(f)]
    except Exception:
        pass
    return extra + FABRICA


def corrigir(texto):
    for padrao, troca in _regras():
        try:   # "Kanivete" já certo (Photo Kanivete...) não vira KANIVETE de novo
            texto = re.sub(padrao, lambda m: m.group(0) if m.group(0) in ("Kanivete", "Kani") else troca, texto, flags=re.I)
        except re.error:
            pass
    for termo in termos():
        for forma in termo.get("formas", []):
            try:
                texto = re.sub(forma["padrao"], forma["troca"], texto, flags=re.I)
            except (re.error, KeyError, TypeError):
                pass
    return _corrigir_rack(texto)


if __name__ == "__main__":
    for t in ("Cane, abre o Poto Canivete", "Você tem a capacidade de abrir o WhatsApp no Cani Browser?",
              "fechar o Slider Canivet e o Kanye Browser", "Certo, Carni, conversa no Kane Code", "o cloud faz isso"):
        print(t, "→", corrigir(t))
