/* Entrada com referências compactas; o textarea continua sendo a ponte de envio e rascunhos. */
(() => {
  const campo = document.getElementById('texto');
  if (!campo || !window.KCResposta) return;
  const editor = document.createElement('div');
  editor.id = 'texto-editor'; editor.contentEditable = 'true';
  editor.setAttribute('role', 'textbox'); editor.setAttribute('aria-multiline', 'true');
  editor.setAttribute('aria-label', 'Mensagem');
  campo.after(editor); campo.hidden = true;
  let sincronizando = false;
  function ler(no) {
    if (no.nodeType === Node.TEXT_NODE) return no.data;
    if (no.dataset?.referencia !== undefined) return no.dataset.referencia;
    if (no.nodeName === 'BR') return '\n';
    return [...no.childNodes].map((filho, i) =>
      (i && /^(DIV|P)$/.test(filho.nodeName) ? '\n' : '') + ler(filho)).join('');
  }
  function formatar(valor) {
    const molde = document.createElement('template');
    molde.innerHTML = KCResposta.mensagem(valor);
    for (const link of molde.content.querySelectorAll('.link-compacto')) {
      const chip = document.createElement('span');
      chip.className = 'link-compacto entrada-referencia'; chip.contentEditable = 'false';
      chip.dataset.referencia = link.dataset.abrirCaminho || link.getAttribute('href');
      // Mantém www. exatamente como foi colado, sem acrescentar protocolo ao pedido.
      if (link.title.startsWith('www.')) chip.dataset.referencia = link.title;
      chip.title = link.title; chip.append(...link.childNodes); link.replaceWith(chip);
    }
    return molde.innerHTML;
  }
  const valor = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value');
  Object.defineProperty(campo, 'value', {
    configurable: true,
    get() { return valor.get.call(campo); },
    set(v) {
      valor.set.call(campo, v);
      if (!sincronizando) editor.innerHTML = formatar(campo.value);
    }
  });
  campo.focus = () => editor.focus();
  function atributos() {
    editor.dataset.placeholder = campo.placeholder;
    editor.contentEditable = String(!campo.disabled);
    editor.setAttribute('aria-disabled', String(campo.disabled));
  }
  new MutationObserver(atributos).observe(campo, {attributes:true, attributeFilter:['placeholder','disabled']});
  editor.addEventListener('input', () => {
    sincronizando = true;
    campo.value = ler(editor);
    campo.dispatchEvent(new Event('input', {bubbles:true}));
    sincronizando = false;
  });
  editor.addEventListener('keydown', e => {
    if (e.isComposing || e.defaultPrevented) return;
    const copia = new KeyboardEvent('keydown', {key:e.key, code:e.code, shiftKey:e.shiftKey,
      ctrlKey:e.ctrlKey, altKey:e.altKey, metaKey:e.metaKey, bubbles:false, cancelable:true});
    campo.dispatchEvent(copia);
    if (copia.defaultPrevented) {
      e.preventDefault();
      if (e.key === 'Escape') e.stopPropagation();
    }
  });
  editor.addEventListener('paste', e => {
    if ([...(e.clipboardData?.items || [])].some(i => i.type.startsWith('image/'))) return;
    const colado = e.clipboardData?.getData('text/plain');
    if (!colado) return;
    e.preventDefault();
    document.execCommand('insertHTML', false, formatar(colado).replace(/\r?\n/g, '<br>'));
    const selecao = window.getSelection(), no = selecao.anchorNode;
    const chip = (no?.nodeType === Node.ELEMENT_NODE ? no : no?.parentElement)?.closest('.entrada-referencia');
    if (chip) {
      const fim = document.createRange(); fim.setStartAfter(chip); fim.collapse(true);
      selecao.removeAllRanges(); selecao.addRange(fim);
    }
  });
  function copiar(e) {
    const selecao = window.getSelection();
    if (!selecao.rangeCount || selecao.isCollapsed) return;
    const trecho = selecao.getRangeAt(0).cloneContents();
    e.clipboardData.setData('text/plain', ler(trecho)); e.preventDefault();
    if (e.type === 'cut') document.execCommand('delete');
  }
  editor.addEventListener('copy', copiar);
  editor.addEventListener('cut', copiar);
  editor.innerHTML = formatar(campo.value); atributos();
})();
