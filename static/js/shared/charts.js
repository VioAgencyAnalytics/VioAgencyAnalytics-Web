function ensureChart(elementId) {
  const container = document.getElementById(elementId);
  if (!container) return null;
  return echarts.init(container);
}

function renderRevenueTrend(chartData) {
  const chart = ensureChart('revenue-chart');
  if (!chart) return;

  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: chartData.labels || [] },
    yAxis: { type: 'value' },
    series: [{
      data: chartData.values || [],
      type: 'line',
      smooth: true,
      areaStyle: {},
      itemStyle: { color: '#2d6cdf' },
    }],
  };
  chart.setOption(option);
}

function renderChannelMix(chartData) {
  const chart = ensureChart('channel-chart');
  if (!chart) return;

  const option = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: '70%',
      data: (chartData.labels || []).map((label, index) => ({
        name: label,
        value: (chartData.values || [])[index] || 0,
      })),
    }],
  };
  chart.setOption(option);
}

function renderReportChart(series) {
  const chart = ensureChart('report-chart');
  if (!chart) return;

  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: series.labels || [] },
    yAxis: { type: 'value' },
    series: [{
      data: series.values || [],
      type: 'bar',
      itemStyle: { color: '#1cbf7a' },
    }],
  };
  chart.setOption(option);
}

window.dashboardCharts = {
  renderOverview: function (charts) {
    renderRevenueTrend(charts.revenue_trend || { labels: [], values: [] });
    renderChannelMix(charts.channel_mix || { labels: [], values: [] });
  },
  renderReportChart,
};

