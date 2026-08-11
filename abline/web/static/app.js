/* AB Line Platform — browser client.
 *
 * No framework and no build step: this has to be servable from a laptop in an
 * office with no npm and no CDN reachable. State is four arrays and a couple of
 * selected ids, which is small enough that re-rendering a section wholesale is
 * simpler and faster than tracking diffs.
 */

'use strict';

const state = {
  monitors: [],
  monitorsByKey: {},
  machines: [],
  fields: [],
  lines: [],
  selectedFieldId: null,
  selectedLineId: null,
  producer: { catalog: [], machineId: null, lineIds: new Set() },
};

/* ------------------------------------------------------------------ utils */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'html') node.innerHTML = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value === true) node.setAttribute(key, '');
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

let toastTimer = null;
function toast(message, bad = false) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.toggle('bad', bad);
  node.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove('show'), bad ? 7000 : 3500);
}

/* The API reports failures as {detail: "..."}; surfacing that text verbatim is
 * the whole point of writing careful messages on the server. */
async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (response.status === 204) return null;
  const type = response.headers.get('content-type') || '';
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    if (type.includes('json')) {
      try {
        const body = await response.json();
        if (body.detail) {
          detail = typeof body.detail === 'string'
            ? body.detail
            : body.detail.map(d => d.msg || JSON.stringify(d)).join('; ');
        }
      } catch { /* keep the status text */ }
    }
    throw new Error(detail);
  }
  return type.includes('json') ? response.json() : response;
}

function fmt(value, digits = 2) {
  return value === null || value === undefined ? '—' : Number(value).toFixed(digits);
}

function parsePoints(text) {
  return text.split('\n')
    .map(row => row.trim())
    .filter(Boolean)
    .map((row, i) => {
      const parts = row.split(/[,;\s]+/).filter(Boolean).map(Number);
      if (parts.length < 2 || parts.some(Number.isNaN)) {
        throw new Error(`line ${i + 1} (${row}) is not a "lat, lon" pair`);
      }
      return [parts[0], parts[1]];
    });
}

/* ------------------------------------------------------------------- boot */

async function boot() {
  try {
    const catalog = await api('/api/catalog/monitors');
    state.monitors = catalog.monitors;
    for (const monitor of catalog.monitors) state.monitorsByKey[monitor.key] = monitor;
    fillMonitorSelect();
  } catch (error) {
    toast(`Could not load the monitor catalog: ${error.message}`, true);
  }
  await refreshAll();
  wireTabs();
  wireForms();
}

async function refreshAll() {
  await Promise.all([refreshMachines(), refreshFields()]);
  refreshStats();
  if (state.selectedFieldId) await selectField(state.selectedFieldId);
}

async function refreshStats() {
  try {
    const health = await api('/api/health');
    $('#stats').textContent =
      `${health.machines} machines · ${health.fields} fields · ${health.lines} lines`;
  } catch { /* the header count is decoration; failing it must not block work */ }
}

/* --------------------------------------------------------------- machines */

function fillMonitorSelect() {
  const select = $('#machine-monitor');
  const byBrand = {};
  for (const monitor of state.monitors) (byBrand[monitor.brand] ||= []).push(monitor);
  for (const brand of Object.keys(byBrand).sort()) {
    const group = el('optgroup', { label: brand });
    for (const monitor of byBrand[brand]) {
      group.append(el('option', { value: monitor.key }, `${monitor.model} — ${monitor.support_headline}`));
    }
    select.append(group);
  }
  select.addEventListener('change', () => {
    const monitor = state.monitorsByKey[select.value];
    $('#monitor-note').textContent = monitor
      ? `${monitor.support_headline}. Primary format: ${monitor.formats[0]?.label || '—'}.`
      : '';
  });
}

async function refreshMachines() {
  state.machines = await api('/api/machines');
  const list = $('#machine-list');
  list.replaceChildren();
  if (!state.machines.length) {
    list.append(el('li', { class: 'empty' }, 'No machines yet'));
  }
  for (const machine of state.machines) {
    const monitor = state.monitorsByKey[machine.monitor_key];
    list.append(el('li', {},
      el('span', { class: 'grow' },
        el('span', { class: 'name' }, machine.name),
        el('span', { class: 'sub' },
          `${machine.working_width_m} m`,
          machine.overlap_m ? ` (${machine.effective_width_m} m spacing)` : '',
          monitor ? ` · ${monitor.label}` : ' · no display set')),
      monitor ? el('span', { class: `badge ${monitor.support}` }, monitor.support_headline) : null,
      el('button', {
        class: 'danger tiny',
        title: 'Delete machine',
        onclick: async (event) => {
          event.stopPropagation();
          if (!confirm(`Delete ${machine.name}? Its lines are kept but lose the machine label.`)) return;
          try {
            await api(`/api/machines/${machine.id}`, { method: 'DELETE' });
            toast(`Deleted ${machine.name}`);
            await refreshAll();
          } catch (error) { toast(error.message, true); }
        },
      }, '×'),
    ));
  }
  for (const select of $$('.machine-select')) {
    const previous = select.value;
    select.replaceChildren(el('option', { value: '' }, '-- select --'));
    for (const machine of state.machines) {
      select.append(el('option', { value: machine.id },
        `${machine.name} (${machine.working_width_m} m)`));
    }
    select.value = previous;
  }
}

