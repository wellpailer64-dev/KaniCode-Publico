"""Origem do conhecimento: nucleo distribuido, perfil pessoal e plugins instalados."""
import json
from pathlib import Path
from dados_app import pasta_dados

PLUGIN_FERRAMENTAS = {
    **dict.fromkeys(("rodar_js_kanivete", "ver_kanivete", "clicar_no_kanivete", "abrir_kanivete",
                    "abrir_ferramenta", "buscar_habilidade", "usar_habilidade", "reiniciar_kanivete",
                    "fechar_kanivete", "pedir_ao_kanivete", "consultar_receita"), "kanivete"),
    "demandas_panda": "pandalab",
}


def instalados():
    import plugins_kc
    return {p["id"]: p for p in plugins_kc.listar() if not p.get("erro")}


def arquivo_pessoal():
    return pasta_dados() / "cerebro" / "conhecimento_pessoal.json"


def ler(caminho):
    try:
        r = json.loads(Path(caminho).read_text(encoding="utf-8"))
        return r if isinstance(r, dict) else {}
    except (OSError, ValueError):
        return {}


def preservar_legado(registro):
    """Migracao aditiva: nunca substitui memorias locais nem publica os registros antigos."""
    destino = arquivo_pessoal()
    dados = ler(destino)
    if "registro_anterior_v1" not in dados:
        dados["registro_anterior_v1"] = registro
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_suffix(".json.tmp")
        temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(destino)
    return destino


def registros_plugins(plugins):
    for pid, plugin in plugins.items():
        raiz = Path(plugin["pasta"]).resolve()
        caminho = raiz / "conhecimento.json"
        if not caminho.resolve().is_relative_to(raiz):
            continue
        registro = ler(caminho)
        for grupo in ("ferramentas", "interfaces"):
            entradas = registro.get(grupo, {})
            if not isinstance(entradas, dict):
                continue
            for nome, entrada in entradas.items():
                if isinstance(entrada, dict):
                    yield pid, nome, entrada, str(caminho)


def validar_publico(registro):
    if registro.get("versao") != 2 or registro.get("camada") != "vanilla":
        raise ValueError("Registro publico deve declarar versao 2 e camada vanilla")
    for grupo in ("ferramentas", "interfaces"):
        for nome, item in registro.get(grupo, {}).items():
            if item.get("categoria") != "kanicode_vanilla" or nome in PLUGIN_FERRAMENTAS:
                raise ValueError("Conhecimento de plugin no nucleo: " + nome)
    import re
    texto = json.dumps(registro, ensure_ascii=False)
    if re.search(r"[A-Za-z]:[\\/]|(?:sk-|ghp_|github_pat_)[A-Za-z0-9_]{15,}", texto):
        raise ValueError("Caminho local ou credencial no registro publico")


def validar_pacote(arquivos):
    import re
    proibidos = re.compile(r"^(?:contas|cerebro|licoes|preferencias|perfil|conversas|conversas_pickle|mapa_d)/|(?:^|/)(?:client_secret[^/]*|\.env(?:\..*)?|token[^/]*\.json|credenciais[^/]*|desktop\.ini)$|\.(?:bin|sqlite3?|db)$", re.I)
    for arquivo in arquivos:
        if proibidos.search(arquivo.replace("\\", "/")):
            raise ValueError("Arquivo pessoal ou sensivel no pacote: " + arquivo)
