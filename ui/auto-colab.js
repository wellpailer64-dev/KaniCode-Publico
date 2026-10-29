/* Auto-Colab: preferência global persistida; não interrompe as sessões já iniciadas. */
(() => {
  const bt = $('auto-colab');
  let mudando = false;
  const pintar = on => {
    bt.classList.toggle('on', !!on);
    bt.setAttribute('aria-checked', String(!!on));
    bt.querySelector('.auto-colab-estado').textContent = on ? 'Ligado' : 'Desligado';
  };
  const carregar = () => api().auto_colab(null).then(pintar).catch(() => {});
  bt.addEventListener('click', async () => {
    if (mudando) return;
    mudando = true; bt.disabled = true;
    try {
      const on = await api().auto_colab(bt.getAttribute('aria-checked') !== 'true');
      if (typeof on !== 'boolean') throw new Error('resposta inválida');
      pintar(on);
      bolha('sis', on ? 'Auto-Colab ligado: o modelo pode chamar outro modelo para dividir tarefas.' :
        'Auto-Colab desligado: novas chamadas automáticas estão desativadas.');
    } catch (e) { bolha('erro', 'Não deu para alterar o Auto-Colab.'); }
    finally { mudando = false; bt.disabled = false; }
  });
  const anterior = window.kcEv;
  window.kcEv = ev => {
    if (ev?.t === 'auto_colab') { pintar(ev.on); return; }
    anterior(ev);
  };
  window.addEventListener('pywebviewready', carregar);
  $('ferramentas-bt').addEventListener('click', carregar);
})();
