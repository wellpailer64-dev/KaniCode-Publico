# Arquivos e alterações do projeto ativo

Abra o botão Projeto no topo do KaniCode. O caminho mostrado identifica a pasta
acompanhada. Cada aba segue os caminhos informados nas operações das ferramentas
(arquivos, workdir/cwd e comandos com caminhos explícitos). A pasta inicial da
conversa é a referência enquanto nenhum outro projeto for identificado; o painel
não altera a pasta de execução nem a sessão do agente.

O projeto é delimitado pelo marcador mais próximo (kanivete.json, pyproject.toml,
package.json ou .git); sem marcador, usa a pasta informada. Plugins dentro de um
repositório maior mostram somente seus próprios arquivos e alterações.

Com o painel aberto, arquivos e alterações são conferidos a cada três segundos.
Clique numa alteração para ver o diff; ± alterna para o arquivo completo. Editar
abre o texto no próprio painel; Salvar ou Ctrl+S grava, e Cancelar abandona a edição.
O editor aceita arquivos UTF-8 completos de até 400 KB e conserva CRLF quando existe.
Arquivos binários, muito grandes ou de outra codificação continuam apenas para leitura.

Se o agente ou outro programa mudar o arquivo durante a edição, Salvar informa o
conflito e mantém seu rascunho. Copie-o antes de cancelar e reabrir a versão do disco.
Durante uma troca de aba/projeto, uma edição aberta fica preservada: volte à aba e
ao projeto de origem para salvar, ou cancele para acompanhar o novo projeto.

Com Git, as alterações são comparadas ao HEAD (ou arquivo novo antes do primeiro
commit). Sem Git, a referência é o momento em que a pasta começou a ser acompanhada
nesta execução. A referência fica em memória; reiniciar cria uma nova referência.
A captura sem Git limita arquivos, bytes e duração e informa quando é parcial.
Pastas ignoradas, arquivos acima do limite e caminhos que uma ferramenta não informa
podem ficar fora do acompanhamento. Não consulta a porta do Kanivete.

Validação: tests/test_projeto.py e tests/test_projeto_ui.py (pastas sintéticas no D,
Chromium isolado e Git local sem commits), além da bateria essencial por impacto.

