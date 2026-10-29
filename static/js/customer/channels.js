(() => {
  'use strict';
  const W = window.VioLibrary, {$, node} = W, initial = W.initial, params = new URLSearchParams(location.search);
  let group = initial.groups.some((g) => g.id === params.get('category')) ? params.get('category') : 'all', deepLink = params.get('channel');
  $('#library-search').value = (params.get('q') || '').slice(0, 150);
  if ([...$('#channels-status').options].some((o) => o.value === params.get('status'))) $('#channels-status').value = params.get('status');
  function open(id) {
    const channel = W.channel(id); if (!channel || !W.ready) return;
    W.preview(channel); W.url({channel: id});
    document.querySelectorAll('[data-channel-link]').forEach((a) => { if (a.dataset.channelLink === id) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current'); });
  }
  function render() {
    const channels = initial.channels.map((c) => W.channel(c.id)), counts = Object.fromEntries(Object.keys(W.labels).map((s) => [s, 0]));
    const words = W.fold($('#library-search').value.trim()).split(/\s+/).filter(Boolean), status = $('#channels-status').value;
    let shown = 0;
    for (const channel of channels) {
      const card = document.querySelector(`[data-channel-card="${channel.id}"]`);
      counts[channel.state] += 1; card.dataset.state = channel.state;
      card.querySelector('[data-card-state]').textContent = W.labels[channel.state];
      for (const metric of channel.metrics) {
        const value = channel.state === 'ready' ? W.format(metric.value, metric.unit) : '—';
        card.querySelector(`[data-value="${metric.key}"]`).textContent = value;
        card.querySelector(`[data-value="${metric.key}"]`).nextElementSibling.textContent = value === '—' ? 'Chưa có dữ liệu' : 'Trong kỳ';
      }
      const haystack = W.fold([channel.id.replaceAll('_', ' '), channel.name, channel.description, ...channel.topics].join(' '));
      const matches = (group === 'all' || channel.group === group) && (status === 'all' || channel.state === status) && words.every((q) => haystack.includes(q));
      card.hidden = !matches; if (matches) shown += 1;
    }
    $('#channels-health-counts').replaceChildren(...Object.entries(counts).map(([state, count]) => { const item = node('span', `${W.labels[state]} (${count})`); item.dataset.state = state; return item; }));
    $('#channels-health-description').textContent = counts.ready ? `${counts.ready}/9 kênh có số liệu trong kỳ. Kiểm tra phạm vi và cách ghi nhận của từng nguồn trước khi so sánh.` : 'Chưa có số liệu trong kỳ đang chọn. Bạn có thể xem cấu trúc phân tích của từng kênh trước khi kết nối dữ liệu.';
    $('#library-no-results').hidden = shown > 0; $('#library-result-count').textContent = `Hiển thị ${shown} / ${channels.length} kênh`;
    document.querySelectorAll('[data-library-group]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.libraryGroup === group)));
    if (deepLink && W.ready) { const id = deepLink; deepLink = null; if (initial.channels.some((c) => c.id === id)) open(id); }
  }
  function filter() { W.url({q: $('#library-search').value.trim(), category: group === 'all' ? '' : group, status: $('#channels-status').value === 'all' ? '' : $('#channels-status').value}); render(); }
  $('#library-search').addEventListener('input', filter); $('#channels-status').addEventListener('change', filter);
  document.querySelectorAll('[data-library-group]').forEach((b) => b.addEventListener('click', () => { group = b.dataset.libraryGroup; filter(); }));
  document.querySelectorAll('[data-open-channel]').forEach((b) => b.addEventListener('click', () => open(b.dataset.openChannel)));
  document.querySelectorAll('[data-channel-link]').forEach((link) => link.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault(); open(link.dataset.channelLink);
  }));
  $('#library-reset').addEventListener('click', () => { group = 'all'; $('#library-search').value = ''; $('#channels-status').value = 'all'; filter(); $('#library-search').focus(); });
  $('#library-preview').addEventListener('close', () => { W.url({channel: ''}); document.querySelectorAll('[data-channel-link]').forEach((a) => a.removeAttribute('aria-current')); });
  window.VioChannels = Object.freeze({getContext: W.context, render: W.accept});
  W.mount(render);
})();
