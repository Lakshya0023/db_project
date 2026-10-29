/**
 * Query Lab - interactive catalogue of the project's SQL operations.
 *
 *   SELECT  (22)  - choose parameters, run, see the SQL and the result table
 *   INSERT  (5)   - fill a form, execute, see statements + inserted rows
 *   UPDATE  (5)   - fill a form, execute, see statements + affected rows
 */
import { API } from './api.js';

// ── small helpers ────────────────────────────────────────────────────────────
function esc(text) {
  if (text === null || text === undefined) return '';
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

const SQL_KEYWORDS = [
  'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'INNER', 'ON', 'GROUP', 'ORDER', 'BY', 'HAVING',
  'LIMIT', 'AS', 'AND', 'OR', 'NOT', 'EXISTS', 'IN', 'LIKE', 'UNION', 'ALL', 'INSERT', 'INTO',
  'VALUES', 'RETURNING', 'UPDATE', 'SET', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'DISTINCT',
  'COUNT', 'SUM', 'AVG', 'ROUND', 'COALESCE', 'NULLIF', 'LOWER', 'SUBSTR', 'CAST', 'DESC', 'ASC',
  'IS', 'NULL', 'VARCHAR',
];
const SQL_TOKEN = new RegExp(
  `('[^']*')|(:[a-z_][a-z0-9_]*)|\\b(${SQL_KEYWORDS.join('|')})\\b`, 'gi');

/** Tiny SQL syntax highlighter (keywords / :parameters / string literals). */
function highlightSql(sql) {
  let out = '';
  let last = 0;
  for (const m of sql.matchAll(SQL_TOKEN)) {
    out += esc(sql.slice(last, m.index));
    const cls = m[1] ? 'sql-str' : m[2] ? 'sql-param' : 'sql-kw';
    out += `<span class="${cls}">${esc(m[0])}</span>`;
    last = m.index + m[0].length;
  }
  return out + esc(sql.slice(last));
}

function fmtCell(value) {
  if (value === null || value === undefined) return '<span class="text-[#8B7B74]">—</span>';
  if (typeof value === 'number') {
    return Number.isInteger(value)
      ? value.toLocaleString('en-IN')
      : value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return esc(value);
}

function renderTable(columns, rows) {
  if (!rows.length) {
    return `<div class="text-xs text-[#8B7B74] italic py-3">The query ran successfully but returned 0 rows.</div>`;
  }
  const head = columns.map(c =>
    `<th class="px-3 py-2 text-left font-semibold whitespace-nowrap">${esc(c.replace(/_/g, ' '))}</th>`).join('');
  const body = rows.map(r => `
    <tr class="border-t border-[#C8B8A8]/60 hover:bg-[#EAE0D5]/70">
      ${columns.map(c => `<td class="px-3 py-2 whitespace-nowrap ${typeof r[c] === 'number' ? 'text-right font-mono' : ''}">${fmtCell(r[c])}</td>`).join('')}
    </tr>`).join('');
  return `
    <div class="overflow-auto max-h-80 border border-[#C8B8A8] rounded-xl bg-[#F7F4EF]">
      <table class="min-w-full text-xs text-[#2C221E]">
        <thead class="bg-[#D8CABF] text-[#5C4A42] uppercase tracking-wide text-[10px] sticky top-0"><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

const KIND_STYLE = {
  select: { badge: 'bg-sky-100 text-sky-800 border-sky-300', prefix: 'Q' },
  insert: { badge: 'bg-green-100 text-green-800 border-green-300', prefix: '' },
  update: { badge: 'bg-amber-100 text-amber-800 border-amber-300', prefix: '' },
};

const INPUT_CLS =
  'w-full bg-[#F7F4EF] border border-[#C8B8A8] rounded-lg px-3 py-1.5 text-xs text-[#2C221E] ' +
  'focus:outline-none focus:border-[#C86D51] focus:ring-1 focus:ring-[#C86D51]/40';

// ── module state (survives tab switches) ─────────────────────────────────────
let activeSection = 'select';
let catalog = null;
let lookups = { supplier: [], warehouse: [], product: [] };

async function loadLookups() {
  const [suppliers, warehouses, products] = await Promise.all([
    API.getSuppliers(), API.getWarehouses(), API.getProducts(),
  ]);
  lookups = { supplier: suppliers || [], warehouse: warehouses || [], product: products || [] };
}

function lookupOptions(type) {
  if (type === 'supplier') return lookups.supplier.map(s => [s.supplier_id, s.name]);
  if (type === 'warehouse') return lookups.warehouse.map(w => [w.warehouse_id, w.name]);
  return lookups.product.map(p => [p.product_id, `${p.sku} - ${p.name}`]);
}

// ── field + card builders ────────────────────────────────────────────────────
function fieldHtml(f, idx) {
  const id = `ql-f-${f.name}-${idx}`;
  let control;
  if (['supplier', 'warehouse', 'product'].includes(f.type)) {
    control = `<select id="${id}" data-field="${f.name}" data-lookup="${f.type}" class="${INPUT_CLS}">
      ${lookupOptions(f.type).map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join('')}
    </select>`;
  } else {
    const type = (f.type === 'int' || f.type === 'number') ? 'number' : 'text';
    const attrs = [
      f.type === 'int' ? 'step="1"' : f.type === 'number' ? 'step="any"' : '',
      f.min !== undefined ? `min="${f.min}"` : '',
      f.max !== undefined ? `max="${f.max}"` : '',
      f.default !== undefined && f.default !== null ? `value="${esc(f.default)}"` : '',
    ].join(' ');
    control = `<input id="${id}" data-field="${f.name}" type="${type}" ${attrs} class="${INPUT_CLS}">`;
  }
  const optional = f.required === false ? '<span class="text-[#8B7B74] font-normal"> (optional)</span>' : '';
  return `
    <label class="block" for="${id}">
      <span class="block text-[11px] font-semibold text-[#5C4A42] mb-1">${esc(f.label)}${optional}</span>
      ${control}
    </label>`;
}

function cardShell({ kind, id, label, title, concept, description, fieldsHtml, sqlBlocks, actionLabel, actionIcon }) {
  const st = KIND_STYLE[kind];
  return `
    <article class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-5 space-y-4" data-kind="${kind}" data-id="${esc(id)}">
      <header class="flex flex-wrap items-start gap-3">
        <span class="px-2.5 py-1 rounded-lg border text-xs font-bold font-mono ${st.badge}">${esc(label)}</span>
        <div class="flex-1 min-w-[220px]">
          <h4 class="text-sm font-bold text-[#2C221E] leading-snug">${esc(title)}</h4>
          <p class="text-xs text-[#5C4A42] mt-0.5">${esc(description)}</p>
        </div>
        <span class="text-[10px] uppercase tracking-wide font-semibold text-[#C86D51] bg-[#F7F4EF] border border-[#C86D51]/30 rounded-full px-2.5 py-1">${esc(concept)}</span>
      </header>

      ${fieldsHtml ? `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">${fieldsHtml}</div>` : ''}

      <div class="space-y-2">
        ${sqlBlocks.map(sql => `<pre class="ql-sql">${highlightSql(sql)}</pre>`).join('')}
      </div>

      <div class="flex items-center gap-3">
        <button data-action="run" class="inline-flex items-center gap-2 px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white rounded-lg text-xs font-semibold transition">
          <i data-lucide="${actionIcon}" class="w-3.5 h-3.5"></i> ${esc(actionLabel)}
        </button>
        <span data-role="status" class="text-xs text-[#8B7B74]"></span>
      </div>

      <div data-role="result" class="space-y-3"></div>
    </article>`;
}

function selectCard(q) {
  return cardShell({
    kind: 'select', id: q.id, label: `Q${q.id}`, title: q.title, concept: q.concept,
    description: q.description,
    fieldsHtml: q.params.map((p, i) => fieldHtml(p, `${q.id}-${i}`)).join(''),
    sqlBlocks: [q.sql], actionLabel: 'Run query', actionIcon: 'play',
  });
}

function dmlCard(d) {
  const verb = d.kind === 'INSERT' ? 'Execute INSERT' : 'Execute UPDATE';
  return cardShell({
    kind: d.kind.toLowerCase(), id: d.id, label: d.id, title: d.title, concept: d.concept,
    description: d.description,
    fieldsHtml: d.fields.map((f, i) => fieldHtml(f, `${d.id}-${i}`)).join(''),
    sqlBlocks: d.sql, actionLabel: verb, actionIcon: d.kind === 'INSERT' ? 'plus-circle' : 'pencil',
  });
}

function collectInputs(card) {
  const data = {};
  card.querySelectorAll('[data-field]').forEach(el => { data[el.dataset.field] = el.value; });
  return data;
}

// ── actions ──────────────────────────────────────────────────────────────────
async function runSelect(card, helpers) {
  const status = card.querySelector('[data-role="status"]');
  const result = card.querySelector('[data-role="result"]');
  status.textContent = 'Running…';
  try {
    const res = await API.runSelectQuery(card.dataset.id, collectInputs(card));
    status.textContent = `${res.row_count} row${res.row_count === 1 ? '' : 's'} returned`;
    result.innerHTML = renderTable(res.columns, res.rows);
    return true;
  } catch (err) {
    status.textContent = '';
    result.innerHTML = `<div class="text-xs bg-red-50 border border-red-200 text-red-800 rounded-lg px-3 py-2">${esc(err.message)}</div>`;
    helpers.showToast(err.message, 'error');
    return false;
  }
}

async function runDml(card, root, helpers) {
  const status = card.querySelector('[data-role="status"]');
  const result = card.querySelector('[data-role="result"]');
  const btn = card.querySelector('[data-action="run"]');
  btn.disabled = true;
  btn.classList.add('opacity-60');
  status.textContent = 'Executing…';
  try {
    const res = await API.runDmlQuery(card.dataset.id, collectInputs(card));
    status.textContent = '';
    const stmts = res.statements.map(s => `
      <div class="flex items-start gap-2">
        <span class="shrink-0 mt-1 text-[10px] font-bold font-mono px-2 py-0.5 rounded-full bg-[#C86D51] text-white">${s.rows_affected} row${s.rows_affected === 1 ? '' : 's'}</span>
        <pre class="ql-sql flex-1 !mt-0">${highlightSql(s.sql)}</pre>
      </div>`).join('');
    result.innerHTML = `
      <div class="flex items-center gap-2 text-xs bg-green-50 border border-green-300 text-green-800 rounded-lg px-3 py-2 font-semibold">
        <i data-lucide="check-circle-2" class="w-4 h-4"></i> ${esc(res.message)}
      </div>
      <details open class="text-xs">
        <summary class="cursor-pointer font-semibold text-[#5C4A42] mb-2">Statements executed (committed as one transaction)</summary>
        <div class="space-y-2">${stmts}</div>
      </details>
      ${res.rows.length ? `<div class="text-[11px] font-semibold text-[#5C4A42] uppercase tracking-wide">Resulting data</div>${renderTable(res.columns, res.rows)}` : ''}`;
    helpers.showToast(res.message, 'success');
    if (window.lucide) window.lucide.createIcons();
    await refreshLookups(root, helpers);
  } catch (err) {
    status.textContent = '';
    result.innerHTML = `
      <div class="flex items-center gap-2 text-xs bg-red-50 border border-red-200 text-red-800 rounded-lg px-3 py-2">
        <i data-lucide="x-circle" class="w-4 h-4"></i> ${esc(err.message)}
        <span class="text-[#8B7B74]">- nothing was changed (transaction rolled back).</span>
      </div>`;
    if (window.lucide) window.lucide.createIcons();
    helpers.showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.classList.remove('opacity-60');
  }
}

/** Re-read suppliers/warehouses/products so dropdowns reflect new rows. */
async function refreshLookups(root, helpers) {
  await loadLookups();
  root.querySelectorAll('select[data-lookup]').forEach(sel => {
    const keep = sel.value;
    sel.innerHTML = lookupOptions(sel.dataset.lookup)
      .map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join('');
    if ([...sel.options].some(o => o.value === keep)) sel.value = keep;
  });
  if (helpers.onDataChanged) helpers.onDataChanged();
}

// ── page ─────────────────────────────────────────────────────────────────────
const SECTIONS = [
  { key: 'select', label: 'SELECT queries', icon: 'search' },
  { key: 'insert', label: 'INSERT operations', icon: 'plus-circle' },
  { key: 'update', label: 'UPDATE operations', icon: 'pencil' },
];

function sectionHtml(key) {
  if (key === 'select') return catalog.select.map(selectCard).join('');
  return catalog[key].map(dmlCard).join('');
}

export async function renderQueryLab(container, helpers) {
  const [cat] = await Promise.all([API.queryLabCatalog(), loadLookups()]);
  catalog = cat;
  const c = catalog.counts;

  container.innerHTML = `
    <div class="fade-in space-y-5" id="query-lab-root">
      <div class="bg-[#EAE0D5] p-5 rounded-2xl border border-[#C8B8A8] flex flex-wrap items-center gap-4">
        <div class="flex-1 min-w-[260px]">
          <h3 class="text-base font-semibold text-[#2C221E]">Query Lab</h3>
          <p class="text-xs text-[#5C4A42] mt-0.5">
            Every SQL statement below is the exact text that runs against the database. Parameters are bound
            safely (never concatenated into the SQL). INSERT / UPDATE operations run inside a transaction and
            roll back on any error.
          </p>
        </div>
        <div class="flex gap-2 text-[11px] font-bold">
          <span class="px-3 py-1.5 rounded-full bg-sky-100 text-sky-800 border border-sky-300">${c.select} SELECT</span>
          <span class="px-3 py-1.5 rounded-full bg-green-100 text-green-800 border border-green-300">${c.insert} INSERT</span>
          <span class="px-3 py-1.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300">${c.update} UPDATE</span>
        </div>
        <button data-action="seed" class="inline-flex items-center gap-2 px-4 py-2 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#2C221E] rounded-lg text-xs font-semibold transition">
          <i data-lucide="database" class="w-3.5 h-3.5"></i> Load demo data
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-2" id="ql-tabs"></div>
      <div id="ql-section" class="space-y-4"></div>
    </div>`;

  const root = container.querySelector('#query-lab-root');
  const tabs = root.querySelector('#ql-tabs');
  const section = root.querySelector('#ql-section');

  function paint() {
    tabs.innerHTML = SECTIONS.map(s => {
      const on = s.key === activeSection;
      return `<button data-tab="${s.key}" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border transition
        ${on ? 'bg-[#C86D51] text-white border-[#C86D51]' : 'bg-[#EAE0D5] text-[#5C4A42] border-[#C8B8A8] hover:bg-[#D8CABF]'}">
        <i data-lucide="${s.icon}" class="w-3.5 h-3.5"></i> ${s.label} (${c[s.key]})</button>`;
    }).join('') + (activeSection === 'select' ? `
      <button data-action="run-all" class="ml-auto inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-[#2C221E] text-[#F7F4EF] hover:bg-black transition">
        <i data-lucide="play-circle" class="w-3.5 h-3.5"></i> Run all ${c.select}
      </button>` : '');
    section.innerHTML = sectionHtml(activeSection);
    if (window.lucide) window.lucide.createIcons();
  }
  paint();

  root.addEventListener('click', async (e) => {
    const tab = e.target.closest('[data-tab]');
    if (tab) { activeSection = tab.dataset.tab; paint(); return; }

    const action = e.target.closest('[data-action]');
    if (!action) return;
    const card = action.closest('article');

    if (action.dataset.action === 'seed') {
      action.disabled = true;
      try {
        const res = await API.seedDemoData();
        helpers.showToast(res.message, res.seeded ? 'success' : 'info');
        await refreshLookups(root, helpers);
      } catch (err) {
        helpers.showToast(err.message, 'error');
      } finally { action.disabled = false; }
    } else if (action.dataset.action === 'run-all') {
      action.disabled = true;
      for (const c2 of section.querySelectorAll('article[data-kind="select"]')) {
        await runSelect(c2, helpers);
      }
      action.disabled = false;
      helpers.showToast(`Ran all ${c.select} SELECT queries`, 'success');
    } else if (action.dataset.action === 'run' && card) {
      if (card.dataset.kind === 'select') await runSelect(card, helpers);
      else await runDml(card, root, helpers);
    }
  });
}