/* ----------------------------------------------------------------- fields */

async function refreshFields() {
  state.fields = await api('/api/fields');
  const list = $('#field-list');
  list.replaceChildren();
  if (!state.fields.length) {
    list.append(el('li', { class: 'empty' }, 'No fields yet'));
  }
  for (const field of state.fields) {
    list.append(el('li', {
      class: field.id === state.selectedFieldId ? 'selected' : '',
      onclick: () => selectField(field.id),
    },
      el('span', { class: 'grow' },
        el('span', { class: 'name' }, field.name),
        el('span', { class: 'sub' },
          field.boundary.length ? `${fmt(field.area_ha)} ha` : 'no boundary',
          field.farm ? ` · ${field.farm}` : '')),
      el('button', {
        class: 'danger tiny',
        title: 'Delete field',
        onclick: async (event) => {
          event.stopPropagation();
          if (!confirm(`Delete ${field.name} and all of its lines?`)) return;
          try {
            await api(`/api/fields/${field.id}`, { method: 'DELETE' });
            if (state.selectedFieldId === field.id) state.selectedFieldId = null;
            toast(`Deleted ${field.name}`);
            await refreshAll();
          } catch (error) { toast(error.message, true); }
        },
      }, '×'),
    ));
  }
  for (const select of $$('.field-select')) {
    const previous = select.value;
    select.replaceChildren(el('option', { value: '' }, '-- do not save --'));
    for (const field of state.fields) select.append(el('option', { value: field.id }, field.name));
    select.value = previous;
  }
}

async function selectField(fieldId) {
  state.selectedFieldId = fieldId;
  const field = state.fields.find(f => f.id === fieldId);
  if (!field) return;

  $$('#field-list li').forEach(node => node.classList.remove('selected'));
  const index = state.fields.indexOf(field);
  const node = $$('#field-list li')[index];
  if (node) node.classList.add('selected');

  $('#field-title').textContent = field.name;
  $('#field-sub').textContent = [
    field.farm && `Farm: ${field.farm}`,
    field.grower && `Grower: ${field.grower}`,
    field.boundary.length ? `${fmt(field.area_ha)} ha` : 'No boundary — import one to generate from shape',
  ].filter(Boolean).join(' · ');
  $('#field-body').hidden = false;

  state.lines = await api(`/api/lines?field_id=${encodeURIComponent(fieldId)}`);
  renderLines(field);
  drawMap(field, null);
  if (state.lines.length) previewLine(state.lines[0].id);
}

function renderLines(field) {
  const host = $('#line-list');
  host.replaceChildren();
  if (!state.lines.length) {
    host.append(el('p', { class: 'hint' }, 'No lines yet. Generate one from the boundary, fit one from machine data, or enter A/B by hand.'));
    return;
  }
  for (const line of state.lines) {
    host.append(el('div', { class: 'lineitem' },
      el('span', { class: 'grow' },
        el('span', { class: 'name' }, line.name || 'Line'),
        el('span', { class: 'sub' },
          `${line.pattern} · ${line.swath_width_m} m`,
          line.heading_deg !== null ? ` · ${fmt(line.heading_deg)}° true` : '',
          ` · from ${line.source}`,
          line.source_detail ? ` — ${line.source_detail}` : '')),
      line.confidence && line.confidence !== 'ok'
        ? el('span', { class: `badge ${line.confidence}` }, line.confidence) : null,
      el('button', { class: 'tiny', onclick: () => previewLine(line.id) }, 'Preview'),
      el('button', {
        class: 'danger tiny',
        onclick: async () => {
          if (!confirm(`Delete line "${line.name}"?`)) return;
          try {
            await api(`/api/lines/${line.id}`, { method: 'DELETE' });
            toast('Line deleted');
            await selectField(field.id);
            refreshStats();
          } catch (error) { toast(error.message, true); }
        },
      }, '×'),
    ));
  }
}

async function previewLine(lineId) {
  state.selectedLineId = lineId;
  try {
    const preview = await api(`/api/lines/${lineId}/preview`);
    const field = preview.field || state.fields.find(f => f.id === state.selectedFieldId);
    drawMap(field, preview.swaths);
    const swaths = preview.swaths;
    $('#map-meta').replaceChildren(
      el('span', {}, 'Passes: ', el('b', {}, swaths.swath_count)),
      el('span', {}, 'Swath: ', el('b', {}, `${swaths.width_m} m`)),
      el('span', {}, 'Driven length: ', el('b', {}, `${(swaths.total_length_m / 1000).toFixed(2)} km`)),
      el('span', {}, 'Covered: ', el('b', {}, `${fmt(swaths.covered_ha)} ha`)),
      el('span', {}, 'Heading: ', el('b', {}, `${fmt(preview.line.heading_deg)}° true`)),
    );
  } catch (error) {
    toast(error.message, true);
  }
}

/* -------------------------------------------------------------------- map */

/* An equirectangular sketch scaled to the viewbox. This is a shape check, not
 * a map: no tiles, no projection library, nothing fetched from a network the
 * office may not have. */
