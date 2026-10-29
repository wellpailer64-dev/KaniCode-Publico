"""título da aba que acompanha o TEMA da conversa (2026-10-28): a Kani local lê as últimas trocas e dá 2–5 palavras.
Antes a aba mostrava a 1ª frase do último pedido ("Ok, faz isso"), e as abas se confundiam."""
import re

import ajudantes

QUANDO = {1, 2, 4}      # trocas em que reavalia; depois, a cada CADA
CADA = 4
_SISTEMA = ("Você dá nome a abas de conversa. Leia as trocas e responda SÓ com um título de 2 a 5 palavras em português "
            "que diga o TEMA geral (projeto, cliente, ferramenta ou problema), não o último pedido. Sem aspas, sem ponto, "
            "sem emoji, nada genérico como \"Tema da conversa\" ou \"Ajuda\". Use nomes próprios que aparecem. "
            "Exemplos: \"Abas do KaniCode por tema\", \"Reels BF do ClienteAlfa\", \"Exportação na placa\", "
            "\"Flyer da pizzaria\". Se o título atual ainda serve, repita-o igual.")


def deve(n):
    return n in QUANDO or (n > max(QUANDO) and n % CADA == 0)


def _limpo(t):
    t = (t or "").strip().splitlines()[0] if (t or "").strip() else ""
    t = re.sub(r"^(t[ií]tulo|tema)\s*:\s*", "", t, flags=re.I).strip(" \"'“”`*.#-")
    return t[:48] if 2 <= len(t) and len(t.split()) <= 7 else ""


def sugerir(atual, trocas):
    """trocas = [(pedido, resposta)]; devolve o título novo ou "" (Kani fora/erro: a aba fica como está)"""
    if not ajudantes.kani_disponivel() or not trocas:
        return ""
    linhas = []
    for p, r in trocas[-4:]:
        linhas.append("Pailer: " + re.sub(r"\s+", " ", p)[:400])
        if r:
            linhas.append("Assistente: " + re.sub(r"\s+", " ", r)[:300])
    pedido = f"{_SISTEMA}\n\nTítulo atual: {atual or '(nenhum)'}\n\nTrocas:\n" + "\n".join(linhas) + "\n\nTítulo:"
    r = ajudantes.kani(pedido)
    return _limpo(r["texto"]) if r.get("ok") else ""
