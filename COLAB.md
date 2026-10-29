# Colab Board — Colab entre chats

No Board (Ctrl+B), use **⇄ Colab**. Escolha duas abas paradas, na mesma pasta de projeto,
escreva o objetivo e clique em **Criar e planejar**. Também pode puxar o fio entre dois chats
e escolher Colab. O chat de origem coordena; os dois conservam seus modelos e históricos.

O chat de origem é o **Chamador**; o outro é o **Chamado**. O Chamador define o contrato, as interfaces,
as instruções, o formato da entrega e as tarefas com arquivos relativos explícitos. O Chamado segue
esse contrato, sem ampliar o escopo nem delegar a terceiros; impedimentos são relatados no diário.
O Chamador aprova a revisão e inicia executar. Sessões antigas preservam a aprovação dos dois.
Uma proposta nova invalida aprovações anteriores. Arquivo ou pasta não pode pertencer às duas abas.
Depois da execução começar o plano fica estável; impedimentos e mudanças necessárias vão ao diário.
A reserva é um acordo informado aos modelos, não uma trava de escrita no disco.

O início de executar dispara o parceiro sem esperar a resposta; o coordenador continua sua parte.
Durante a execução ambos consultam o diário e publicam avisos sem chamadas bloqueantes entre si.
Cada um registra sua entrega e evidências. Quando ambos entregam, o estado passa para integração.
O coordenador é retomado automaticamente ao ficar livre e testa o conjunto antes de finalizar.
O botão **Continuar com o coordenador** também retoma
planejamento/execução/integração pendente; também serve quando uma resposta terminou antes do parceiro.

O painel Colab mostra objetivo, fase, revisão, aprovações, arquivos, entregas e avisos em tempo real.
Os cartões dos chats mostram mensagens completas e atividade recebida, inclusive progresso do Codex,
entradas e saídas de ferramentas. O texto pode ser selecionado; mova o cartão pelo cabeçalho.
Use **Conversar aqui** para responder numa aba. A recuperação inicial mostra até 200 registros recentes;
o histórico original permanece no armazenamento de cada modelo.

## Canal dos agentes

Claude: ferramenta MCP `chat`, `acao=colab`, `de`, `para`, `texto` com objeto JSON serializado.
Codex e modelos com terminal: `py -3.13 "<pasta do plugin>/chat_colab.py" --de 1 --para 2 --acao colab`.
Sem texto, consulta o estado. Para ações, `--texto` recebe JSON; para JSON complexo prefira `--arquivo`
com caminho de um arquivo UTF-8 no D. O contexto de cada turno inclui estado e instruções do Colab.

Objeto de ação:
- `consultar`: lê o estado sem bloquear nem gravar.
- `propor`: `contrato`, `tarefas: [{aba, titulo, arquivos: [caminhos relativos]}]`.
- `aprovar` e `executar`: `revisao` numérica; executar é exclusivo do coordenador.
- `avisar`: `texto` para o diário compartilhado.
- `concluir_tarefa`: `evidencia` da entrega e da verificação da sua parte.
- `finalizar`: `evidencia` do teste integrado, exclusivo do coordenador.

O canal é o mesmo servidor local dos fios (47613); não acessa as portas do Kanivete.
Estado e diário ficam em estado.json, chave colabs, sob a trava de estado do aplicativo.
Remover um fio desliga a colaboração; não apaga arquivos ou históricos dos agentes.

Verificação isolada: `py -3.13 verificar.py --area board`.
Os testes usam motores simulados e Chromium isolado; não consomem sessões reais dos modelos.


## Auto-Colab

Configurações › Preferências › **Auto-Colab** liga/desliga a autonomia para novas chamadas.
Desligado por padrão; a preferência fica salva globalmente. Desligar não cancela Colabs em andamento.
A mudança de orientação entra nos próximos turnos; o bloqueio de novas chamadas vale imediatamente.

Ligado, o próprio modelo avalia a complexidade e a possibilidade de dividir o trabalho. Para tarefas
simples ou escritas inseparáveis, continua sozinho. Havendo benefício, informa o usuário e chama
`chat` com `acao=colab`, `de=<sua aba>`, `para=auto`, `texto=<JSON abaixo>`; com terminal, usa
`chat_colab.py --de <sua aba> --para auto --acao colab --arquivo <JSON UTF-8 no D>`.
Kani e Pickle usam `chat_colab` com `para=auto`, `dados=<objeto>`.

```json
{"acao":"iniciar_auto","objetivo":"Site autorizado pelo usuário","contrato":"API, instruções exatas, formato da entrega e testes esperados","tarefas":[{"aba":"chamador","titulo":"Implementar API e testar","arquivos":["api.py"]},{"aba":"chamado","titulo":"Implementar interface; entregar resumo e evidência de teste","arquivos":["ui/site.js"]}]}
```

O app valida o plano antes de abrir uma aba dedicada na mesma pasta, sem mudar a aba em uso.
Claude chama Codex; os demais chamam Claude. `quem` opcional pode escolher `claude` ou `codex`,
sempre diferente do modelo do Chamador. Os modelos precisam estar configurados no KaniCode.
A resposta contém os IDs reais para consultar o diário e registrar entregas nas próximas ações.
O Chamado começa em paralelo; o Chamador já está trabalhando e segue sua parte.
Ao entrar em execução, o Colab Board abre automaticamente e enquadra os dois participantes
com o fio ⇄ Colab visível. No Auto-Colab, o novo quadro fica ao lado do Chamador.
Atualizações do diário não reabrem o Board se o usuário voltar às abas.

Só uma Colab ativa por aba. O Chamado não pode criar outra nem comandar o Chamador ou reescrever
o plano. Instruções do usuário e regras do projeto prevalecem; impedimentos devem ser informados.
Após as duas entregas, só o Chamador integra, testa e finaliza. As reservas de arquivos são
um contrato informado aos agentes, não uma trava de escrita. Os testes usam motores simulados:
não provam que um modelo real sempre reconheça a complexidade ou cumpra instruções perfeitamente.