function drawMap(field, swaths) {
  const svg = $('#map');
  svg.replaceChildren();
  const W = 800, H = 520, PAD = 24;

  const points = [];
  if (field && field.boundary) for (const ring of field.boundary) points.push(...ring);
  if (swaths) {
    for (const path of swaths.swaths) points.push(...path);
    points.push(...swaths.reference);
  }
  if (!points.length) {
    svg.append(svgEl('text', { x: W / 2, y: H / 2, 'text-anchor': 'middle', class: 'empty-note' },
      'No geometry to draw yet'));
    return;
  }

  const lats = points.map(p => p[0]);
  const lons = points.map(p => p[1]);
  const midLat = (Math.min(...lats) + Math.max(...lats)) / 2;
  // Longitude degrees shrink with latitude; without this the field is stretched
  // sideways and a square field looks like a rectangle.
  const kx = Math.cos(midLat * Math.PI / 180);
  const minX = Math.min(...lons) * kx, maxX = Math.max(...lons) * kx;
  const minY = Math.min(...lats), maxY = Math.max(...lats);
  const spanX = Math.max(maxX - minX, 1e-9), spanY = Math.max(maxY - minY, 1e-9);
  const scale = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY);
  const offX = (W - spanX * scale) / 2, offY = (H - spanY * scale) / 2;

  const project = ([lat, lon]) => [
    offX + (lon * kx - minX) * scale,
    // SVG y grows downward, so north has to be flipped.
    H - (offY + (lat - minY) * scale),
  ];
  const pathOf = coords => coords.map(project).map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join('');

  if (field && field.boundary) {
    for (const ring of field.boundary) {
      if (ring.length >= 3) svg.append(svgEl('path', { class: 'boundary', d: pathOf(ring) + 'Z' }));
    }
  }
  if (swaths) {
    for (const path of swaths.swaths) {
      if (path.length >= 2) svg.append(svgEl('path', { class: 'pass', d: pathOf(path) }));
    }
    if (swaths.reference.length >= 2) {
      svg.append(svgEl('path', { class: 'ref', d: pathOf(swaths.reference) }));
    }
  }
}

function svgEl(tag, attrs = {}, ...children) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  for (const child of children) node.append(child);
  return node;
}

/* ------------------------------------------------------------------ forms */

function wireTabs() {
  for (const tab of $$('.tab')) {
    tab.addEventListener('click', () => {
      $$('.tab').forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      const which = tab.dataset.tab;
      $('#panel-guide').classList.toggle('active', which === 'guide');
      $('#panel-ops').classList.toggle('active', which === 'ops');
      $('#panel-producer').classList.toggle('active', which === 'producer');
      if (which === 'producer') loadProducer();
      if (which === 'ops') loadCoverage();
    });
  }
}

function wireForms() {
  $('#machine-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    try {
      await api('/api/machines', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          ...data,
          working_width_m: Number(data.working_width_m),
          overlap_m: Number(data.overlap_m || 0),
          lateral_offset_m: Number(data.lateral_offset_m || 0),
        }),
      });
      event.target.reset();
      toast('Machine added');
      await refreshMachines();
      refreshStats();
    } catch (error) { toast(error.message, true); }
  });

  $('#field-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    try {
      const boundary = data.boundary.trim() ? [parsePoints(data.boundary)] : [];
      await api('/api/fields', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: data.name, farm: data.farm, grower: data.grower, boundary }),
      });
      event.target.reset();
      toast('Field added');
      await refreshFields();
      refreshStats();
    } catch (error) { toast(error.message, true); }
  });

  $('#import-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    form.set('persist', form.get('persist') ? 'true' : 'false');
    const host = $('#import-result');
    host.className = 'result';
    host.textContent = 'Reading…';
    try {
      const result = await api('/api/import', { method: 'POST', body: form });
      host.replaceChildren(
        el('div', {}, `Detected: ${result.detected_format}`),
        el('div', {}, `${result.fields.length} field(s), ${result.lines.length} line(s), ${result.track_points} track point(s)`),
        result.persisted ? el('div', {}, `Saved ${result.persisted.fields} field(s) and ${result.persisted.lines} line(s).`) : null,
        result.warnings.length ? el('ul', {}, result.warnings.map(w => el('li', {}, w))) : null,
      );
      if (result.warnings.length) host.className = 'result warn';
      await refreshAll();
    } catch (error) {
      host.className = 'result bad';
      host.textContent = error.message;
    }
  });

  $('#fit-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    form.set('persist', form.get('field_id') ? 'true' : 'false');
    const host = $('#fit-result');
    host.className = 'result';
    host.textContent = 'Fitting…';
    try {
      const result = await api('/api/fit', { method: 'POST', body: form });
      const diag = result.diagnostics;
      host.className = result.warnings.length ? 'result warn' : 'result';
      host.replaceChildren(
        el('div', {}, el('b', {}, `${result.line.pattern} line, confidence ${result.confidence}`)),
        el('dl', {},
          el('dt', {}, 'Passes found'), el('dd', {}, result.pass_count),
          el('dt', {}, 'Dominant heading'), el('dd', {}, `${fmt(diag.dominant_heading_deg)}° `),
          el('dt', {}, 'On-heading travel'), el('dd', {}, `${(diag.heading_concentration * 100).toFixed(0)}%`),
          el('dt', {}, 'Measured spacing'), el('dd', {}, result.estimated_width_m ? `${result.estimated_width_m} m` : '—'),
          el('dt', {}, 'Longest pass'), el('dd', {}, `${diag.longest_pass_m} m`)),
        result.persisted ? el('div', {}, 'Saved to the selected field.') : el('div', {}, 'Not saved — pick a field to keep it.'),
        result.warnings.length ? el('ul', {}, result.warnings.map(w => el('li', {}, w))) : null,
      );
      if (result.persisted) await refreshAll();
      refreshStats();
    } catch (error) {
      host.className = 'result bad';
      host.textContent = error.message;
    }
  });

  $('#generate-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    try {
      const result = await api('/api/lines/from-boundary', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          field_id: state.selectedFieldId,
          machine_id: data.machine_id,
          strategy: data.strategy,
          headland_passes: Number(data.headland_passes || 0),
        }),
      });
      showHeading(result.heading);
      toast(`Created ${result.lines.length} line(s)`);
      await selectField(state.selectedFieldId);
      refreshStats();
    } catch (error) { toast(error.message, true); }
  });

  $('#btn-suggest').addEventListener('click', async () => {
    const data = Object.fromEntries(new FormData($('#generate-form')));
    if (!data.machine_id) return toast('Pick a machine first', true);
    try {
      const params = new URLSearchParams({ machine_id: data.machine_id, strategy: data.strategy });
      showHeading(await api(`/api/fields/${state.selectedFieldId}/heading?${params}`));
    } catch (error) { toast(error.message, true); }
  });

  $('#manual-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    try {
      await api('/api/lines', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          field_id: state.selectedFieldId,
          machine_id: data.machine_id,
          name: data.name,
          pattern: data.pattern,
          points: parsePoints(data.points),
          heading_deg: data.heading_deg ? Number(data.heading_deg) : null,
          radius_m: data.radius_m ? Number(data.radius_m) : null,
        }),
      });
      event.target.reset();
      toast('Line created');
      await selectField(state.selectedFieldId);
      refreshStats();
    } catch (error) { toast(error.message, true); }
  });
}

