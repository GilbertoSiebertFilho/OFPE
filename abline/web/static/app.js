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
      $('#panel-ops').classList.toggle('active', tab.dataset.tab === 'ops');
      $('#panel-producer').classList.toggle('active', tab.dataset.tab === 'producer');
      if (tab.dataset.tab === 'producer') loadProducer();
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

boot();
