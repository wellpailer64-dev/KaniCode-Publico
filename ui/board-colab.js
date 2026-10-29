/* Colab do Board: objetivo, acordo entre modelos e diário compartilhado, sem trocar de aba. */
(() => {
  if (!window.KC_BOARD) return;
  const B = KC_BOARD.estado, estados = {};
  let atual = null, pendente = null;
  function mostrarPendente() {
    if (!pendente) return;
    const s = estados[pendente];
    if (!s || s.fase !== 'execucao') { pendente = null; return; }
    if (!B.fios.some(f => f.id === pendente && f.modo === 'colab')) return;
    if (!KC_BOARD.mostrarColab(s.membros, !!s.automatico)) return;
    pendente = null;
    if (dlg.open) dlg.close();
  }
  const dlg = document.createElement('dialog');
  dlg.className = 'bd-colab'; dlg.setAttribute('aria-label', 'Colab entre chats');
  dlg.innerHTML = `<form method="dialog"><header><b>Colab entre chats</b><button aria-label="Fechar">✕</button></header></form>
    <section class="colab-novo"><label>Chamador<select class="colab-de"></select></label>
    <label>Chamado<select class="colab-para"></select></label><label>Objetivo<textarea class="colab-objetivo" rows="3" placeholder="O que os dois vão construir juntos?"></textarea></label>
    <button class="colab-criar">Criar e planejar</button></section>
    <label>Colabs existentes<select class="colab-lista"></select></label>
    <p class="colab-erro" role="alert"></p><section class="colab-estado" aria-live="polite"></section>
    <button class="colab-continuar" hidden>Continuar com o Chamador</button>`;
  document.body.appendChild(dlg);
  const el = c => dlg.querySelector('.colab-' + c);
  const rot = { planejamento: 'Planejando juntos', execucao: 'Executando em paralelo', integracao: 'Integração e teste conjunto', concluido: 'Concluído' };
  function render() {
    const s = estados[atual];
    el('continuar').hidden = !s || s.fase === 'concluido';
    if (!s) { el('estado').innerHTML = '<p>Escolha dois chats na mesma pasta de projeto.</p>'; return; }
    const papel = aba => String(aba) === s.coordenador ? 'Chamador' : 'Chamado';
    el('estado').innerHTML = `<p>Chamador: ${esc(KC_BOARD.nomeAba(s.coordenador))} · Chamado: ${esc(KC_BOARD.nomeAba(s.membros.find(a => a !== s.coordenador)))}</p><h3>${esc(rot[s.fase] || s.fase)} · revisão ${s.revisao}</h3><p>${esc(s.objetivo)}</p>
      <p>Aprovações: ${(s.aprovacoes || []).map(KC_BOARD.nomeAba).map(esc).join(', ') || 'aguardando aprovação do Chamador'}</p>
      <div class="colab-contrato">${esc(s.contrato || 'As interfaces e a divisão de arquivos ainda serão combinadas.')}</div>
      ${(s.tarefas || []).map(t => `<article><b>${t.concluida ? '✓' : '○'} ${papel(t.aba)} · ${esc(KC_BOARD.nomeAba(t.aba))} — ${esc(t.titulo)}</b><pre>${esc(t.arquivos.join('\n'))}</pre>${t.evidencia ? `<p>${esc(t.evidencia)}</p>` : ''}</article>`).join('')}
      <h4>Conversa de coordenação</h4><div class="colab-diario">${(s.diario || []).map(d => `<p><b>${esc(KC_BOARD.nomeAba(d.aba))}:</b> ${esc(d.texto)}</p>`).join('') || 'Ainda sem avisos.'}</div>`;
  }
  async function carregar() {
    const fs = B.fios.filter(f => f.modo === 'colab');
    el('lista').innerHTML = '<option value="">Escolher Colab</option>' + fs.map(f => `<option value="${esc(f.id)}">${esc(KC_BOARD.nomeAba(f.de))} + ${esc(KC_BOARD.nomeAba(f.para))}</option>`).join('');
    for (const f of fs) {
      try { const s = await api().colab_consultar(f.id); if (s && typeof s === 'object') estados[f.id] = s; } catch (e) { el('erro').textContent = String(e); }
    }
    if (!fs.some(f => f.id === atual)) atual = fs[0]?.id || null;
    el('lista').value = atual || ''; render();
  }
  function abrir(de, para) {
    const op = KC_ABAS.lista.map(a => `<option value="${esc(a.id)}">${esc(KC_BOARD.nomeAba(a.id))}</option>`).join('');
    el('de').innerHTML = op; el('para').innerHTML = op;
    el('de').value = de || KC_ABAS.ativa;
    el('para').value = para || KC_ABAS.lista.find(a => a.id !== el('de').value)?.id || '';
    el('erro').textContent = '';
    if (!dlg.open) dlg.showModal();
    carregar();
  }
  el('criar').onclick = async () => {
    el('criar').disabled = true; el('erro').textContent = '';
    try {
      const f = await api().colab_criar(el('de').value, el('para').value, el('objetivo').value);
      if (!f || !f.id) throw new Error('Não foi possível criar o Colab.');
      atual = f.id;
      B.fios = await api().fios();
      await carregar();
      await api().colab_planejar(f.id);
    } catch (e) { el('erro').textContent = String(e); }
    finally { el('criar').disabled = false; }
  };
  el('lista').onchange = () => { atual = el('lista').value; render(); };
  el('continuar').onclick = async () => {
    el('continuar').disabled = true; el('erro').textContent = '';
    try { await api().colab_planejar(atual); } catch (e) { el('erro').textContent = String(e); }
    finally { el('continuar').disabled = false; }
  };
  const bt = document.createElement('button'); bt.textContent = '⇄ Colab'; bt.dataset.acao = 'colab';
  bt.title = 'Ligar dois chats para planejar e dividir o trabalho';
  document.querySelector('.bd-barra').appendChild(bt);
  bt.onclick = () => abrir();
  const anterior = window.kcEv;
  window.kcEv = ev => {
    if (ev && ev.t === 'colab') {
      const faseAntes = estados[ev.id]?.fase;
      estados[ev.id] = ev.estado;
      if (dlg.open && atual === ev.id) render();
      if (ev.estado?.fase === 'execucao' && faseAntes !== 'execucao') pendente = ev.id;
      mostrarPendente();
      return;
    }
    anterior(ev);
    if (ev && ['abas', 'fios'].includes(ev.t)) mostrarPendente();
    if (ev && ev.t === 'fios' && dlg.open) carregar();
  };
  window.KC_COLAB = { abrir, estados };
})();