function showHeading(heading) {
  $('#heading-result').replaceChildren(
    el('dl', {},
      el('dt', {}, 'Heading'), el('dd', {}, `${fmt(heading.heading_deg)}° true`),
      el('dt', {}, 'Passes'), el('dd', {}, heading.pass_count),
      el('dt', {}, 'Driven segments'), el('dd', {}, heading.segment_count),
      el('dt', {}, 'Total length'), el('dd', {}, `${(heading.total_length_m / 1000).toFixed(2)} km`),
      el('dt', {}, 'Strategy'), el('dd', {}, `${heading.strategy} (${heading.headings_considered} headings scored)`)),
  );
}

/* --------------------------------------------------------------- producer */

async function loadProducer() {
  try {
    const result = await api('/api/producer/catalog');
    state.producer.catalog = result.machines;
    renderProducerMachines();
  } catch (error) { toast(error.message, true); }
}

function renderProducerMachines() {
  const host = $('#producer-machines');
  host.replaceChildren();
  if (!state.producer.catalog.length) {
    host.append(el('p', { class: 'hint' },
      'Nothing published yet. Once the office publishes lines for a machine, it shows up here.'));
    return;
  }
  for (const entry of state.producer.catalog) {
    const lineCount = entry.fields.reduce((sum, field) => sum + field.lines.length, 0);
    host.append(el('button', {
      class: `mcard ${entry.machine_id === state.producer.machineId ? 'selected' : ''}`,
      onclick: () => {
        state.producer.machineId = entry.machine_id;
        state.producer.lineIds = new Set();
        renderProducerMachines();
        renderProducerLines();
      },
    },
      el('span', { class: 'mname' }, entry.machine_name),
      el('span', { class: 'mmeta' }, [entry.brand, entry.category].filter(Boolean).join(' · ')),
      el('span', { class: 'mwidth' }, `${entry.working_width_m} m`),
      el('span', { class: 'mmeta' },
        `${lineCount} line${lineCount === 1 ? '' : 's'} · ${entry.monitor ? entry.monitor.label : 'no display set'}`),
    ));
  }
}

function renderProducerLines() {
  const entry = state.producer.catalog.find(m => m.machine_id === state.producer.machineId);
  const host = $('#producer-lines');
  host.replaceChildren();
  $('#step-lines').hidden = !entry;
  $('#step-download').hidden = true;
  if (!entry) return;

  for (const field of entry.fields) {
    const block = el('div', { class: 'fieldblock' },
      el('h3', {}, field.field_name),
      el('div', { class: 'sub' }, [field.farm, field.grower].filter(Boolean).join(' · ') || 'No farm recorded'));
    for (const line of field.lines) {
      const id = `pick-${line.line_id}`;
      block.append(el('label', { class: 'pick', for: id },
        el('input', {
          type: 'checkbox', id, value: line.line_id,
          onchange: (event) => {
            if (event.target.checked) state.producer.lineIds.add(line.line_id);
            else state.producer.lineIds.delete(line.line_id);
            renderProducerDownload();
          },
        }),
        el('span', { class: 'grow' },
          el('span', { class: 'name' }, line.name),
          el('span', { class: 'sub' }, ` — ${line.pattern}, ${line.swath_width_m} m swath`)),
        line.confidence && line.confidence !== 'ok'
          ? el('span', { class: `badge ${line.confidence}` }, line.confidence) : null,
      ));
    }
    host.append(block);
  }
}

