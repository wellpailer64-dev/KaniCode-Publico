/* Painel Projeto no painel da direita (2026-10-22, pedido do Pailer: "igual no Codex"): Arquivos (árvore ao vivo com
   as marcas do git e busca), Alterações (o que mudou desde o último commit, +/−, diferença colorida) e leitura de
   arquivo e edição manual. Aberto, confere o projeto a cada 3 s. Largura arrastável. */
(() => {
  if (window.KC_MOVEL) return;
  const el = id => document.getElementById(id), api = () => window.pywebview.api;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const ST = { M: ['alterado', 'm'], A: ['novo', 'a'], '?': ['novo', 'a'], D: ['apagado', 'd'], R: ['renomeado', 'm'], '•': ['alterações dentro', 'p'] };
  const IC_PASTA = '<svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>';
  const IC_ARQ = '<svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/></svg>';

  const trilho = document.createElement('button'); trilho.id = 'proj-trilho';
  trilho.title = 'Projeto: arquivos e alterações'; trilho.setAttribute('aria-label', 'Projeto');
  trilho.setAttribute('aria-expanded', 'false'); trilho.setAttribute('aria-controls', 'proj-painel');
  trilho.innerHTML = '<span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg></span><span class="cont" id="proj-cont" hidden></span>';
  // no topo, ao lado do 🌐 (pedido do Pailer, 2026-10-26)
  const bolas = document.querySelector('.janela-bolas');
  if (bolas) bolas.parentNode.insertBefore(trilho, bolas); else el('atv-trilho').after(trilho);
  const painel = document.createElement('section'); painel.id = 'proj-painel'; painel.className = 'det';
  painel.setAttribute('aria-label', 'Projeto');
  painel.innerHTML = `<div class="pj-puxa" title="Arraste para mudar a largura"></div>
    <div class="cab"><div class="pj-abas" role="tablist"><button data-aba="arq" aria-selected="true">Arquivos</button><button data-aba="alt" aria-selected="false">Alterações <span id="pj-n"></span></button></div>
      <span class="esp"></span><button class="bt" id="pj-atualizar" title="Atualizar">↻</button><button class="bt" id="pj-fechar" aria-label="Recolher o projeto">»</button></div>
    <div class="pj-contexto" id="pj-contexto"></div>
    <div class="pj-busca"><input id="pj-filtro" placeholder="Filtrar arquivos…" spellcheck="false"></div>
    <div class="pj-rolo" id="pj-corpo"></div>
    <div class="pj-ver" id="pj-ver" hidden><div class="pj-ver-cab"><button class="bt" id="pj-voltar" title="Voltar">‹</button><b id="pj-ver-nome"></b>
      <span class="esp"></span><button class="bt" id="pj-editar" title="Editar este arquivo">Editar</button><button class="bt" id="pj-salvar" hidden>Salvar</button><button class="bt" id="pj-cancelar" hidden>Cancelar</button><button class="bt" id="pj-modo" title="Arquivo inteiro / só as diferenças" hidden>±</button><button class="bt" id="pj-citar" title="Citar na conversa">@</button><button class="bt" id="pj-abrir" title="Abrir no programa padrão">↗</button></div>
      <div class="pj-aviso" id="pj-aviso" role="status" hidden></div>
      <textarea id="pj-editor" class="pj-editor" aria-label="Código do arquivo" spellcheck="false" hidden></textarea>
      <div class="pj-codigo" id="pj-codigo"></div></div>`;
  el('atv').append(painel); painel.inert = true;

  const P = { aba: 'arq', abertas: new Set(['']), cache: {}, alt: null, ver: null, modo: 'diff', timer: 0, filtro: '', achados: null, raiz: '', contexto: null, edicao: null, geracao: 0 };

  const aviso = texto => { el('pj-aviso').textContent = texto; el('pj-aviso').hidden = !texto; };
  async function pedir(acao, arq = '', dados = null) {
    const contexto = P.contexto, geracao = P.geracao;
    const r = await api().projeto(acao, arq, { ...contexto, ...dados });
    return geracao === P.geracao ? r : null;
  }
  async function contexto() {
    const r = await api().projeto('contexto');
    if (!r || !r.ok || !r.raiz) return true;
    if (P.contexto && P.contexto.aba === r.aba && P.contexto.raiz === r.raiz) return true;
    if (P.edicao) {
      aviso('O projeto ativo mudou. Seu texto está mantido aqui. Volte à aba de origem para salvar ou cancele a edição.');
      return false;
    }
    P.geracao++; P.contexto = { aba: r.aba, raiz: r.raiz };
    P.cache = {}; P.abertas = new Set(['']); P.alt = null; P.achados = null;
    P.filtro = ''; el('pj-filtro').value = ''; P.raiz = r.nome;
    P.ver = null; el('pj-ver').hidden = true; el('pj-corpo').hidden = false;
    painel.querySelector('.pj-busca').hidden = false;
    el('pj-contexto').textContent = r.raiz; el('pj-contexto').title = r.raiz;
    return true;
  }

  // ── Arquivos ──
  async function pasta(sub) {
    const r = await pedir('arvore', sub);
    if (r && r.ok) { P.cache[sub] = r.itens; if (!sub) P.raiz = r.nome; }
    return r;
  }
  function linhaItem(it, nivel) {
    const [dica, cls] = ST[it.st] || ['', ''];
    const aberta = it.d && P.abertas.has(it.rel);
    return `<div class="pj-it${it.d ? ' dir' : ''}${aberta ? ' aberta' : ''}" data-rel="${esc(it.rel)}" data-d="${it.d ? 1 : 0}" style="padding-left:${8 + nivel * 14}px" title="${esc(it.rel)}">
      <span class="pj-seta">${it.d ? '›' : ''}</span><span class="pj-ic">${it.d ? IC_PASTA : IC_ARQ}</span><span class="pj-nome ${cls}">${esc(it.n)}</span>
      ${it.st ? `<span class="pj-st ${cls}" title="${dica}">${it.st === '•' ? '●' : it.st === '?' ? 'U' : it.st}</span>` : ''}</div>`;
  }
  function ramo(sub, nivel) {
    return (P.cache[sub] || []).map(it => linhaItem(it, nivel) + (it.d && P.abertas.has(it.rel) ? ramo(it.rel, nivel + 1) : '')).join('');
  }
  function desenharArq() {
    const c = el('pj-corpo');
    if (P.achados) {
      c.innerHTML = P.achados.itens.length ? P.achados.itens.map(a => {
        const i = a.rel.lastIndexOf('/'), [, cls] = ST[a.st] || ['', ''];
        return `<div class="pj-it" data-rel="${esc(a.rel)}" data-d="0" style="padding-left:8px" title="${esc(a.rel)}"><span class="pj-ic">${IC_ARQ}</span>
          <span class="pj-nome ${cls}">${esc(a.rel.slice(i + 1))}</span><span class="pj-dir">${esc(a.rel.slice(0, i + 1))}</span>${a.st ? `<span class="pj-st ${cls}">${a.st === '?' ? 'U' : a.st}</span>` : ''}</div>`;
      }).join('') + (P.achados.total > P.achados.itens.length ? `<p class="pj-nota">+ ${P.achados.total - P.achados.itens.length} outros</p>` : '')
        : '<p class="pj-nota">Nada com esse nome.</p>';
      return;
    }
    c.innerHTML = `<div class="pj-raiz">${esc(P.raiz)}</div>` + ramo('', 0);
  }
  async function atualizarArq() {
    if (P.edicao) return;
    if (P.filtro) {
      const r = await pedir('buscar', P.filtro);
      if (r && r.ok) { P.achados = r; if (!P.ver && P.aba === 'arq') desenharArq(); }
      return;
    }
    const subs = [...P.abertas];
    await Promise.all(subs.map(pasta));
    if (P.aba === 'arq' && !P.ver) desenharArq();
  }

  // ── Alterações ──
  function desenharAlt() {
    const c = el('pj-corpo'), a = P.alt;
    if (!a) { c.innerHTML = '<p class="pj-nota">Lendo…</p>'; return; }
    if (!a.ok) { c.innerHTML = `<p class="pj-nota">${esc(a.erro || 'Não consegui conferir as alterações.')}</p>`; return; }
    const f = P.filtro.toLowerCase(), itens = a.itens.filter(i => !f || i.arq.toLowerCase().includes(f));
    c.innerHTML = (a.cortado ? '<p class="pj-nota">Acompanhamento parcial: limite de arquivos ou tamanho atingido.</p>' : '') + `<div class="pj-ramo"><b>${esc(a.ramo)}</b>${a.frente ? ` · ${a.frente} commit${a.frente > 1 ? 's' : ''} para enviar` : ''}
      <span class="esp"></span><span class="mais">+${a.mais}</span> <span class="menos">−${a.menos}</span></div>` +
      (itens.length ? itens.map(i => {
        const k = i.arq.lastIndexOf('/'), [dica, cls] = ST[i.st] || ['', ''];
        return `<div class="pj-it" data-rel="${esc(i.arq)}" data-d="0" data-alt="1" style="padding-left:8px" title="${esc(i.arq)} · ${dica}">
          <span class="pj-ic">${IC_ARQ}</span><span class="pj-nome ${cls}">${esc(i.arq.slice(k + 1))}</span><span class="pj-dir">${esc(i.arq.slice(0, k + 1))}</span>
          <span class="pj-num">${i.mais ? `<span class="mais">+${i.mais}</span>` : ''}${i.menos ? ` <span class="menos">−${i.menos}</span>` : ''}</span>
          <span class="pj-st ${cls}">${i.st === '?' ? 'U' : i.st}</span></div>`;
      }).join('') : '<p class="pj-nota">Nenhuma alteração nesta referência.</p>');
  }
  async function atualizarAlt() {
    if (P.edicao) return;
    const r = await pedir('alteracoes');
    P.alt = r;
    const n = r && r.ok ? r.itens.length : 0;
    el('pj-n').textContent = n ? n : ''; el('proj-cont').textContent = n; el('proj-cont').hidden = !n;
    if (P.aba === 'alt' && !P.ver) desenharAlt();
    if (P.ver && P.ver.mudou !== estaAlterado(P.ver.rel)) abrir(P.ver.rel, true);   // o arquivo aberto mudou de estado
  }
  const estaAlterado = rel => !!(P.alt && P.alt.ok && P.alt.itens.some(i => i.arq === rel));

  // ── ver um arquivo / a diferença ──
  function blocoDiff(texto) {
    let a = 0, b = 0;
    return texto.split('\n').map(l => {
      const h = l.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)/);
      if (h) { a = +h[1]; b = +h[2]; return `<div class="pj-l h"><span class="n"></span><span class="n"></span><code>${esc(l)}</code></div>`; }
      if (l.startsWith('+')) return `<div class="pj-l mais"><span class="n"></span><span class="n">${b++}</span><code>${esc(l.slice(1))}</code></div>`;
      if (l.startsWith('-')) return `<div class="pj-l menos"><span class="n">${a++}</span><span class="n"></span><code>${esc(l.slice(1))}</code></div>`;
      if (l.startsWith('\\')) return '';
      return `<div class="pj-l"><span class="n">${a++}</span><span class="n">${b++}</span><code>${esc(l.slice(1))}</code></div>`;
    }).join('');
  }
  async function abrir(rel, quieto) {
    if (P.edicao) { aviso('Salve ou cancele a edição antes de abrir outro arquivo.'); return; }
    const geracao = P.geracao;
    const mudou = estaAlterado(rel), cod = el('pj-codigo'), topo = quieto ? cod.scrollTop : 0;
    P.ver = { rel, mudou };
    el('pj-ver').hidden = false; el('pj-corpo').hidden = true; painel.querySelector('.pj-busca').hidden = true;
    el('pj-ver-nome').textContent = rel.split('/').pop(); el('pj-ver-nome').title = rel;
    el('pj-modo').hidden = !mudou;
    const diff = mudou && P.modo === 'diff';
    if (!quieto) cod.innerHTML = '<p class="pj-nota">Lendo…</p>';
    const r = await pedir(diff ? 'diff' : 'ler', rel);
    if (geracao !== P.geracao || !P.ver || P.ver.rel !== rel || P.edicao) return;
    P.ver.assinatura = r && r.texto;
    el('pj-editar').hidden = !(r && r.ok && !r.binario);
    aviso('');
    if (!r || !r.ok) cod.innerHTML = `<p class="pj-nota">${esc((r && r.erro) || 'Não consegui ler.')}</p>`;
    else if (r.binario) cod.innerHTML = '<p class="pj-nota">Arquivo binário (imagem, áudio…): use ↗ para abrir.</p>';
    else if (diff) cod.innerHTML = `<div class="pj-diff">${blocoDiff(r.texto)}</div>` + (r.cortado ? '<p class="pj-nota">(cortado)</p>' : '');
    else cod.innerHTML = `<div class="pj-diff">${r.texto.split('\n').map((l, i) => `<div class="pj-l"><span class="n">${i + 1}</span><code>${esc(l)}</code></div>`).join('')}</div>`
      + (r.cortado ? '<p class="pj-nota">(mostrando o começo: arquivo grande)</p>' : '');
    cod.scrollTop = topo;
  }
  async function conferirAberto() {   // ao vivo: relê o arquivo aberto e só redesenha se mudou
    if (!P.ver || P.edicao) return;
    const diff = P.ver.mudou && P.modo === 'diff';
    const r = await pedir(diff ? 'diff' : 'ler', P.ver.rel);
    if (P.ver && r && r.ok && r.texto !== P.ver.assinatura) abrir(P.ver.rel, true);
  }
  function fecharVer() {
    if (P.edicao) { aviso('Salve ou cancele a edição antes de sair do arquivo.'); return; }
    P.ver = null; el('pj-ver').hidden = true; el('pj-corpo').hidden = false; painel.querySelector('.pj-busca').hidden = false;
    P.aba === 'alt' ? desenharAlt() : desenharArq();
  }

  function modoEdicao(ativo) {
    el('pj-editor').hidden = !ativo; el('pj-codigo').hidden = ativo;
    el('pj-salvar').hidden = !ativo; el('pj-cancelar').hidden = !ativo;
    el('pj-editar').hidden = ativo; el('pj-modo').disabled = ativo;
    el('pj-abrir').disabled = ativo;
  }
  el('pj-editar').addEventListener('click', async () => {
    if (!P.ver || P.edicao) return;
    const rel = P.ver.rel, geracao = P.geracao;
    const r = await pedir('ler', rel);
    if (geracao !== P.geracao || !P.ver || P.ver.rel !== rel) return;
    if (!r || !r.ok || !r.editavel) { aviso((r && r.erro) || 'Este arquivo não pode ser editado aqui (binário, grande ou fora de UTF-8).'); return; }
    P.edicao = { rel, versao: r.versao, crlf: r.texto.includes('\r\n') };
    el('pj-editor').value = r.texto; modoEdicao(true); aviso(''); el('pj-editor').focus();
  });
  el('pj-salvar').addEventListener('click', async () => {
    if (!P.edicao) return;
    const edicao = P.edicao;
    el('pj-salvar').disabled = true; el('pj-cancelar').disabled = true;
    try {
      let texto = el('pj-editor').value;
      if (edicao.crlf) texto = texto.replace(/\n/g, '\r\n');
      const r = await pedir('salvar', edicao.rel, { texto, versao: edicao.versao });
      if (!r || !r.ok) { aviso((r && r.erro) || 'Não consegui salvar. Seu texto foi mantido.'); return; }
      P.edicao = null; modoEdicao(false); P.modo = 'tudo';
      await abrir(edicao.rel); aviso('Arquivo salvo.'); await atualizarAlt();
    } catch (e) { aviso('Não consegui salvar: ' + e.message); }
    finally { el('pj-salvar').disabled = false; el('pj-cancelar').disabled = false; }
  });
  el('pj-cancelar').addEventListener('click', async () => {
    if (!P.edicao) return;
    const rel = P.edicao.rel;
    P.edicao = null; modoEdicao(false); aviso('');
    const anterior = P.geracao; await contexto();
    if (anterior === P.geracao) await abrir(rel); else await tique();
  });
  el('pj-editor').addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); e.stopPropagation(); el('pj-salvar').click(); }
    if (e.key === 'Tab') {
      e.preventDefault(); const t = e.target; t.setRangeText('  ', t.selectionStart, t.selectionEnd, 'end');
    }
  });

  // ── eventos ──
  el('pj-corpo').addEventListener('click', async e => {
    const it = e.target.closest('.pj-it'); if (!it) return;
    const rel = it.dataset.rel;
    if (it.dataset.d === '1') {
      if (P.abertas.has(rel)) P.abertas.delete(rel);
      else { P.abertas.add(rel); if (!P.cache[rel]) await pasta(rel); }
      desenharArq(); return;
    }
    if (it.dataset.alt) P.modo = 'diff';
    abrir(rel);
  });
  painel.querySelector('.pj-abas').addEventListener('click', e => {
    const b = e.target.closest('button[data-aba]'); if (!b) return;
    if (P.edicao) { aviso('Salve ou cancele a edição antes de trocar a visualização.'); return; }
    P.aba = b.dataset.aba;
    painel.querySelectorAll('.pj-abas button').forEach(x => x.setAttribute('aria-selected', String(x === b)));
    if (P.ver) fecharVer(); else P.aba === 'alt' ? desenharAlt() : desenharArq();
  });
  let tBusca = 0;
  el('pj-filtro').addEventListener('input', () => {
    P.filtro = el('pj-filtro').value.trim(); clearTimeout(tBusca);
    if (P.aba === 'alt') return desenharAlt();
    if (!P.filtro) { P.achados = null; return desenharArq(); }
    tBusca = setTimeout(async () => { const f = P.filtro, r = await pedir('buscar', f); if (!r || !r.ok || f !== P.filtro) return; P.achados = r; if (P.aba === 'arq' && !P.ver) desenharArq(); }, 220);
  });
  el('pj-voltar').addEventListener('click', fecharVer);
  el('pj-modo').addEventListener('click', () => { P.modo = P.modo === 'diff' ? 'tudo' : 'diff'; if (P.ver) abrir(P.ver.rel); });
  el('pj-abrir').addEventListener('click', async () => {
    if (!P.ver) return;
    const r = await pedir('ler', P.ver.rel);
    if (r && r.caminho) api().resposta_abrir_caminho(r.caminho);
  });
  el('pj-citar').addEventListener('click', () => {
    if (!P.ver) return;
    const t = el('texto'); t.value = (t.value && !/\s$/.test(t.value) ? t.value + ' ' : t.value) + P.ver.rel + ' ';
    t.dispatchEvent(new Event('input')); t.focus();
  });
  el('pj-atualizar').addEventListener('click', () => { P.cache = {}; tique(); });
  trilho.addEventListener('click', () => window.kaniPainelDireito(trilho.getAttribute('aria-expanded') !== 'true', 'projeto'));
  el('pj-fechar').addEventListener('click', () => window.kaniPainelDireito(false, 'projeto'));
  painel.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    e.stopPropagation();
    if (P.ver) fecharVer(); else { window.kaniPainelDireito(false, 'projeto'); trilho.focus(); }
  });

  // largura: arrastar a borda esquerda (guardada)
  const LARG = 'kc-projeto-largura2';
  painel.style.setProperty('--pj-w', (+localStorage.getItem(LARG) || 540) + 'px');
  painel.querySelector('.pj-puxa').addEventListener('pointerdown', e => {
    const x0 = e.clientX, w0 = painel.getBoundingClientRect().width, alvo = e.target;
    alvo.setPointerCapture(e.pointerId); painel.classList.add('puxando');
    const mexer = ev => painel.style.setProperty('--pj-w', Math.max(300, Math.min(1100, w0 + x0 - ev.clientX)) + 'px');
    const soltar = () => {
      alvo.removeEventListener('pointermove', mexer); painel.classList.remove('puxando');
      localStorage.setItem(LARG, parseInt(painel.style.getPropertyValue('--pj-w')));
    };
    alvo.addEventListener('pointermove', mexer); alvo.addEventListener('pointerup', soltar, { once: true });
  });

  let rodando = false;
  async function tique() {
    if (rodando || document.hidden) return;
    rodando = true;
    try { if (await contexto()) await Promise.all([atualizarAlt(), P.aba === 'arq' && !P.ver ? atualizarArq() : null, conferirAberto()]); }
    catch (e) { console.warn('projeto', e); }
    rodando = false;
  }
  new MutationObserver(() => {
    const aberto = trilho.getAttribute('aria-expanded') === 'true'; painel.inert = !aberto; clearInterval(P.timer);
    if (aberto) { tique(); P.timer = setInterval(tique, 3000); }
  }).observe(trilho, { attributes: true, attributeFilter: ['aria-expanded'] });
  // a contagem no trilho, mesmo fechado (leve: 1×/30 s)
  window.addEventListener('pywebviewready', () => { tique(); setInterval(() => { if (!document.hidden && painel.inert) tique(); }, 30000); });
  window.kcProjeto = { abrir: async rel => { window.kaniPainelDireito(true, 'projeto'); await contexto(); abrir(rel); }, atualizar: tique, P };
})();