// Published reports use the same local chart entry point. The older ECharts
// functions above remain untouched; this renderer needs no CDN or global SDK.
window.dashboardCharts.renderBundleChart = function (container, chart) {
  const ns = 'http://www.w3.org/2000/svg';
  const colors = ['#0051aa', '#6845c5', '#15803d', '#a50058', '#727784', '#d08d18'];
  const surface = container.querySelector('.pb-chart-surface');
  const tooltip = container.querySelector('.pb-chart-tooltip');
  tooltip.hidden = true;
  const fmt = value => value === null ? 'Chưa có dữ liệu' : new Intl.NumberFormat('vi-VN', {maximumFractionDigits:12}).format(value);
  const make = (tag, attrs = {}, text = null) => {
    const node = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([key,value]) => node.setAttribute(key,String(value)));
    if (text !== null) node.textContent = text;
    return node;
  };
  const plotWidth = chart.kind === 'donut' ? 600 : Math.max(240, Math.min(900, surface.clientWidth || 600));
  const svg = make('svg', {viewBox:`0 0 ${plotWidth} 280`, role:'img', 'aria-label':chart.title});
  svg.appendChild(make('title', {}, chart.title));
  surface.replaceChildren(svg);
  const values = chart.values, labels = chart.labels;
  if (!values.length || values.every(v => v === null)) { surface.textContent = 'Chưa có dữ liệu biểu đồ.'; return; }
  function interactive(node, index) {
    const description = `${labels[index]}${chart.timezone ? ' ' + chart.timezone : ''}: ${fmt(values[index])} ${chart.unit || ''}`;
    node.setAttribute('tabindex','0'); node.setAttribute('role','img'); node.setAttribute('aria-label', description);
    node.appendChild(make('title', {}, description));
    const show = () => { tooltip.textContent = `${description}\nNguồn: ${chart.source}`; tooltip.hidden = false; };
    const hide = () => { tooltip.hidden = true; };
    node.addEventListener('pointerenter',show); node.addEventListener('focus',show);
    node.addEventListener('pointerleave',hide); node.addEventListener('blur',hide);
    svg.appendChild(node);
  }
  if (chart.kind === 'donut') {
    if (values.some(v => v === null || v < 0) || !values.some(v => v > 0)) { surface.textContent = 'Dữ liệu chưa phù hợp cho biểu đồ tỷ trọng.'; return; }
    // The sum is used solely for arc geometry, never surfaced as a new KPI.
    const total = values.reduce((a,b) => a+b,0), radius = 88, circumference = 2*Math.PI*radius;
    let offset = 0;
    values.forEach((value,i) => {
      const length = value / total * circumference;
      interactive(make('circle',{cx:300,cy:130,r:radius,fill:'none',stroke:colors[i%colors.length],'stroke-width':32,
        'stroke-dasharray':`${length} ${circumference-length}`,'stroke-dashoffset':-offset,transform:'rotate(-90 300 130)'}),i);
      offset += length;
    });
  } else {
    const finite = values.filter(v => v !== null), low = Math.min(0,...finite), high = Math.max(0,...finite);
    const spread = high-low || 1;
    const axisNumber = value => new Intl.NumberFormat('vi-VN', {notation:'compact', maximumSignificantDigits:3}).format(value);
    const divisions = chart.integer_axis ? Math.min(4, Math.max(1, Math.ceil(spread))) : 3;
    const ticksY = [...new Set(Array.from({length:divisions+1}, (_, i) => chart.integer_axis ? Math.round(low+spread*i/divisions) : low+spread*i/divisions))];
    // Reserve space for the actual tick text, including thousands and negatives.
    const left = Math.max(56, ...ticksY.map(value => axisNumber(value).length * 8 + 20));
    const right = plotWidth-16, top = 24, bottom = 224;
    const y = value => bottom-(value-low)/spread*(bottom-top);
    const x = i => chart.kind === 'bar' ? left+(i+.5)*(right-left)/values.length : values.length === 1 ? (left+right)/2 : left+i*(right-left)/(values.length-1);
    for (const value of ticksY) {
      svg.appendChild(make('line',{x1:left,x2:right,y1:y(value),y2:y(value),stroke:'#e9edf8'}));
      svg.appendChild(make('text',{x:left-12,y:y(value)+4,'text-anchor':'end',fill:'#64748b','font-size':12},axisNumber(value)));
    }
    if (chart.kind === 'line') {
      let path = '', connected = false;
      values.forEach((value,i) => { if (value === null) { connected=false; return; } path += `${connected?'L':'M'}${x(i)},${y(value)} `; connected=true; });
      svg.appendChild(make('path',{d:path,fill:'none',stroke:colors[0],'stroke-width':2.5,'stroke-linejoin':'round'}));
    }
    values.forEach((value,i) => {
      if (value === null) return;
      const node = chart.kind === 'bar' ? make('rect',{x:x(i)-(right-left)/values.length*.32,y:Math.min(y(0),y(value)),
        width:(right-left)/values.length*.64,height:Math.max(1,Math.abs(y(value)-y(0))),rx:3,fill:colors[0]}) : make('circle',{cx:x(i),cy:y(value),r:4,fill:colors[0]});
      interactive(node,i);
    });
    // Fewer axis labels leave room for readable dates. All points and their
    // complete labels remain available through pointer and keyboard tooltips.
    const dateLabel = label => /^\d{4}-\d{2}-\d{2}(?:T|$)/.test(label) ? label.slice(8,10)+'/'+label.slice(5,7) : label.length > 18 ? label.slice(0,16)+'…' : label;
    const ticks = plotWidth < 500 || labels.some(label => dateLabel(label).length > 8) ? [0,.5,1] : [0,.25,.5,.75,1];
    const indices = [...new Set(ticks.map(v => Math.round(v*(labels.length-1))))];
    indices.forEach((i, tick) => svg.appendChild(make('text',{x:x(i),y:250,
      'text-anchor':indices.length === 1 ? 'middle' : tick === 0 ? 'start' : tick === indices.length-1 ? 'end' : 'middle',
      fill:'#64748b','font-size':12},dateLabel(labels[i]))));
  }
  const legend = document.createElement('div'); legend.className='pb-chart-legend';
  (chart.kind === 'donut' ? labels : [chart.title]).forEach((label,i) => {
    const span = document.createElement('span'), swatch = make('svg',{viewBox:'0 0 10 10','aria-hidden':'true'});
    swatch.appendChild(make('circle',{cx:5,cy:5,r:5,fill:colors[i%colors.length]})); span.appendChild(swatch);
    span.appendChild(document.createTextNode(chart.kind === 'donut' ? `${label}: ${fmt(values[i])} ${chart.unit || ''}` : label)); legend.appendChild(span);
  });
  surface.appendChild(legend);
};