function renderProducerDownload() {
  const host = $('#producer-download');
  const entry = state.producer.catalog.find(m => m.machine_id === state.producer.machineId);
  const chosen = Array.from(state.producer.lineIds);
  $('#step-download').hidden = !(entry && chosen.length);
  if (!entry || !chosen.length) return;

  const monitor = entry.monitor;
  host.replaceChildren();

  if (!monitor) {
    host.append(el('div', { class: 'dlcard' },
      el('div', { class: 'callout bad' },
        entry.monitor_warning || 'No display set for this machine, so we cannot pick a file format.')));
    return;
  }

  const card = el('div', { class: 'dlcard' },
    el('div', { class: 'big' }, `${chosen.length} line${chosen.length === 1 ? '' : 's'} for your ${monitor.label}`),
    el('div', { class: 'fmt' }, `Format: ${monitor.formats[0]?.label || '—'}`),
  );

  const calloutClass =
    monitor.support === 'native' ? 'callout good'
      : monitor.support === 'api_only' ? 'callout bad' : 'callout';
  card.append(el('div', { class: calloutClass },
    monitor.support === 'desktop_bridge'
      ? `Heads up: ${monitor.brand}'s guidance format is closed, so this is a two-step import — the file goes into ${monitor.brand}'s own software first, and that writes the file your display reads. The steps below cover both halves.`
      : monitor.support === 'needs_sample'
        ? 'Heads up: we have the folder layout from the manual but have not confirmed the file contents against a real machine. A shapefile copy is included as a fallback.'
        : monitor.support === 'structural'
          ? 'This imports directly. Menu wording moves between software versions — if the steps do not match your screen, look for the equivalent import option.'
          : 'This imports directly. Copy it to a USB stick and import.'));

  card.append(el('button', {
    class: 'primary',
    onclick: async (event) => {
      const button = event.target;
      button.disabled = true;
      button.textContent = 'Building…';
      try {
        const response = await fetch('/api/download', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            monitor_key: monitor.key,
            line_ids: chosen,
            machine_id: entry.machine_id,
          }),
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || `${response.status} ${response.statusText}`);
        }
        const blob = await response.blob();
        const name = (response.headers.get('content-disposition') || '')
          .match(/filename="([^"]+)"/)?.[1] || 'ab-lines.zip';
        const url = URL.createObjectURL(blob);
        const anchor = el('a', { href: url, download: name });
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        toast('Downloaded. The instructions are inside as HOW-TO-IMPORT.txt.');
      } catch (error) {
        toast(error.message, true);
      } finally {
        button.disabled = false;
        button.textContent = 'Download AB lines';
      }
    },
  }, 'Download AB lines'));

  if (monitor.usb_path) {
    card.append(el('p', {}, el('b', {}, 'Where it goes on the stick: '), monitor.usb_path,
      ` — format the stick ${monitor.filesystem}.`));
  }
  if (monitor.steps.length) {
    card.append(el('h3', {}, 'Step by step'));
    card.append(el('ol', {}, monitor.steps.map(step => el('li', {}, step))));
  }
  if (monitor.guidance_vocabulary) {
    card.append(el('p', {}, el('b', {}, 'On this display an AB line is called: '), monitor.guidance_vocabulary));
  }
  if (monitor.common_errors.length) {
    card.append(el('h3', {}, 'Things that go wrong'));
    card.append(el('ul', {}, monitor.common_errors.map(item => el('li', {}, item))));
  }
  host.append(card);
}

/* ---------------------------------------------------------- coverage panel
 *
 * Shown on the operations tab because it is a work queue, not a sales figure:
 * the interesting column is what is missing.
 */

let coverageLoaded = false;

async function loadCoverage() {
  if (coverageLoaded) return;
  try {
    const data = await api('/api/guide/coverage');
    coverageLoaded = true;
    const s = data.summary;

    $('#coverage-summary').replaceChildren(
      el('span', {}, 'Procedures: ', el('b', {}, s.total)),
      el('span', {}, 'Displays: ', el('b', {}, s.monitors)),
      el('span', {}, 'Version-specific: ', el('b', {}, s.version_specific)),
      el('span', {}, 'Verified: ', el('b', {}, s.by_confidence.verified || 0)),
      el('span', {}, 'Cloud platforms: ', el('b', {}, data.cloud_platforms.length)),
    );

    const labels = {};
    for (const objective of data.objectives) labels[objective.key] = objective.label;

    const table = el('table', { class: 'covtable' },
      el('thead', {}, el('tr', {},
        el('th', {}, 'Display'),
        el('th', {}, 'Jobs'),
        el('th', {}, 'Routes'),
        el('th', {}, 'Not documented yet'))));
    const body = el('tbody', {});
    for (const monitor of data.monitors) {
      const complete = monitor.objectives === monitor.objectives_possible;
      body.append(el('tr', {},
        el('td', {},
          el('img', { class: 'covicon', src: monitor.icon_url, alt: '', loading: 'lazy' }),
          monitor.label),
        el('td', { class: complete ? 'ok' : '' },
          `${monitor.objectives}/${monitor.objectives_possible}`),
        el('td', {}, monitor.transports.join(', ')),
        el('td', { class: 'gaps' },
          monitor.missing.length
            ? monitor.missing.map(k => labels[k] || k).join(', ')
            : '\u2014')));
    }
    table.append(body);
    $('#coverage-table').replaceChildren(table);
  } catch (error) {
    $('#coverage-table').replaceChildren(
      el('p', { class: 'hint' }, `Could not load coverage: ${error.message}`));
  }
}

