/* Saved observations only. Chart geometry never changes a reported KPI. */
(() => {
  'use strict';
  const dayMs = 86400000;
  let sequence = 0;
  const observers = new WeakMap();
  const observed = (value) => (typeof value === 'number' || typeof value === 'string' && value.trim() !== '')
    && Number.isFinite(Number(value)) && Number(value) >= 0;
  const stamp = (value) => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(value + 'T00:00:00Z'))
    && new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value;
  const shortDate = (value) => typeof value === 'string' ? value.slice(8, 10) + '/' + value.slice(5, 7) : '';
  const compact = (value) => new Intl.NumberFormat('vi-VN', {notation: 'compact', maximumSignificantDigits: 3}).format(value);
  const count = (value) => new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2}).format(value);

  function element(doc, tag, text, className) {
    const node = doc.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function svgNode(doc, tag, attributes = {}, text) {
    const node = doc.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function points(rows, first, last, key) {
    if (!stamp(first) || !stamp(last)) return [];
    const map = new Map((rows || []).map((row) => [row.date, row.values?.[key] ?? null]));
    const output = [], end = Date.parse(last + 'T00:00:00Z');
    for (let date = Date.parse(first + 'T00:00:00Z'); date <= end && output.length < 90; date += dayMs) {
      const day = new Date(date).toISOString().slice(0, 10), value = map.get(day);
      output.push({date: day, value: observed(value) ? value : null});
    }
    return output;
  }

  function scaleFor(maximum, integer = false) {
    if (!(maximum > 0)) return {max: 1, step: 1, ticks: [0, 1]};
    const raw = maximum / 4, power = 10 ** Math.floor(Math.log10(raw));
    const factor = [1, 2, 2.5, 5, 10].find((value) => value >= raw / power) || 10;
    const step = integer ? Math.max(1, Math.ceil(factor * power)) : factor * power;
    const upper = Math.ceil(maximum / step) * step;
    if (!Number.isFinite(upper)) return {max: maximum, step: maximum / 4, ticks: [0, maximum / 4, maximum / 2, maximum * .75, maximum]};
    const max = upper;
    const ticks = Array.from({length: Math.round(max / step) + 1}, (_, index) => index * step);
    return {max, step, ticks};
  }

  function renderSeries(target, current, options = {}) {
    if (!target) return false;
    observers.get(target)?.disconnect();
    const doc = target.ownerDocument;
    const format = options.format || ((value) => observed(value) ? count(value) : 'Chưa có số liệu');
    const isPosition = options.position === true, minimum = isPosition ? 1 : 0;
    const reading = (row) => ({...row, value: observed(row.value) && Number(row.value) >= minimum ? row.value : null});
    const rows = current.map(reading);
    const prior = (options.previous || []).map(reading);
    const hasPrevious = prior.some((row) => row.value !== null);
    const values = [...rows, ...prior].filter((row) => row.value !== null).map((row) => Number(row.value));
    if (!rows.some((row) => row.value !== null)) {
      target.replaceChildren(element(doc, 'p', 'Nguồn chưa cung cấp chuỗi ngày cho chỉ số này.', 'cd-chart-empty viz-empty'));
      return false;
    }
    const model = scaleFor(Math.max(...values) - minimum, isPosition || options.integer === true);
    const compactPanel = Boolean(target.closest('.cr-mini-chart, .sc-charts'));
    const viewWidth = compactPanel ? 620 : 880;
    const size = Math.max(rows.length, prior.length), left = 76, width = viewWidth - left - 30, top = 24;
    const height = compactPanel ? 164 : 194;
    const step = width / Math.max(1, size), x = (index) => left + (index + .5) * step;
    const y = (value) => top + (isPosition ? (Number(value) - minimum) / model.max : 1 - Number(value) / model.max) * height;
    const baseline = top + height;
    const shell = element(doc, 'div', undefined, 'viz-series');
    if (compactPanel) shell.classList.add('viz-series-compact');
    const toolbar = element(doc, 'div', undefined, 'viz-toolbar');
    const coverage = rows.filter((row) => row.value !== null).length;
    toolbar.append(element(doc, 'span', `${coverage}/${rows.length} mốc có số liệu`, 'viz-coverage'));
    let kind = isPosition || options.kind === 'line' ? 'line' : 'bar';
    if (!isPosition) {
      const toggles = element(doc, 'div', undefined, 'viz-toggle');
      toggles.setAttribute('role', 'group');
      toggles.setAttribute('aria-label', 'Dạng biểu đồ');
      const buttons = [];
      for (const [value, label, icon] of [['bar', 'Cột', 'bar_chart'], ['line', 'Đường', 'show_chart']]) {
        const button = element(doc, 'button', undefined);
        button.type = 'button';
        button.setAttribute('aria-pressed', String(kind === value));
        const mark = element(doc, 'span', icon, 'material-symbols-outlined');
        mark.setAttribute('aria-hidden', 'true');
        button.append(mark, doc.createTextNode(label));
        button.addEventListener('click', () => {
          kind = value;
          buttons.forEach((item) => item.button.setAttribute('aria-pressed', String(item.value === value)));
          draw();
        });
        buttons.push({value, button});
        toggles.append(button);
      }
      toolbar.append(toggles);
    }
    const plot = element(doc, 'div', undefined, 'viz-plot');
    const tooltip = element(doc, 'div', undefined, 'viz-tooltip');
    tooltip.hidden = true;
    tooltip.setAttribute('aria-hidden', 'true');
    const svg = svgNode(doc, 'svg', {viewBox: `0 0 ${viewWidth} ${baseline + 62}`, role: 'img', 'aria-label': options.title || 'Biểu đồ theo ngày'});
    plot.append(svg, tooltip);
    const readout = element(doc, 'output', 'Chọn một mốc để xem số liệu.', 'viz-readout');
    readout.setAttribute('aria-live', 'polite');
    shell.append(toolbar);
    if (options.legend && hasPrevious) {
      const legend = element(doc, 'div', undefined, 'viz-legend');
      legend.append(element(doc, 'span', 'Kỳ đang xem'), element(doc, 'span', 'Kỳ đối chiếu · theo thứ tự ngày'));
      shell.append(legend);
    }
    if (isPosition) shell.append(element(doc, 'p', 'Hạng 1 ở trên cùng. Đường đi lên là cải thiện vị trí.', 'viz-rank-guide'));
    shell.append(plot, readout);
    target.replaceChildren(shell);
    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(() => {
        const renderedWidth = svg.getBoundingClientRect().width;
        if (renderedWidth > 0) svg.style.setProperty('--viz-axis-size', 12 * viewWidth / renderedWidth + 'px');
      });
      observer.observe(svg);
      observers.set(target, observer);
    }

    function draw() {
      svg.replaceChildren();
      const gradientId = 'viz-gradient-' + (++sequence);
      const defs = svgNode(doc, 'defs');
      const gradient = svgNode(doc, 'linearGradient', {id: gradientId, x1: 0, y1: 0, x2: 0, y2: 1});
      gradient.append(svgNode(doc, 'stop', {offset: '0%', class: 'viz-gradient-top'}), svgNode(doc, 'stop', {offset: '100%', class: 'viz-gradient-bottom'}));
      defs.append(gradient); svg.append(defs);
      for (const offset of model.ticks) {
        const tick = minimum + offset;
        const yy = y(tick);
        svg.append(svgNode(doc, 'line', {x1: left, x2: left + width, y1: yy, y2: yy, class: offset === 0 ? 'viz-baseline' : 'cr-grid-line'}));
        const label = svgNode(doc, 'text', {x: left - 13, y: yy + 4, 'text-anchor': 'end', class: 'cr-axis'}, options.axisFormat ? options.axisFormat(tick) : compact(tick));
        label.append(svgNode(doc, 'title', {}, format(tick))); svg.append(label);
      }
      function line(series, className, area = false) {
        let segment = [];
        const flush = () => {
          if (segment.length > 1) {
            if (area && !isPosition) svg.append(svgNode(doc, 'polygon', {points: `${segment[0].split(',')[0]},${baseline} ${segment.join(' ')} ${segment[segment.length - 1].split(',')[0]},${baseline}`, class: 'viz-area'}));
            svg.append(svgNode(doc, 'polyline', {points: segment.join(' '), class: className}));
          }
          segment = [];
        };
        series.forEach((point, index) => {
          const previousDate = series[index - 1]?.date;
          if (index && options.maxGapDays && stamp(previousDate) && stamp(point.date)
              && (Date.parse(point.date) - Date.parse(previousDate)) / dayMs > options.maxGapDays) flush();
          if (point.value === null) flush(); else segment.push(x(index) + ',' + y(point.value));
        });
        flush();
      }
      if (kind === 'line') {
        if (hasPrevious) line(prior, 'pr-line-previous');
        line(rows, 'pr-line', true);
      }
      const cadence = Math.max(1, Math.ceil(size / 7));
      for (let index = 0; index < size; index += 1) {
        const point = rows[index] || {date: null, value: null}, previous = prior[index];
        const label = point.label || shortDate(point.date);
        const summary = (point.date ? label + ': ' + format(point.value) : 'Ngoài kỳ đang xem')
          + (previous ? ' · Đối chiếu ' + (previous.label || shortDate(previous.date)) + ': ' + format(previous.value) : '');
        const group = svgNode(doc, 'g', {class: 'cr-chart-point', tabindex: '0', role: 'img', 'aria-label': summary,
          'data-value': point.value ?? '', 'data-date': point.date || ''});
        group.append(svgNode(doc, 'title', {}, summary));
        group.append(svgNode(doc, 'line', {x1: x(index), x2: x(index), y1: top, y2: top + height, class: 'viz-crosshair'}));
        const column = Math.min(options.maxBarWidth || 28, step * (hasPrevious ? .31 : .62));
        if (kind === 'bar' && observed(previous?.value)) {
          if (Number(previous.value) === 0) group.append(svgNode(doc, 'circle', {cx: x(index) - column / 2 - 1, cy: y(0), r: 2.5, class: 'pr-zero-previous'}));
          else group.append(svgNode(doc, 'rect', {x: x(index) - column - 1, y: y(previous.value), width: column, height: baseline - y(previous.value), rx: Math.min(4, column / 3), class: 'viz-previous-bar'}));
        }
        if (point.value !== null) {
          if (kind === 'line' || Number(point.value) === 0) group.append(svgNode(doc, 'circle', {cx: x(index), cy: y(point.value), r: kind === 'line' ? 3.5 : 2.5, class: Number(point.value) === 0 ? 'pr-zero-dot' : 'pr-line-dot'}));
          else group.append(svgNode(doc, 'rect', {x: hasPrevious ? x(index) + 1 : x(index) - column / 2, y: y(point.value), width: column,
            height: baseline - y(point.value), rx: Math.min(4, column / 3), fill: `url(#${gradientId})`, style: `fill:url(#${gradientId})`, class: 'cr-bar'}));
        } else if (point.date && !isPosition) group.append(svgNode(doc, 'line', {x1: x(index) - 3, x2: x(index) + 3, y1: baseline, y2: baseline, class: 'cr-bar-missing'}));
        if (kind === 'line' && observed(previous?.value)) group.append(svgNode(doc, 'circle', {cx: x(index), cy: y(previous.value), r: 2.5, class: 'pr-zero-previous'}));
        if (index % cadence === 0 && size - index > Math.max(1, cadence / 2) || index === size - 1) {
          svg.append(svgNode(doc, 'text', {x: x(index), y: baseline + 29, 'text-anchor': 'middle', class: 'cr-axis'}, label || shortDate(previous?.date)));
        }
        group.append(svgNode(doc, 'rect', {x: left + index * step, y: top, width: step, height, fill: 'transparent', class: 'viz-hit'}));
        function show() {
          tooltip.replaceChildren(element(doc, 'strong', point.full_date || point.date || 'Kỳ đối chiếu'), element(doc, 'span', (options.title || 'Giá trị') + ' · ' + format(point.value)));
          if (previous) tooltip.append(element(doc, 'small', 'Đối chiếu ' + (previous.date || '') + ' · ' + format(previous.value)));
          tooltip.hidden = false;
          const visibleLeft = plot.scrollLeft, tooltipWidth = Math.min(260, plot.clientWidth - 16);
          const anchor = x(index) / viewWidth * svg.getBoundingClientRect().width;
          tooltip.style.maxWidth = tooltipWidth + 'px';
          tooltip.style.left = Math.max(visibleLeft + 8, Math.min(visibleLeft + plot.clientWidth - tooltipWidth - 8, anchor - tooltipWidth / 2)) + 'px';
          readout.textContent = summary;
          if (options.onRead) options.onRead((options.title ? options.title + ' · ' : '') + summary);
        }
        for (const event of ['pointerenter', 'focus', 'click']) group.addEventListener(event, show);
        for (const event of ['pointerleave', 'blur']) group.addEventListener(event, () => { tooltip.hidden = true; });
        group.addEventListener('keydown', (event) => { if (event.key === 'Escape') tooltip.hidden = true; });
        svg.append(group);
      }
    }
    draw();
    return hasPrevious;
  }

  function render(target, report, key, {kind = 'bar', onRead = null, compare = true} = {}) {
    if (!target) return false;
    const metric = report.metrics.find((item) => item.key === key);
    if (!metric || !report.snapshot) {
      target.replaceChildren(element(target.ownerDocument, 'p', 'Nguồn chưa cung cấp chuỗi ngày cho chỉ số này.', 'cd-chart-empty viz-empty'));
      return false;
    }
    const comparison = report.comparison, item = comparison?.items?.find((value) => value.key === key);
    const previous = compare && comparison?.status === 'ready' && item?.status === 'ready'
      ? points(comparison.daily, comparison.period?.start, comparison.period?.end, key) : [];
    return renderSeries(target, points(report.daily, report.snapshot.start_date, report.snapshot.end_date, key), {
      title: metric.label, kind, previous, onRead, integer: metric.unit === 'count',
      position: key === 'position',
      format: (value) => window.VioDataFormat.format(value, metric.unit, metric.currency || report.snapshot.currency),
      axisFormat: (value) => metric.unit === 'percent' ? compact(value * 100) + '%' : compact(value),
    });
  }

  function renderDonut(target, rows, {label = 'Tổng', format = count, emptyText = 'Chưa có dữ liệu phân bổ.', maxSlices = 5} = {}) {
    if (!target) return;
    const doc = target.ownerDocument;
    if (!rows.length || rows.some((row) => !observed(row.value))) {
      target.replaceChildren(element(doc, 'p', emptyText, 'viz-empty'));
      return;
    }
    function sumValues(values) {
      if (!values.some((value) => typeof value === 'string')) return values.reduce((sum, value) => sum + value, 0);
      const parts = values.map((value) => /^(\d+)(?:\.(\d+))?$/.exec(String(value)));
      if (parts.some((part) => !part)) return values.reduce((sum, value) => sum + Number(value), 0);
      const digits = Math.max(...parts.map((part) => (part[2] || '').length));
      const sum = parts.reduce((total, part) => total + BigInt(part[1] + (part[2] || '').padEnd(digits, '0')), 0n);
      const value = sum.toString().padStart(digits + 1, '0');
      return digits ? value.slice(0, -digits) + '.' + value.slice(-digits) : value;
    }
    const total = sumValues(rows.map((row) => row.value));
    if (!(Number(total) > 0) || !Number.isFinite(Number(total))) {
      target.replaceChildren(element(doc, 'p', Number(total) === 0 ? 'Các nhóm đều có giá trị 0 trong kỳ này.' : emptyText, 'viz-empty'));
      return;
    }
    const sorted = rows.filter((row) => Number(row.value) > 0).map((row) => ({...row})).sort((a, b) => Number(b.value) - Number(a.value));
    const limit = Number.isInteger(maxSlices) && maxSlices >= 5 && maxSlices <= 8 ? maxSlices : 5;
    const slices = sorted.length > limit ? [...sorted.slice(0, limit - 1), {label: 'Các nhóm còn lại', value: sumValues(sorted.slice(limit - 1).map((row) => row.value))}] : sorted;
    const wrapper = element(doc, 'div', undefined, 'viz-donut-layout');
    const svg = svgNode(doc, 'svg', {viewBox: '0 0 240 240', role: 'img', 'aria-label': label + ': ' + format(total), class: 'viz-donut'});
    svg.append(svgNode(doc, 'circle', {cx: 120, cy: 120, r: 84, class: 'viz-ring-track'}));
    const centerValue = svgNode(doc, 'text', {x: 120, y: 119, 'text-anchor': 'middle', class: 'viz-donut-value'}, compact(total));
    const centerLabel = svgNode(doc, 'text', {x: 120, y: 142, 'text-anchor': 'middle', class: 'viz-donut-label'}, label);
    const list = element(doc, 'ul', undefined, 'viz-donut-legend');
    let angle = -Math.PI / 2;
    slices.forEach((row, index) => {
      const share = row.value / total, end = angle + Math.PI * 2 * share;
      const xy = (a) => [120 + 84 * Math.cos(a), 120 + 84 * Math.sin(a)];
      const start = xy(angle), finish = xy(end);
      const arc = slices.length === 1 ? svgNode(doc, 'circle', {cx: 120, cy: 120, r: 84})
        : svgNode(doc, 'path', {d: `M${start.join(',')} A84 84 0 ${share > .5 ? 1 : 0} 1 ${finish.join(',')}`});
      const percentage = new Intl.NumberFormat('vi-VN', {style: 'percent', maximumFractionDigits: 1}).format(share);
      arc.setAttribute('class', 'viz-slice viz-color-' + index);
      arc.setAttribute('tabindex', '0');
      arc.setAttribute('role', 'img');
      arc.setAttribute('aria-label', row.label + ': ' + format(row.value) + ' · ' + percentage);
      arc.append(svgNode(doc, 'title', {}, row.label + ' · ' + format(row.value) + ' · ' + percentage));
      svg.append(arc);
      const item = element(doc, 'li', undefined, 'viz-legend-item viz-color-' + index);
      const swatch = element(doc, 'span', undefined, 'viz-swatch'); swatch.setAttribute('aria-hidden', 'true');
      item.append(swatch, element(doc, 'span', row.label, 'viz-legend-name'), element(doc, 'strong', format(row.value)), element(doc, 'small', percentage));
      function highlight() {
        wrapper.dataset.active = String(index);
        centerValue.textContent = compact(row.value); centerLabel.textContent = percentage;
      }
      function reset() { delete wrapper.dataset.active; centerValue.textContent = compact(total); centerLabel.textContent = label; }
      for (const event of ['pointerenter', 'focus']) arc.addEventListener(event, highlight);
      for (const event of ['pointerleave', 'blur']) arc.addEventListener(event, reset);
      item.addEventListener('pointerenter', highlight); item.addEventListener('pointerleave', reset);
      list.append(item); angle = end;
    });
    svg.append(centerValue, centerLabel); wrapper.append(svg, list); target.replaceChildren(wrapper);
  }

  function mount(root = document) {
    root.querySelectorAll('[data-viz-donut]').forEach((target) => {
      let rows;
      try { rows = JSON.parse(target.dataset.vizDonut); } catch { return; }
      const unit = target.dataset.vizUnit || 'count', currency = target.dataset.vizCurrency;
      renderDonut(target, rows, {label: target.dataset.vizLabel || 'Tổng',
        maxSlices: Number(target.dataset.vizMaxSlices || 5),
        format: (value) => window.VioDataFormat.format(value, unit, currency)});
    });
    root.querySelectorAll('[data-fc-plot]').forEach((target) => {
      const data = target.querySelector('script[type="application/json"]');
      if (!data) return;
      let rows;
      try { rows = JSON.parse(data.textContent); } catch { return; }
      renderSeries(target, rows, {title: target.dataset.fcPlot, integer: true, kind: 'bar'});
    });
    root.querySelectorAll('[data-viz-series]').forEach((target) => {
      const source = target.querySelector('script[type="application/json"]');
      if (!source) return;
      let model;
      try { model = JSON.parse(source.textContent); } catch { return; }
      renderSeries(target, model.rows, {title: model.label, kind: model.kind, previous: model.previous || [],
        integer: model.unit === 'count', legend: true, position: model.reverse_y === true,
        format: (value) => window.VioDataFormat.format(value, model.unit, model.currency),
        axisFormat: (value) => compact(model.unit === 'percent' ? value * 100 : value) + (model.unit === 'percent' ? '%' : ''),
      });
    });
  }
  window.VioReportCharts = Object.freeze({render, renderSeries, renderDonut, points, scaleFor, mount});
  mount();
})();
