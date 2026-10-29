# Leitura de vídeos no KaniCode

Usa o motor de download do KANIVETE, FFmpeg, Pillow e Whisper já instalados, sem abrir o app principal.
O código do KANIVETE continua necessário; KANIVETE_RAIZ permite indicar outra pasta do código.

## Fluxo recomendado

1. baixar --url "LINK" salva MP4 (ou --formato mp3); info --url "LINK" consulta metadados.
2. analisar --arquivo "VIDEO_LOCAL" gera folha.jpg, leitura.md e transcricao.json.
3. Leia primeiro leitura.md e abra folha.jpg. Amplie apenas quadros necessários.
4. Para aprofundar, repita com --inicio 10 --fim 20. Os tempos são segundos absolutos do vídeo original.

Todos os comandos usam py -3.13 video_download.py nesta pasta. CLI, Kani e Claude/MCP usam a mesma ferramenta.
Codex recebe o caminho e o fluxo no contexto inicial e na retomada.

## Seleção e folha

--metodo cenas (padrão) detecta mudanças no vídeo reduzido a 4 amostras por segundo e evita quadros quase iguais.
--quantidade 8 é o máximo de quadros; uma cena estática pode gerar só um.
Se houver mais cenas do que o limite, a seleção distribui amostras pelas cenas.
--metodo uniforme gera a quantidade exata, distribuída pelo trecho, sem remover repetições.
Falha da detecção é avisada e usa amostragem uniforme.
A folha traz miniaturas, tempos absolutos e fala que coincida com o instante do quadro.
As legendas são abreviadas na folha; leitura.md e transcricao.json conservam os segmentos completos.
Quadros são amostras: cortes muito rápidos, gestos e detalhes pequenos podem exigir trechos menores e imagens individuais.

## Fala local

analisar usa --transcricao auto por padrão. quadros também gera folha, mas usa --transcricao nao por padrão.
auto tenta Whisper local quando há áudio; falha ou modelo ausente gera aviso explícito e preserva o resultado visual.
--transcricao sim exige transcrição concluída se houver áudio; sem áudio retorna sem_audio.
--transcricao nao desativa a fala. --modelo small e --idioma pt são os padrões; idioma auto detecta a língua.
Procura pesos .pt já existentes em modelos_ia/whisper ou dist/CaniveteDoPailer/modelos_ia/whisper.
Não instala pacotes nem baixa pesos; usa CPU, podendo demorar mais em vídeos longos.
Tempos dos segmentos são corrigidos para o vídeo original ao analisar um trecho.
Só trate a fala como transcrita quando o status for concluida. A transcrição automática pode errar.

## Cache e arquivos

Padrão: D:/Kanivete/Downloads; análises em Analises. --destino escolhe outra pasta no D.
O cache fica na pasta de destino: a mesma pasta permite reutilizar os resultados.
Confere conteúdo SHA-256 do vídeo, parâmetros da análise e assinatura do modelo.
Confere também integridade dos arquivos gerados antes de reutilizá-los.
Fala tem cache separado: mudar a quantidade de quadros não exige transcrever o mesmo trecho de novo.
--refazer ignora o cache da análise e da fala. Vídeo alterado, arquivo gerado ausente/corrompido ou parâmetros diferentes
provocam nova análise. Resultados anteriores são preservados em pastas únicas.
Leituras com erro ou indisponibilidade de transcrição não ficam como resultado definitivo no cache.
O cache não elimina o custo em tokens de voltar a abrir as imagens.

## Exemplos

    py -3.13 video_download.py baixar --url "https://site/video"
    py -3.13 video_download.py analisar --arquivo "D:/videos/referencia.mp4"
    py -3.13 video_download.py analisar --arquivo "D:/videos/referencia.mp4" --inicio 10 --fim 20 --quantidade 12
    py -3.13 video_download.py quadros --arquivo "D:/videos/referencia.mp4" --metodo uniforme --quantidade 8
    py -3.13 video_download.py analisar --arquivo "D:/videos/referencia.mp4" --transcricao nao --refazer

WhatsApp: link de conversa não é o arquivo de vídeo; obtenha a mídia pela ponte interna autorizada.
Links privados/expirados, DRM e bloqueios do site podem impedir download. Não importa cookies automaticamente.
Downloads mantêm o motor original e não sobrescrevem arquivos existentes; execução é isolada em processo separado.

## Verificação

    py -3.13 verificar.py --impacto video_download.py video_leitura.py tests/test_video_download.py tests/test_video_leitura.py --workers 2
    py -3.13 verificar.py --area kani --arquivos video_download.py video_leitura.py tests/test_video_leitura.py

Testes usam vídeo sintético no D, HTTP local efêmero para download, FFmpeg real e Whisper simulado para testes rápidos
de falha, sincronização e cache. Nenhum teste acessa contas ou o app do usuário.