/* ============================================================== guide tab
 *
 * A six-step wizard. Each answer narrows the next, and choosing something
 * earlier in the chain clears everything after it -- a stale monitor selection
 * left over from a different brand is how you end up reading the wrong
 * procedure with no way to tell.
 */

const guide = {
  equipment: null,
  monitor: null,
  version: null,
  objective: null,
  transport: null,
  monitors: [],
  objectiveGroups: [],
};

const GUIDE_STEPS = ['equipment', 'monitor', 'version', 'objective', 'transport', 'result'];

function guideReset(from) {
  const index = GUIDE_STEPS.indexOf(from);
  for (const step of GUIDE_STEPS.slice(index)) {
    if (step !== 'result') guide[step] = null;
    const section = $(`#g-step-${step}`);
    if (section && step !== 'equipment') section.hidden = true;
  }
}

async function loadGuide() {
  try {
    const start = await api('/api/guide/start');
    const host = $('#g-equipment');
    host.replaceChildren();
    for (const kind of start.equipment_types) {
      host.append(el('button', {
        class: 'chip',
        onclick: () => selectEquipment(kind.key, kind.label),
      }, kind.label, el('span', { class: 'count' }, `${kind.monitor_count}`)));
    }
  } catch (error) {
    toast(`Could not load the guide: ${error.message}`, true);
  }
}

async function selectEquipment(key, label) {
  guide.equipment = key;
  guideReset('monitor');
  markSelected('#g-equipment', label);
  await showMonitors({ equipment: key });
}

