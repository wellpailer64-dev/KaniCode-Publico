"""Folhas de vídeo, cenas, trechos e transcrição local com cache conferido."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageStat

VERSAO = 1
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def validar(arquivo, quantidade, inicio, fim, metodo, transcricao, modelo, idioma):
    if type(quantidade) is not int or not 1 <= quantidade <= 20:
        raise ValueError("Quantidade de quadros deve estar entre 1 e 20.")
    for nome, valor in (("início", inicio), ("fim", fim)):
        if valor is not None and (type(valor) not in (int, float) or not math.isfinite(valor) or valor < 0):
            raise ValueError(f"Tempo de {nome} inválido; use segundos positivos.")
    if inicio is None or (fim is not None and fim <= inicio):
        raise ValueError("O fim deve ser maior que o início.")
    if metodo not in ("cenas", "uniforme") or transcricao not in ("auto", "sim", "nao"):
        raise ValueError("Método ou modo de transcrição inválido.")
    if modelo not in ("tiny", "base", "small", "medium", "large", "large-v2", "large-v3"):
        raise ValueError("Modelo Whisper inválido.")
    if not isinstance(idioma, str) or not re.fullmatch(r"auto|[a-z]{2,3}", idioma):
        raise ValueError("Use idioma auto ou código como pt/en.")
    origem = Path(arquivo).expanduser().resolve()
    if not origem.is_file():
        raise ValueError("Arquivo de vídeo não encontrado.")
    return origem


def _hash(arquivo):
    h = hashlib.sha256()
    with open(arquivo, "rb") as entrada:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _chave(dados):
    return hashlib.sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _gravar(arquivo, dados):
    if isinstance(dados, dict) and "resultado" in dados:
        dados["assinatura_resultado"] = _chave(dados["resultado"])
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=arquivo.parent, suffix=".json", delete=False) as saida:
        json.dump(dados, saida, ensure_ascii=False, indent=2)
        temporario = saida.name
    os.replace(temporario, arquivo)


def _rodar(cmd, prazo=120):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=prazo, creationflags=NO_WINDOW, check=True)


def _sondar(origem, ffmpeg):
    probe = Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    if not ffmpeg or not probe.is_file():
        raise RuntimeError("FFmpeg/FFprobe não encontrados.")
    r = _rodar([str(probe), "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                "-of", "json", str(origem)], 60)
    info = json.loads(r.stdout)
    duracao = float(info["format"]["duration"])
    if not math.isfinite(duracao) or duracao <= 0:
        raise ValueError("Não foi possível determinar a duração do vídeo.")
    tipos = {s.get("codec_type") for s in info.get("streams", [])}
    if "video" not in tipos:
        raise ValueError("O arquivo não contém uma faixa de vídeo.")
    return duracao, "audio" in tipos


def _modelo_local(motor, nome):
    raiz = Path(motor.__file__).resolve().parent.parent
    for base in (raiz / "modelos_ia" / "whisper", raiz / "dist" / "CaniveteDoPailer" / "modelos_ia" / "whisper"):
        arquivo = base / (nome + ".pt")
        if arquivo.is_file():
            st = arquivo.stat()
            return arquivo, [str(arquivo), st.st_size, st.st_mtime_ns]
    return None, None


def _tempos(ffmpeg, origem, inicio, fim, quantidade, metodo):
    if metodo == "uniforme":
        return [inicio + (fim - inicio) * (i + 0.5) / quantidade for i in range(quantidade)], []
    try:
        r = _rodar([ffmpeg, "-nostdin", "-hide_banner", "-ss", str(inicio), "-i", str(origem),
                    "-t", str(fim - inicio), "-an", "-vf",
                    r"setpts=PTS-STARTPTS,fps=4,scale=160:-2,select=gt(scene\,0.25),showinfo",
                    "-fps_mode", "vfr", "-f", "null", "-"], 600)
        cortes = [inicio]
        for valor in re.findall(r"pts_time:([0-9.eE+-]+)", r.stderr):
            segundo = inicio + float(valor)
            if cortes[-1] + 0.15 < segundo < fim - 0.15:
                cortes.append(segundo)
        cortes.append(fim)
        medios = [(a + b) / 2 for a, b in zip(cortes, cortes[1:])]
        if len(medios) > quantidade:
            medios = [medios[min(len(medios) - 1, int((i + 0.5) * len(medios) / quantidade))] for i in range(quantidade)]
        return medios, []
    except (subprocess.SubprocessError, OSError, ValueError):
        return _tempos(ffmpeg, origem, inicio, fim, quantidade, "uniforme")[0], [
            "Detecção de cenas indisponível; foram usadas amostras distribuídas pelo trecho."]


def _transcrever(origem, ffmpeg, inicio, fim, modelo, idioma, pasta):
    """Somente pesos locais; áudio convertido pelo FFmpeg já instalado."""
    import numpy as np
    import whisper
    import wave
    audio = pasta / "audio_transcricao.wav"
    _rodar([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-ss", str(inicio), "-i", str(origem),
            "-t", str(fim - inicio), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)], 600)
    with wave.open(str(audio), "rb") as entrada:
        amostras = np.frombuffer(entrada.readframes(entrada.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    motor = whisper.load_model(str(modelo), device="cpu", download_root=str(pasta))
    r = motor.transcribe(amostras, language=None if idioma == "auto" else idioma, fp16=False, verbose=None)
    segmentos = []
    for s in r.get("segments", []):
        ini, final = inicio + float(s["start"]), inicio + float(s["end"])
        texto = str(s["text"]).strip()
        if texto and math.isfinite(ini) and math.isfinite(final) and ini < fim and final > inicio:
            segmentos.append({"inicio": round(max(inicio, ini), 3), "fim": round(min(fim, final), 3), "texto": texto})
    return segmentos


def _tempo(segundo):
    ms = int(round(segundo * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def _legenda(segmentos, segundo):
    return " ".join(s["texto"] for s in segmentos if s["inicio"] <= segundo < s["fim"])


def _fonte(tamanho):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", tamanho)
    except OSError:
        return ImageFont.load_default(size=tamanho)


def _linhas(texto, desenho, fonte, largura, maximo):
    linhas, atual = [], ""
    for palavra in texto.split():
        candidata = (atual + " " + palavra).strip()
        if desenho.textlength(candidata, font=fonte) > largura and atual:
            linhas.append(atual)
            atual = palavra
        else:
            atual = candidata
    if atual:
        linhas.append(atual)
    if len(linhas) > maximo:
        linhas = linhas[:maximo]
        linhas[-1] = linhas[-1][:max(0, len(linhas[-1]) - 3)] + "..."
    return linhas


def _folha(quadros, destino, nome, inicio, fim):
    cols = min(4, len(quadros))
    cel_w, cel_h, margem = 320, 284, 12
    folha = Image.new("RGB", (cols * cel_w + margem, math.ceil(len(quadros) / cols) * cel_h + 64), "#171b22")
    d = ImageDraw.Draw(folha)
    fonte, pequena = _fonte(17), _fonte(14)
    titulo = f"{nome} | {_tempo(inicio)} a {_tempo(fim)}"
    d.text((margem, 12), _linhas(titulo, d, fonte, folha.width - 24, 1)[0], font=fonte, fill="white")
    for i, q in enumerate(quadros):
        x, y = margem + (i % cols) * cel_w, 52 + (i // cols) * cel_h
        with Image.open(q["arquivo"]) as img:
            mini = ImageOps.contain(img.convert("RGB"), (cel_w - 12, 174))
            folha.paste(mini, (x + (cel_w - 12 - mini.width) // 2, y + (174 - mini.height) // 2))
        d.text((x, y + 180), f"{i + 1:02d}  {_tempo(q['segundo'])}", font=fonte, fill="#7dd3fc")
        texto = q.get("fala") or "(sem fala transcrita neste instante)"
        for j, linha in enumerate(_linhas(texto, d, pequena, cel_w - 18, 4)):
            d.text((x, y + 205 + j * 17), linha, font=pequena, fill="#e5e7eb")
    folha.save(destino, quality=88)


def _cache_ler(arquivo):
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        if not isinstance(dados["resultado"], dict) or dados["assinatura_resultado"] != _chave(dados["resultado"]):
            return None
        for nome, esperado in dados["assinaturas"].items():
            caminho = Path(nome)
            if not caminho.is_file() or _hash(caminho) != esperado:
                return None
        return dados["resultado"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def analisar(origem, pasta, motor, quantidade=8, inicio=0, fim=None, metodo="cenas",
             transcricao="auto", modelo="small", idioma="pt", refazer=False):
    ffmpeg = motor._resolver_ffmpeg_exe()
    duracao, tem_audio = _sondar(origem, ffmpeg)
    fim = duracao if fim is None else fim
    if inicio >= duracao or fim > duracao + 0.01:
        raise ValueError(f"Trecho fora do vídeo; duração: {duracao:.3f} s.")
    fim = min(fim, duracao)
    estado_origem = (origem.stat().st_size, origem.stat().st_mtime_ns)
    identidade = _hash(origem)
    modelo_path, assinatura_modelo = _modelo_local(motor, modelo) if tem_audio and transcricao != "nao" else (None, None)
    parametros = [VERSAO, str(origem), identidade, inicio, fim, quantidade, metodo, transcricao, idioma, modelo, assinatura_modelo]
    cache = pasta / ".cache_video"
    cache.mkdir(exist_ok=True)
    registro = cache / (_chave(parametros) + ".json")
    if not refazer:
        pronto = _cache_ler(registro)
        if pronto:
            return {**pronto, "cache": True}
    saida = Path(tempfile.mkdtemp(prefix="leitura_", dir=pasta))
    avisos, segmentos, audio_cache = [], [], False
    status = "desativada" if transcricao == "nao" else "sem_audio" if not tem_audio else "indisponivel"
    if tem_audio and transcricao != "nao":
        if modelo_path is None:
            avisos.append(f"Modelo Whisper {modelo} não encontrado localmente; nenhuma instalação ou download foi feito.")
        else:
            registro_audio = cache / ("fala_" + _chave([VERSAO, identidade, inicio, fim, assinatura_modelo, idioma]) + ".json")
            pronto = _cache_ler(registro_audio) if not refazer else None
            if pronto is not None:
                segmentos, status, audio_cache = pronto["segmentos"], "concluida", True
            else:
                try:
                    segmentos = _transcrever(origem, ffmpeg, inicio, fim, modelo_path, idioma, saida)
                    status = "concluida"
                    if estado_origem != (origem.stat().st_size, origem.stat().st_mtime_ns):
                        raise RuntimeError("O vídeo mudou durante a transcrição.")
                    _gravar(registro_audio, {"resultado": {"segmentos": segmentos}, "assinaturas": {}})
                except Exception as e:
                    status = "erro"
                    avisos.append("Transcrição não concluída: " + str(e)[:250])
        if transcricao == "sim" and status != "concluida":
            raise RuntimeError("; ".join(avisos))
    tempos, avisos_cenas = _tempos(ffmpeg, origem, inicio, fim, quantidade, metodo)
    avisos.extend(avisos_cenas)
    quadros, miniaturas = [], []
    for i, segundo in enumerate(tempos):
        imagem = saida / f"quadro_{i + 1:02d}.jpg"
        _rodar([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-ss", str(segundo),
                "-i", str(origem), "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "3", str(imagem)])
        with Image.open(imagem) as img:
            img.verify()
        with Image.open(imagem) as img:
            mini = img.convert("RGB").resize((32, 18))
        if metodo == "cenas" and any(sum(ImageStat.Stat(ImageChops.difference(mini, anterior)).mean) / 3 < 3
                                      for anterior in miniaturas):
            continue
        miniaturas.append(mini)
        quadros.append({"segundo": round(segundo, 3), "arquivo": str(imagem), "fala": _legenda(segmentos, segundo)[:400]})
    folha, texto, fala_json = saida / "folha.jpg", saida / "leitura.md", saida / "transcricao.json"
    _folha(quadros, folha, origem.name, inicio, fim)
    _gravar(fala_json, {"status": status, "segmentos": segmentos})
    linhas = [f"# Vídeo: {origem.name}", f"Trecho: {_tempo(inicio)} a {_tempo(fim)}", f"Transcrição: {status}",
              "A folha usa amostras; não representa todos os frames.", "", "## Quadros"]
    linhas += [f"- {_tempo(q['segundo'])}: {Path(q['arquivo']).name} — {q['fala']}" for q in quadros]
    linhas += ["", "## Fala transcrita"]
    linhas += [f"[{_tempo(s['inicio'])} – {_tempo(s['fim'])}] {s['texto']}" for s in segmentos]
    linhas += ["", *avisos]
    texto.write_text("\n".join(linhas), encoding="utf-8")
    if estado_origem != (origem.stat().st_size, origem.stat().st_mtime_ns):
        raise RuntimeError("O vídeo mudou durante a leitura; execute novamente.")
    resultado = {"ok": True, "arquivo": str(origem), "duracao": duracao, "inicio": inicio, "fim": fim,
                 "metodo": metodo, "quadros": quadros, "folha": str(folha), "leitura": str(texto),
                 "transcricao": {"status": status, "arquivo": str(fala_json), "segmentos": len(segmentos),
                                  "cache": audio_cache}, "avisos": avisos, "cache": False}
    arquivos = [folha, texto, fala_json, *(Path(q["arquivo"]) for q in quadros)]
    if status not in ("erro", "indisponivel"):
        _gravar(registro, {"resultado": resultado, "assinaturas": {str(a): _hash(a) for a in arquivos}})
    return resultado
