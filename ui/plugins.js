/* Configurações > Plugins: os plugins que o KaniCode achou (plugins_kc.py), ligar/desligar e conferir a conexão. */
(() => {
  const dlg = document.getElementById('plugins-dlg');
  const el = id => document.getElementById(id);
  const api = () => window.pywebview.api;
  const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function cartao(p) {
    const art = document.createElement('article');
    art.className = 'plugin' + (p.ligado ? ' ligado' : '');
    art.style.setProperty('--plugin-cor', p.cor);
    art.innerHTML = `<div class="plugin-topo"><span class="plugin-sigla">${esc(p.sigla)}</span>
        <div class="plugin-nome"><strong>${esc(p.nome)}</strong><small class="plugin-situacao">${p.erro ? esc(p.erro) : p.ligado ? 'Ligado' : 'Desligado'}</small></div>
        <label class="plugin-chave" title="Ligar ou desligar"><input type="checkbox" ${p.ligado ? 'checked' : ''}><span></span></label></div>
      <p class="plugin-desc">${esc(p.descricao)}</p>
      <details><summary>Para que serve e quem chama</summary><p class="plugin-serve">${esc(p.serve)}</p>${p.chamado_por.length ? `<b class="plugin-sub">Quem chama</b><ul>${p.chamado_por.map(c => `<li>${esc(c)}</li>`).join('')}</ul>` : ''}</details>
      ${p.comandos.length ? `<details><summary>Comandos</summary><code class="plugin-cli">py -3.13 "${esc(p.cli)}"</code><ul>${p.comandos.map(c => `<li><code>${esc(c.cmd)}</code>${c.faz ? ` <small>${esc(c.faz)}</small>` : ''}</li>`).join('')}</ul></details>` : ''}
      <div class="plugin-acoes">${p.verificar.length ? '<button class="plugin-testar">Verificar conexão</button>' : ''}<button class="plugin-pasta">Abrir pasta</button>${p.tambem_kanivete ? '<small>também no KANIVETE</small>' : ''}</div>`;
    const sit = art.querySelector('.plugin-situacao');
    if (p.icone) api().plugins_logo(p.id).then(u => {   // o logo do plugin no lugar da sigla
      if (!u) return;
      const img = new Image(); img.alt = ''; img.className = 'plugin-logo'; img.src = u;
      img.onload = () => art.querySelector('.plugin-sigla').replaceWith(img);
    }).catch(() => {});
    art.querySelector('input').addEventListener('change', async e => {
      try { const n = await api().plugins_ligar(p.id, e.target.checked); art.classList.toggle('ligado', n.ligado); sit.textContent = n.ligado ? 'Ligado' : 'Desligado'; resumo(); }
      catch (err) { sit.textContent = String(err.message || err); e.target.checked = !e.target.checked; }
    });
    const testar = art.querySelector('.plugin-testar');
    if (testar) testar.addEventListener('click', async () => {
      testar.disabled = true; sit.textContent = 'Verificando…';
      try { const r = await api().plugins_verificar(p.id); sit.textContent = r.conectado ? `Conectado${r.detalhe ? ' · ' + r.detalhe : ''}` : `Sem conexão${r.detalhe ? ': ' + r.detalhe : ''}`; art.classList.toggle('conectado', !!r.conectado); }
      catch (err) { sit.textContent = String(err.message || err); }
      finally { testar.disabled = false; }
    });
    art.querySelector('.plugin-pasta').addEventListener('click', () => api().plugins_pasta(p.id));
    return art;
  }
  function resumo() {
    const tot = el('plugins-lista').children.length, lig = el('plugins-lista').querySelectorAll('.plugin.ligado').length;
    el('plugins-resumo').textContent = tot ? `${tot} ${tot === 1 ? 'plugin' : 'plugins'} · ${lig} ${lig === 1 ? 'ligado' : 'ligados'}` : 'Nenhum plugin encontrado.';
  }
  async function abrir() {
    window.kaniConfiguracoesMenu?.(false);
    if (!dlg.open) dlg.showModal();
    el('plugins-resumo').textContent = 'Procurando plugins…';
    try {
      const lista = await api().plugins_listar();
      el('plugins-lista').replaceChildren(...lista.map(cartao)); resumo();
      el('plugins-lista').querySelectorAll('.plugin.ligado .plugin-testar').forEach(b => b.click());   // confere sozinho ao abrir
    } catch (e) { el('plugins-resumo').textContent = String(e.message || e); }
  }
  window.kaniPluginsAbrir = abrir;
  el('config-plugins').addEventListener('click', abrir);
  el('plugins-fechar').addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', e => { if (e.target === dlg && e.offsetX < 0) dlg.close(); });
})();