async function showMonitors(params) {
  const query = new URLSearchParams(params);
  guide.monitors = await api(`/api/guide/monitors?${query}`);
  const host = $('#g-monitors');
  host.replaceChildren();
  if (!guide.monitors.length) {
    host.append(el('p', { class: 'hint' }, 'No displays recorded for that yet.'));
  }
  for (const monitor of guide.monitors) {
    host.append(el('button', {
      class: 'monitorcard',
      onclick: () => selectMonitor(monitor),
    },
      el('img', { src: monitor.icon_url, alt: '', loading: 'lazy' }),
      el('span', { class: 'mbrand' }, monitor.brand),
      el('span', { class: 'mname' }, monitor.model),
    ));
  }
  $('#g-step-monitor').hidden = false;
  $('#g-step-monitor').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function selectMonitor(monitor) {
  guide.monitor = monitor;
  guideReset('version');
  for (const card of $$('#g-monitors .monitorcard')) {
    card.classList.toggle('selected', card.querySelector('.mname').textContent === monitor.model);
  }

  const host = $('#g-versions');
  host.replaceChildren();
  for (const version of monitor.versions) {
    host.append(el('button', {
      class: 'chip stacked',
      onclick: () => selectVersion(version.key, version.label),
    }, version.label, version.notes ? el('span', { class: 'sub' }, version.notes) : null));
  }
  // Always offered last: an operator who cannot find the version number should
  // still reach an answer, just one flagged as generic.
  host.append(el('button', {
    class: 'chip stacked',
    onclick: () => selectVersion(null, 'I am not sure'),
  }, 'I am not sure', el('span', { class: 'sub' }, 'You will get the general steps')));

  $('#g-step-version').hidden = false;
  $('#g-step-version').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function selectVersion(key, label) {
  guideReset('objective');  // clears objective and transport, keeps the version
  guide.version = key;
  markSelected('#g-versions', label);

  const query = key ? `?version=${encodeURIComponent(key)}` : '';
  const data = await api(`/api/guide/monitors/${guide.monitor.key}/objectives${query}`);
  guide.objectiveGroups = data.groups;

  const host = $('#g-objectives');
  host.replaceChildren();
  for (const group of data.groups) {
    const block = el('div', { class: 'objgroup' }, el('h3', {}, group.direction_label));
    for (const objective of group.objectives) {
      block.append(el('button', {
        class: 'objcard',
        onclick: () => selectObjective(objective),
      },
        el('span', { class: 'oname' }, objective.label),
        el('span', { class: 'odesc' }, objective.description),
      ));
    }
    host.append(block);
  }
  $('#g-step-objective').hidden = false;
  $('#g-step-objective').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function selectObjective(objective) {
  guideReset('transport');  // clears transport, keeps the objective
  guide.objective = objective;
  for (const card of $$('#g-objectives .objcard')) {
    card.classList.toggle('selected', card.querySelector('.oname').textContent === objective.label);
  }

  const host = $('#g-transports');
  host.replaceChildren();
  for (const transport of objective.transports) {
    host.append(el('button', {
      class: 'chip stacked',
      onclick: () => selectTransport(transport.key, transport.label),
    }, transport.label, el('span', { class: 'sub' }, transport.description)));
  }
  $('#g-step-transport').hidden = false;

  // One route only: choosing it is not a decision, so make it for them.
  if (objective.transports.length === 1) {
    selectTransport(objective.transports[0].key, objective.transports[0].label);
  } else {
    $('#g-step-transport').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

async function selectTransport(key, label) {
  guide.transport = key;
  markSelected('#g-transports', label);
  const params = new URLSearchParams({
    monitor_key: guide.monitor.key,
    objective: guide.objective.key,
    transport: key,
  });
  if (guide.version) params.set('version', guide.version);
  try {
    renderProcedure(await api(`/api/guide/procedure?${params}`));
  } catch (error) {
    toast(error.message, true);
  }
}

function markSelected(selector, label) {
  for (const chip of $$(`${selector} .chip`)) {
    chip.classList.toggle('selected', chip.firstChild && chip.firstChild.textContent === label);
  }
}

function renderProcedure(data) {
  const host = $('#g-result');
  if (data.found && data.procedure) {
    history.replaceState(null, '', procedureHash(
      data.monitor.key, data.version_key,
      data.procedure.objective, data.procedure.transport));
  }
  host.replaceChildren();
  const section = $('#g-step-result');
  section.hidden = false;

  if (!data.found) {
    host.append(el('div', { class: 'proc' },
      el('div', { class: 'proc-body' },
        el('div', { class: 'panelbox warn' }, data.message),
        el('p', {}, 'Documented for this display:'),
        el('ul', { class: 'procnotes' },
          data.alternatives.map(a => el('li', {}, `${a.objective_label} — ${a.transport_label}`))))));
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  const p = data.procedure;
  const monitor = data.monitor;

  const badges = [
    el('span', { class: `badge ${p.confidence === 'verified' ? 'native' : 'needs_sample'}` },
      p.confidence_label),
    el('span', { class: 'badge' }, data.version_label),
    el('span', { class: 'badge' }, p.transport_label),
  ];

  const card = el('div', { class: 'proc' },
    el('div', { class: 'proc-head' },
      el('img', { src: monitor.icon_url, alt: '' }),
      el('div', { class: 'titles' },
        el('h3', {}, p.objective_label),
        el('div', { class: 'sub' }, `${monitor.label} · ${p.direction_label}`),
        el('div', { class: 'badges' }, badges)),
    ));

  const body = el('div', { class: 'proc-body' });

  if (!data.matched_version) {
    body.append(el('div', { class: 'panelbox warn' }, data.message));
  }

  const facts = el('dl', { class: 'facts' });
  const addFact = (label, value) => {
    if (!value) return;
    facts.append(el('div', {}, el('dt', {}, label), el('dd', {}, value)));
  };
  addFact('File format', p.file_format);
  if (p.extensions.length) addFact('Extensions', p.extensions.join('  '));
  if (p.media_path) {
    facts.append(el('div', {},
      el('dt', {}, 'Exactly where it goes'),
      el('dd', {}, el('code', {}, p.media_path))));
  }
  addFact('Format the stick as', p.filesystem);
  // A cloud route is useless advice without naming the portal to log into.
  addFact('Platform', p.platform);
  addFact('Allow about', `${p.minutes} minutes`);
  if (facts.children.length) {
    body.append(el('h4', {}, 'The file'), facts);
  }

  if (p.prerequisites.length) {
    body.append(el('h4', {}, 'Before you start'));
    body.append(el('div', { class: 'panelbox' },
      el('ul', { class: 'procnotes' }, p.prerequisites.map(x => el('li', {}, x)))));
  }

  body.append(el('h4', {}, 'Step by step'));
  body.append(el('ol', { class: 'procsteps' }, p.steps.map(s => el('li', {}, s))));

  if (p.verify.length) {
    body.append(el('h4', {}, 'Check it worked'));
    body.append(el('div', { class: 'panelbox good' },
      el('ul', { class: 'procnotes' }, p.verify.map(x => el('li', {}, x)))));
  }
  if (p.cautions.length) {
    body.append(el('h4', {}, 'Worth knowing'));
    body.append(el('div', { class: 'panelbox warn' },
      el('ul', { class: 'procnotes' }, p.cautions.map(x => el('li', {}, x)))));
  }
  if (p.common_errors.length) {
    body.append(el('h4', {}, 'What usually goes wrong'));
    body.append(el('div', { class: 'panelbox bad' },
      el('ul', { class: 'procnotes' }, p.common_errors.map(x => el('li', {}, x)))));
  }

  // What someone doing this usually needs next. The same trip to the machine
  // is the moment to also pull last week's work data off it.
  if (data.related && data.related.length) {
    body.append(el('h4', {}, 'While you are at the machine'));
    const list = el('div', { class: 'relatedgrid' });
    for (const item of data.related) {
      list.append(el('button', {
        class: 'relatedcard no-print',
        onclick: () => jumpTo(monitor, data.version_key, item.objective, item.transport),
      },
        el('span', { class: 'rname' }, item.objective_label),
        el('span', { class: 'rsub' }, item.transport_label)));
    }
    body.append(list);
  }

  const handbookUrl = `/handbook?monitor_key=${encodeURIComponent(monitor.key)}`
    + (data.version_key ? `&version=${encodeURIComponent(data.version_key)}` : '');

  body.append(el('div', { class: 'proc-actions no-print' },
    el('button', { class: 'primary', onclick: () => window.print() }, 'Print this procedure'),
    el('a', { class: 'btnlink', href: handbookUrl, target: '_blank', rel: 'noopener' },
      'Whole handbook for this display'),
    el('button', { class: 'ghost', onclick: copyLink }, 'Copy link to this procedure'),
    el('button', {
      class: 'ghost',
      onclick: () => {
        guideReset('equipment');
        $('#g-step-result').hidden = true;
        $$('#g-equipment .chip').forEach(c => c.classList.remove('selected'));
        history.replaceState(null, '', location.pathname);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    }, 'Start over')));

  card.append(body);
  if (p.sources.length) {
    card.append(el('div', { class: 'proc-foot' }, `Sources: ${p.sources.join(' · ')}`));
  }
  host.append(card);
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* Deep links.
 *
 * A procedure is the unit people share -- a dealer sends one to a producer, an
 * agronomist pastes one into a message. Encoding the four coordinates in the
 * URL fragment makes every answer addressable without a server round trip and
 * without a database of saved links.
 */

function procedureHash(monitorKey, version, objective, transport) {
  const parts = [`m=${monitorKey}`, `o=${objective}`, `t=${transport}`];
  if (version) parts.push(`v=${version}`);
  return '#' + parts.join('&');
}

function copyLink(event) {
  const url = location.href;
  const done = () => {
    const button = event.target;
    const original = button.textContent;
    button.textContent = 'Link copied';
    setTimeout(() => { button.textContent = original; }, 1800);
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(url).then(done, () => toast(url, false));
  } else {
    // Plain http on a farm office LAN has no clipboard API; show it instead so
    // it can still be copied by hand.
    toast(url);
  }
}

async function jumpTo(monitor, version, objectiveKey, transportKey) {
  guideReset('monitor');
  $('#g-step-monitor').hidden = false;
  $('#g-monitors').replaceChildren(el('button', { class: 'monitorcard selected' },
    el('img', { src: monitor.icon_url, alt: '' }),
    el('span', { class: 'mbrand' }, monitor.brand),
    el('span', { class: 'mname' }, monitor.model)));
  guide.monitors = [monitor];
  guide.monitor = monitor;

  await selectVersionByKey(monitor, version);
  const objective = findObjective(objectiveKey);
  if (!objective) return;
  selectObjective(objective);
  await selectTransport(transportKey, transportLabel(objective, transportKey));
}

function findObjective(key) {
  for (const group of guide.objectiveGroups) {
    const hit = group.objectives.find(o => o.key === key);
    if (hit) return hit;
  }
  return null;
}

function transportLabel(objective, key) {
  const hit = (objective.transports || []).find(t => t.key === key);
  return hit ? hit.label : key;
}

async function selectVersionByKey(monitor, versionKey) {
  const version = (monitor.versions || []).find(v => v.key === versionKey);
  selectMonitor(monitor);
  await selectVersion(version ? version.key : null,
                      version ? version.label : 'I am not sure');
}

async function restoreFromHash() {
  const raw = location.hash.replace(/^#/, '');
  if (!raw) return false;
  const params = new URLSearchParams(raw.replace(/&/g, '&'));
  const monitorKey = params.get('m');
  if (!monitorKey) return false;
  try {
    const monitor = await api(`/api/catalog/monitors/${encodeURIComponent(monitorKey)}`);
    const versions = await api(`/api/guide/monitors?brand=${encodeURIComponent(monitor.brand)}`);
    const full = versions.find(m => m.key === monitorKey) || monitor;
    const objectiveKey = params.get('o');
    const transportKey = params.get('t');
    if (!objectiveKey || !transportKey) {
      selectMonitor(full);
      return true;
    }
    await jumpTo(full, params.get('v'), objectiveKey, transportKey);
    return true;
  } catch (error) {
    toast(`That link did not resolve: ${error.message}`, true);
    return false;
  }
}

function wireGuideSearch() {
  const input = $('#guide-search');
  const results = $('#guide-search-results');
  let timer = null;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = input.value.trim();
      if (q.length < 2) return results.replaceChildren();
      try {
        const hits = await api(`/api/guide/search?q=${encodeURIComponent(q)}`);
        results.replaceChildren();
        for (const monitor of hits.slice(0, 6)) {
          results.append(el('button', {
            onclick: () => {
              results.replaceChildren();
              input.value = '';
              guideReset('monitor');
              $('#g-step-monitor').hidden = false;
              $('#g-monitors').replaceChildren();
              guide.monitors = [monitor];
              $('#g-monitors').append(el('button', { class: 'monitorcard selected' },
                el('img', { src: monitor.icon_url, alt: '' }),
                el('span', { class: 'mbrand' }, monitor.brand),
                el('span', { class: 'mname' }, monitor.model)));
              selectMonitor(monitor);
            },
          },
            el('img', { src: monitor.icon_url, alt: '' }),
            el('span', {}, `${monitor.brand} ${monitor.model}`)));
        }
      } catch { /* a failed search should not shout at anyone */ }
    }, 180);
  });
}

boot();
wireGuideSearch();
loadGuide().then(restoreFromHash);
// Back/forward between shared procedures should work like any other page.
window.addEventListener('hashchange', restoreFromHash);
