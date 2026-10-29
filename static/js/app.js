import { API } from './api.js';
import { renderQueryLab } from './query_lab.js';

// ── Warm Palette Helpers (replaces dark slate classes) ──────────────────────
const C = {
  // Backgrounds
  pageBg:       'bg-[#F7F4EF]',
  card:         'bg-[#EAE0D5]',
  card2:        'bg-[#D8CABF]',
  input:        'bg-[#F7F4EF]',
  // Borders
  border:       'border-[#C8B8A8]',
  // Text
  text:         'text-[#2C221E]',
  textSec:      'text-[#5C4A42]',
  textMuted:    'text-[#8B7B74]',
  // Accent (Terracotta)
  accent:       'bg-[#C86D51]',
  accentHover:  'hover:bg-[#B35D42]',
  accentText:   'text-[#C86D51]',
  accentBorder: 'border-[#C86D51]',
  // Buttons
  btnPrimary:   'bg-[#C86D51] hover:bg-[#B35D42] text-white',
  btnSecondary: 'bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#2C221E]',
  // Table
  theadBg:      'bg-[#D8CABF]',
  rowHover:     'hover:bg-[#EAE0D5]/70',
  // Divider
  divider:      'border-[#C8B8A8]',
};

// ── Global Application State ─────────────────────────────────────────────────
const state = {
  activeTab: 'dashboard',
  products: [], warehouses: [], suppliers: [],
  inventory: [], purchaseOrders: [], salesOrders: [],
  shipments: [], lowStockItems: [],
  selectedWarehouseFilter: 'all',
  searchQuery: '',
  charts: {}
};

// ── Toast Notification System ────────────────────────────────────────────────
export function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const typeStyles = {
    success: 'bg-[#EAE0D5] border-green-500/60 text-green-800',
    error:   'bg-[#EAE0D5] border-red-500/60 text-red-800',
    warning: 'bg-[#EAE0D5] border-amber-500/60 text-amber-800',
    info:    'bg-[#EAE0D5] border-[#C86D51]/50 text-[#2C221E]',
  };
  const icons = {
    success: '<i data-lucide="check-circle-2" class="w-5 h-5 text-green-600 shrink-0"></i>',
    error:   '<i data-lucide="alert-triangle" class="w-5 h-5 text-red-600 shrink-0"></i>',
    warning: '<i data-lucide="alert-circle" class="w-5 h-5 text-amber-600 shrink-0"></i>',
    info:    '<i data-lucide="info" class="w-5 h-5 text-[#C86D51] shrink-0"></i>',
  };

  toast.className = `toast flex items-start gap-3 p-4 rounded-xl border shadow-xl max-w-md ${typeStyles[type] || typeStyles.info}`;
  toast.innerHTML = `
    ${icons[type] || icons.info}
    <div class="flex-1 text-sm font-medium leading-snug">${message}</div>
    <button class="text-[#8B7B74] hover:text-[#2C221E] shrink-0 -mr-1 -mt-1 p-1 rounded-lg transition-colors" onclick="this.parentElement.remove()">
      <i data-lucide="x" class="w-4 h-4"></i>
    </button>
  `;
  container.appendChild(toast);
  lucide.createIcons({ root: toast });

  setTimeout(() => {
    toast.classList.add('toast-hiding');
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

// ── Modal Helpers ─────────────────────────────────────────────────────────────
export function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.classList.add('overflow-hidden');
    lucide.createIcons({ root: modal });
  }
}
window.openModal = openModal;

export function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
  }
}
window.closeModal = closeModal;
window.showToast = showToast;

window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.add('hidden');
    e.target.classList.remove('flex');
    document.body.classList.remove('overflow-hidden');
  }
});
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop').forEach(m => {
      m.classList.add('hidden'); m.classList.remove('flex');
    });
    document.body.classList.remove('overflow-hidden');
  }
});

// ── Core Data Fetchers ────────────────────────────────────────────────────────
async function refreshBaseLookups() {
  try {
    const [prods, whs, supps] = await Promise.all([
      API.getProducts(), API.getWarehouses(), API.getSuppliers()
    ]);
    state.products   = prods  || [];
    state.warehouses = whs    || [];
    state.suppliers  = supps  || [];
    updateGlobalWarehouseFilter();
  } catch (err) { console.error('Lookup error:', err); }
}

function updateGlobalWarehouseFilter() {
  const select = document.getElementById('global-warehouse-filter');
  if (!select) return;
  const cur = select.value;
  select.innerHTML = `<option value="all">All Warehouses</option>` +
    state.warehouses.map(w =>
      `<option value="${w.warehouse_id}">${esc(w.name)} (${esc(w.location || '')})</option>`
    ).join('');
  if (cur && state.warehouses.some(w => String(w.warehouse_id) === cur)) select.value = cur;
}

// ── Tab Routing ───────────────────────────────────────────────────────────────
export function switchTab(tabName) {
  state.activeTab = tabName;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.dataset.tab === tabName) {
      link.classList.add('bg-[#C86D51]', 'text-white', '!text-white');
      link.classList.remove('text-[#5C4A42]', 'hover:bg-[#D8CABF]', 'hover:text-[#2C221E]', 'text-brown', 'hover:bg-taupe2', 'hover:text-espresso');
    } else {
      link.classList.remove('bg-[#C86D51]', 'text-white', '!text-white');
      link.classList.add('text-brown', 'hover:bg-taupe2', 'hover:text-espresso');
    }
  });

  const titles = {
    dashboard:       'System Overview & Analytics',
    inventory:       'Inventory & Stock Management',
    products:        'Product Catalog',
    warehouses:      'Warehouses & Locations',
    suppliers:       'Suppliers Directory',
    'purchase-orders': 'Purchase Orders (Procurement)',
    'sales-orders':  'Sales Orders (Fulfillment)',
    shipments:       'Shipments & Logistics',
    'query-lab':     'Query Lab (SQL SELECT / INSERT / UPDATE)',
  };
  const el = document.getElementById('current-tab-title');
  if (el) el.textContent = titles[tabName] || 'Dashboard';
  loadActiveTabContent();
}
window.switchTab = switchTab;

async function loadActiveTabContent() {
  const container = document.getElementById('main-content-area');
  if (!container) return;

  container.innerHTML = `
    <div class="flex items-center justify-center py-24">
      <div class="flex flex-col items-center gap-3">
        <div class="w-10 h-10 border-4 border-[#C86D51] border-t-transparent rounded-full animate-spin"></div>
        <p class="text-[#8B7B74] text-sm font-medium">Loading ${state.activeTab.replace('-', ' ')}…</p>
      </div>
    </div>`;

  try {
    switch (state.activeTab) {
      case 'dashboard':       await renderDashboard(container);      break;
      case 'inventory':       await renderInventory(container);      break;
      case 'products':        await renderProducts(container);       break;
      case 'warehouses':      await renderWarehouses(container);     break;
      case 'suppliers':       await renderSuppliers(container);      break;
      case 'purchase-orders': await renderPurchaseOrders(container); break;
      case 'sales-orders':    await renderSalesOrders(container);    break;
      case 'shipments':       await renderShipments(container);      break;
      case 'query-lab':       await renderQueryLab(container, { showToast, onDataChanged: refreshBaseLookups }); break;
      default:                await renderDashboard(container);
    }
    lucide.createIcons();
  } catch (error) {
    container.innerHTML = `
      <div class="p-8 text-center bg-red-50 border border-red-200 rounded-2xl">
        <i data-lucide="alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-3"></i>
        <h3 class="text-lg font-semibold text-red-800 mb-1">Failed to load data</h3>
        <p class="text-[#8B7B74] text-sm max-w-md mx-auto mb-4">${error.message || 'An error occurred while communicating with the server.'}</p>
        <button onclick="window.refreshCurrentTab()" class="px-4 py-2 bg-[#EAE0D5] hover:bg-[#D8CABF] text-[#2C221E] rounded-lg text-sm transition">Retry</button>
      </div>`;
    lucide.createIcons();
  }
}
window.refreshCurrentTab = loadActiveTabContent;

// ── 1. DASHBOARD ─────────────────────────────────────────────────────────────
async function renderDashboard(container) {
  const [products, inventory, lowStock, warehouses, pos, sos, shipments] = await Promise.all([
    API.getProducts(), API.getInventory(), API.getLowStockProducts(),
    API.getWarehouses(), API.getPurchaseOrders(), API.getSalesOrders(), API.getShipments()
  ]);
  state.products = products || []; state.inventory = inventory || [];
  state.lowStockItems = lowStock || []; state.warehouses = warehouses || [];
  state.purchaseOrders = pos || []; state.salesOrders = sos || []; state.shipments = shipments || [];

  const totalStock  = state.inventory.reduce((s, i) => s + (parseInt(i.quantity) || 0), 0);
  const pendingPOs  = state.purchaseOrders.filter(p => p.status === 'pending').length;
  const pendingSOs  = state.salesOrders.filter(s => s.status === 'pending').length;
  const activeShips = state.shipments.filter(s => s.status !== 'delivered').length;

  const kpiCard = (label, value, icon, color, sub) => `
    <div class="bg-[#EAE0D5] border border-[#C8B8A8] p-5 rounded-2xl card-glow">
      <div class="flex items-center justify-between text-[#8B7B74] mb-2">
        <span class="text-xs font-semibold uppercase tracking-wider">${label}</span>
        <div class="p-2 rounded-lg" style="background:${color}22;color:${color}"><i data-lucide="${icon}" class="w-4 h-4"></i></div>
      </div>
      <div class="text-2xl font-bold text-[#2C221E]">${value}</div>
      <div class="text-xs text-[#8B7B74] mt-1">${sub}</div>
    </div>`;

  container.innerHTML = `
    <div class="fade-in space-y-6">
      <!-- KPI Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        ${kpiCard('Total SKUs',    state.products.length, 'package',        '#C86D51', 'Catalog items')}
        ${kpiCard('Stock Units',   totalStock.toLocaleString(), 'boxes',    '#2E7D4F', 'Across all warehouses')}
        ${kpiCard('Low Stock',     state.lowStockItems.length, 'alert-triangle', '#A83428', 'Needs reordering')}
        ${kpiCard('Pending POs',   pendingPOs, 'arrow-down-to-dot',        '#7B4F8A', 'Awaiting receiving')}
        ${kpiCard('Pending Sales', pendingSOs, 'shopping-cart',            '#9A6C20', 'Ready for fulfillment')}
        ${kpiCard('Shipments',     activeShips, 'truck',                   '#C86D51', 'In fulfillment/transit')}
      </div>

      <!-- Low Stock Alert -->
      ${state.lowStockItems.length > 0 ? `
        <div class="bg-red-50 border border-red-200 rounded-2xl p-5">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-red-100 text-red-600 rounded-xl"><i data-lucide="alert-octagon" class="w-5 h-5"></i></div>
              <div>
                <h3 class="text-base font-semibold text-red-800">Critical Stock Replenishment Required</h3>
                <p class="text-xs text-red-600/80">${state.lowStockItems.length} product(s) at or below minimum threshold</p>
              </div>
            </div>
            <button onclick="window.openCreatePOModal()" class="px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-[#C86D51]/20 flex items-center gap-2">
              <i data-lucide="plus-circle" class="w-4 h-4"></i> Create Purchase Order
            </button>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="text-[#8B7B74] uppercase tracking-wider border-b border-[#C8B8A8]">
                <tr>
                  <th class="py-2 px-3">SKU</th><th class="py-2 px-3">Product</th>
                  <th class="py-2 px-3">Warehouse</th><th class="py-2 px-3 text-right">Stock</th>
                  <th class="py-2 px-3 text-right">Threshold</th><th class="py-2 px-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[#C8B8A8]/60">
                ${state.lowStockItems.map(item => `
                  <tr class="hover:bg-red-100/40 transition">
                    <td class="py-2.5 px-3 font-mono font-medium text-[#C86D51]">${esc(item.sku)}</td>
                    <td class="py-2.5 px-3 font-semibold text-[#2C221E]">${esc(item.name)}</td>
                    <td class="py-2.5 px-3 text-[#5C4A42]">${esc(item.warehouse_name)}</td>
                    <td class="py-2.5 px-3 text-right font-bold text-red-700">${item.quantity}</td>
                    <td class="py-2.5 px-3 text-right text-[#8B7B74]">${item.reorder_level}</td>
                    <td class="py-2.5 px-3 text-center">
                      <button onclick="window.openQuickAdjustModal(${item.product_id}, ${item.warehouse_id}, '${esc(item.name)}', ${item.quantity})"
                        class="px-2.5 py-1 bg-[#EAE0D5] hover:bg-[#D8CABF] text-[#2C221E] rounded-lg text-xs font-medium transition inline-flex items-center gap-1">
                        <i data-lucide="sliders" class="w-3 h-3 text-[#C86D51]"></i> Adjust
                      </button>
                    </td>
                  </tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      ` : `
        <div class="bg-green-50 border border-green-200 rounded-2xl p-4 flex items-center gap-3">
          <div class="p-2 bg-green-100 text-green-700 rounded-xl"><i data-lucide="check-check" class="w-5 h-5"></i></div>
          <div>
            <h4 class="text-sm font-semibold text-green-800">Stock Levels Optimal</h4>
            <p class="text-xs text-[#8B7B74]">All inventory items are above minimum reorder levels.</p>
          </div>
        </div>`}

      <!-- Charts & Quick Actions -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Bar Chart -->
        <div class="lg:col-span-2 bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-5">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-[#2C221E] flex items-center gap-2">
              <i data-lucide="bar-chart-3" class="w-5 h-5 text-[#C86D51]"></i> Stock Distribution by Warehouse
            </h3>
            <button onclick="window.switchTab('inventory')" class="text-xs text-[#C86D51] hover:underline">View Details →</button>
          </div>
          <div class="h-64"><canvas id="warehouseStockChart"></canvas></div>
        </div>

        <!-- Quick Operations + Recent Shipments -->
        <div class="space-y-5">
          <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-5">
            <h3 class="text-base font-semibold text-[#2C221E] mb-3 flex items-center gap-2">
              <i data-lucide="zap" class="w-5 h-5 text-amber-600"></i> Quick Operations
            </h3>
            <div class="grid grid-cols-2 gap-2.5">
              ${[
                ['openCreateProductModal', 'plus-circle', '#C86D51', 'Add Product',    'New SKU in catalog'],
                ['openCreatePOModal',      'arrow-down-circle', '#2E7D4F', 'Purchase Order', 'Buy from supplier'],
                ['openCreateSOModal',      'shopping-bag', '#7B4F8A', 'Sales Order',    'Sell to customer'],
                ['openCreateWarehouseModal','warehouse', '#9A6C20', 'New Warehouse', 'Add location'],
              ].map(([fn, icon, col, title, sub]) => `
                <button onclick="window.${fn}()" class="p-3 bg-[#D8CABF] hover:bg-[#C8B8A8] rounded-xl text-left transition border border-[#C8B8A8]">
                  <i data-lucide="${icon}" class="w-5 h-5 mb-1" style="color:${col}"></i>
                  <div class="text-xs font-semibold text-[#2C221E]">${title}</div>
                  <div class="text-[10px] text-[#8B7B74]">${sub}</div>
                </button>`).join('')}
            </div>
          </div>

          <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-5">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-base font-semibold text-[#2C221E] flex items-center gap-2">
                <i data-lucide="truck" class="w-5 h-5 text-[#C86D51]"></i> Active Logistics
              </h3>
              <button onclick="window.switchTab('shipments')" class="text-xs text-[#C86D51] hover:underline">All →</button>
            </div>
            <div class="space-y-2.5">
              ${state.shipments.slice(0, 3).map(sh => `
                <div class="p-3 bg-[#D8CABF] border border-[#C8B8A8] rounded-xl flex items-center justify-between text-xs">
                  <div>
                    <span class="font-bold text-[#2C221E]">#SH-${sh.shipment_id}</span>
                    <span class="text-[#8B7B74] ml-1.5">(SO #${sh.so_id})</span>
                    <div class="text-[11px] text-[#8B7B74] mt-0.5">${esc(sh.customer_name || 'Customer')}</div>
                  </div>
                  ${shipStatusBadge(sh.status)}
                </div>`).join('') || '<div class="text-xs text-[#8B7B74] text-center py-4">No active shipments</div>'}
            </div>
          </div>
        </div>
      </div>
    </div>`;

  // Chart
  setTimeout(() => {
    const ctx = document.getElementById('warehouseStockChart');
    if (!ctx) return;
    const wMap = {};
    state.warehouses.forEach(w => wMap[w.warehouse_id] = { name: w.name, count: 0, cap: w.capacity || 0 });
    state.inventory.forEach(inv => { if (wMap[inv.warehouse_id]) wMap[inv.warehouse_id].count += (parseInt(inv.quantity) || 0); });
    const labels = Object.values(wMap).map(w => w.name);
    const dataStock = Object.values(wMap).map(w => w.count);
    const dataCap   = Object.values(wMap).map(w => w.cap);
    if (state.charts.wh) state.charts.wh.destroy();
    state.charts.wh = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels.length ? labels : ['No Warehouses'],
        datasets: [
          { label: 'Current Stock', data: dataStock.length ? dataStock : [0], backgroundColor: 'rgba(200,109,81,0.7)', borderColor: '#C86D51', borderWidth: 1, borderRadius: 6 },
          { label: 'Max Capacity',  data: dataCap.length   ? dataCap   : [0], backgroundColor: 'rgba(44,34,30,0.12)', borderColor: '#C8B8A8', borderWidth: 1, borderRadius: 6 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#5C4A42', font: { size: 11, family: 'Inter' } } } },
        scales: {
          x: { ticks: { color: '#8B7B74', font: { size: 11 } }, grid: { color: 'rgba(200,184,168,0.3)' } },
          y: { beginAtZero: true, ticks: { color: '#8B7B74', font: { size: 11 } }, grid: { color: 'rgba(200,184,168,0.3)' } }
        }
      }
    });
  }, 50);
}

// ── 2. INVENTORY ──────────────────────────────────────────────────────────────
async function renderInventory(container) {
  const [inventory, warehouses, products] = await Promise.all([
    API.getInventory(), API.getWarehouses(), API.getProducts()
  ]);
  state.inventory = inventory || []; state.warehouses = warehouses || []; state.products = products || [];
  let items = [...state.inventory];
  if (state.selectedWarehouseFilter !== 'all')
    items = items.filter(i => String(i.warehouse_id) === String(state.selectedWarehouseFilter));
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    items = items.filter(i =>
      (i.product_name && i.product_name.toLowerCase().includes(q)) ||
      (i.sku && i.sku.toLowerCase().includes(q)) ||
      (i.warehouse_name && i.warehouse_name.toLowerCase().includes(q))
    );
  }

  container.innerHTML = `
    <div class="fade-in space-y-6">
      <!-- Action Bar -->
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-[#EAE0D5] p-4 rounded-2xl border border-[#C8B8A8]">
        <div class="relative flex-1 max-w-md">
          <i data-lucide="search" class="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8B7B74]"></i>
          <input type="text" placeholder="Search product SKU, name or warehouse…" value="${esc(state.searchQuery)}"
            oninput="window.handleInventorySearch(this.value)"
            class="w-full bg-[#F7F4EF] border border-[#C8B8A8] rounded-xl pl-10 pr-4 py-2 text-sm text-[#2C221E]" />
        </div>
        <div class="flex items-center gap-3">
          <select onchange="window.handleWarehouseFilterChange(this.value)"
            class="bg-[#F7F4EF] border border-[#C8B8A8] text-[#2C221E] text-sm rounded-xl px-3.5 py-2">
            <option value="all">All Warehouses</option>
            ${state.warehouses.map(w => `<option value="${w.warehouse_id}" ${String(state.selectedWarehouseFilter) === String(w.warehouse_id) ? 'selected' : ''}>${esc(w.name)}</option>`).join('')}
          </select>
          <button onclick="window.openAddInventoryModal()" class="px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-[#C86D51]/20 flex items-center gap-2 shrink-0">
            <i data-lucide="plus" class="w-4 h-4"></i> Add Stock Record
          </button>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-[#D8CABF] text-[#8B7B74] text-xs uppercase tracking-wider border-b border-[#C8B8A8]">
              <tr>
                <th class="py-3.5 px-4 font-semibold">SKU</th>
                <th class="py-3.5 px-4 font-semibold">Product Name</th>
                <th class="py-3.5 px-4 font-semibold">Warehouse</th>
                <th class="py-3.5 px-4 font-semibold text-right">In Stock</th>
                <th class="py-3.5 px-4 font-semibold text-right">Reorder Level</th>
                <th class="py-3.5 px-4 font-semibold text-center">Status</th>
                <th class="py-3.5 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#C8B8A8]/60">
              ${items.length > 0 ? items.map(inv => {
                const isLow = inv.quantity <= inv.reorder_level;
                const isOut = inv.quantity === 0;
                return `
                <tr class="hover:bg-[#F7F4EF]/60 transition">
                  <td class="py-3 px-4 font-mono font-medium text-[#C86D51]">${esc(inv.sku)}</td>
                  <td class="py-3 px-4 font-semibold text-[#2C221E]">${esc(inv.product_name)}</td>
                  <td class="py-3 px-4 text-[#5C4A42]">
                    <div class="flex items-center gap-1.5"><i data-lucide="map-pin" class="w-3.5 h-3.5 text-[#8B7B74]"></i>${esc(inv.warehouse_name)}</div>
                  </td>
                  <td class="py-3 px-4 text-right font-bold font-mono text-base ${isOut ? 'text-red-700' : isLow ? 'text-amber-700' : 'text-green-700'}">${inv.quantity}</td>
                  <td class="py-3 px-4 text-right font-mono text-[#8B7B74]">${inv.reorder_level}</td>
                  <td class="py-3 px-4 text-center">
                    ${isOut ? `<span class="badge badge-danger"><i data-lucide="x-circle" class="w-3 h-3"></i> Out of Stock</span>`
                           : isLow ? `<span class="badge badge-warning"><i data-lucide="alert-triangle" class="w-3 h-3"></i> Low Stock</span>`
                           : `<span class="badge badge-success"><i data-lucide="check-circle" class="w-3 h-3"></i> Healthy</span>`}
                  </td>
                  <td class="py-3 px-4 text-right">
                    <div class="flex items-center justify-end gap-2">
                      <button onclick="window.openQuickAdjustModal(${inv.product_id}, ${inv.warehouse_id}, '${esc(inv.product_name)}', ${inv.quantity})"
                        class="px-2.5 py-1.5 bg-[#C86D51]/10 hover:bg-[#C86D51]/20 text-[#C86D51] border border-[#C86D51]/30 rounded-lg text-xs font-semibold transition flex items-center gap-1.5">
                        <i data-lucide="sliders" class="w-3.5 h-3.5"></i> Adjust
                      </button>
                      <button onclick="window.deleteInventoryItem(${inv.inventory_id})"
                        class="p-1.5 text-[#8B7B74] hover:text-red-700 hover:bg-red-100 rounded-lg transition">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                      </button>
                    </div>
                  </td>
                </tr>`;
              }).join('') : `
                <tr><td colspan="7" class="py-12 text-center text-[#8B7B74]">
                  <i data-lucide="package-search" class="w-10 h-10 mx-auto mb-2 text-[#C8B8A8]"></i>
                  No inventory records found.
                </td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}

window.handleInventorySearch = (val) => {
  state.searchQuery = val;
  renderInventory(document.getElementById('main-content-area')).then(() => lucide.createIcons());
};
window.handleWarehouseFilterChange = (val) => {
  state.selectedWarehouseFilter = val;
  renderInventory(document.getElementById('main-content-area')).then(() => lucide.createIcons());
};

// ── 3. PRODUCTS ───────────────────────────────────────────────────────────────
async function renderProducts(container) {
  const [products, suppliers] = await Promise.all([API.getProducts(), API.getSuppliers()]);
  state.products = products || []; state.suppliers = suppliers || [];

  container.innerHTML = `
    <div class="fade-in space-y-6">
      <div class="flex items-center justify-between bg-[#EAE0D5] p-4 rounded-2xl border border-[#C8B8A8]">
        <div>
          <h3 class="text-base font-semibold text-[#2C221E]">Product Catalog (${state.products.length})</h3>
          <p class="text-xs text-[#8B7B74]">Master product database, pricing, and supplier affiliations</p>
        </div>
        <button onclick="window.openCreateProductModal()" class="px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-[#C86D51]/20 flex items-center gap-2">
          <i data-lucide="plus" class="w-4 h-4"></i> New Product
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        ${state.products.map(p => `
          <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-5 flex flex-col justify-between card-glow">
            <div>
              <div class="flex items-start justify-between gap-3 mb-2">
                <span class="font-mono text-xs px-2 py-0.5 bg-[#C86D51]/10 text-[#C86D51] border border-[#C86D51]/20 rounded-md font-semibold">${esc(p.sku)}</span>
                <span class="text-lg font-bold text-green-700 font-mono">$${parseFloat(p.unit_price || 0).toFixed(2)}</span>
              </div>
              <h4 class="text-base font-bold text-[#2C221E] mb-1.5">${esc(p.name)}</h4>
              <p class="text-xs text-[#8B7B74] line-clamp-2 mb-4">${esc(p.description || 'No description provided.')}</p>
            </div>
            <div class="pt-4 border-t border-[#C8B8A8] space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="text-[#8B7B74]">Supplier:</span>
                <span class="font-medium text-[#5C4A42]">${esc(p.supplier_name || 'None')}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-[#8B7B74]">Reorder Threshold:</span>
                <span class="font-mono text-amber-700 font-semibold">${p.reorder_level} units</span>
              </div>
              <div class="flex items-center justify-end gap-2 pt-2">
                <button onclick='window.openEditProductModal(${JSON.stringify(p)})'
                  class="px-3 py-1.5 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#2C221E] rounded-lg text-xs font-semibold transition flex items-center gap-1.5">
                  <i data-lucide="edit-3" class="w-3.5 h-3.5"></i> Edit
                </button>
                <button onclick="window.deleteProductItem(${p.product_id})"
                  class="px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-700 border border-red-200 rounded-lg text-xs font-semibold transition flex items-center gap-1.5">
                  <i data-lucide="trash-2" class="w-3.5 h-3.5"></i> Delete
                </button>
              </div>
            </div>
          </div>`).join('') || `
          <div class="col-span-full py-16 text-center text-[#8B7B74] bg-[#EAE0D5] rounded-2xl border border-dashed border-[#C8B8A8]">
            <i data-lucide="package" class="w-12 h-12 mx-auto mb-3 text-[#C8B8A8]"></i>
            No products found. Add your first product to get started!
          </div>`}
      </div>
    </div>`;
}

// ── 4. WAREHOUSES ─────────────────────────────────────────────────────────────
async function renderWarehouses(container) {
  const [warehouses, inventory] = await Promise.all([API.getWarehouses(), API.getInventory()]);
  state.warehouses = warehouses || []; state.inventory = inventory || [];

  container.innerHTML = `
    <div class="fade-in space-y-6">
      <div class="flex items-center justify-between bg-[#EAE0D5] p-4 rounded-2xl border border-[#C8B8A8]">
        <div>
          <h3 class="text-base font-semibold text-[#2C221E]">Warehouses & Storage Facilities (${state.warehouses.length})</h3>
          <p class="text-xs text-[#8B7B74]">Manage distribution centers, capacity constraints, and inventory</p>
        </div>
        <button onclick="window.openCreateWarehouseModal()" class="px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-[#C86D51]/20 flex items-center gap-2">
          <i data-lucide="plus" class="w-4 h-4"></i> Add Warehouse
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        ${state.warehouses.map(w => {
          const whInv = state.inventory.filter(i => i.warehouse_id === w.warehouse_id);
          const total = whInv.reduce((a, c) => a + (parseInt(c.quantity) || 0), 0);
          const cap   = w.capacity || 0;
          const pct   = cap > 0 ? Math.min(100, Math.round((total / cap) * 100)) : 0;
          const barColor = pct > 85 ? '#A83428' : pct > 60 ? '#9A6C20' : '#C86D51';
          return `
          <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-5 flex flex-col justify-between card-glow">
            <div>
              <div class="flex items-start justify-between gap-3 mb-2">
                <div class="p-2.5 bg-[#C86D51]/10 text-[#C86D51] rounded-xl">
                  <i data-lucide="warehouse" class="w-6 h-6"></i>
                </div>
                <span class="badge ${pct > 85 ? 'badge-danger' : pct > 60 ? 'badge-warning' : 'badge-success'}">${pct}% Utilized</span>
              </div>
              <h4 class="text-lg font-bold text-[#2C221E] mb-1">${esc(w.name)}</h4>
              <p class="text-xs text-[#8B7B74] flex items-center gap-1.5 mb-4">
                <i data-lucide="map-pin" class="w-3.5 h-3.5 text-[#C8B8A8]"></i>
                ${esc(w.location || 'Location unassigned')}
              </p>
              <div class="space-y-1.5 mb-4">
                <div class="flex justify-between text-xs font-semibold">
                  <span class="text-[#8B7B74]">Stored: <strong class="text-[#2C221E]">${total.toLocaleString()}</strong> units</span>
                  <span class="text-[#8B7B74]">Cap: <strong class="text-[#5C4A42]">${cap.toLocaleString()}</strong></span>
                </div>
                <div class="cap-bar-track">
                  <div class="cap-bar-fill" style="width:${pct}%;background-color:${barColor}"></div>
                </div>
              </div>
            </div>
            <div class="pt-4 border-t border-[#C8B8A8] space-y-2">
              <button onclick="window.viewWarehouseStock(${w.warehouse_id}, '${esc(w.name)}')"
                class="w-full py-2 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#2C221E] text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5">
                <i data-lucide="package-open" class="w-4 h-4 text-[#C86D51]"></i> View Stocked Products (${whInv.length})
              </button>
              <div class="flex items-center gap-2">
                <button onclick='window.openEditWarehouseModal(${JSON.stringify(w)})'
                  class="flex-1 py-1.5 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#5C4A42] rounded-lg text-xs font-medium transition flex items-center justify-center gap-1">
                  <i data-lucide="edit-3" class="w-3.5 h-3.5"></i> Edit
                </button>
                <button onclick="window.deleteWarehouseItem(${w.warehouse_id})"
                  class="p-1.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition">
                  <i data-lucide="trash-2" class="w-4 h-4"></i>
                </button>
              </div>
            </div>
          </div>`;
        }).join('') || `
          <div class="col-span-full py-16 text-center text-[#8B7B74] bg-[#EAE0D5] rounded-2xl border border-dashed border-[#C8B8A8]">
            <i data-lucide="warehouse" class="w-12 h-12 mx-auto mb-3 text-[#C8B8A8]"></i>No warehouses configured.
          </div>`}
      </div>
    </div>`;
}

// ── 5. SUPPLIERS ──────────────────────────────────────────────────────────────
async function renderSuppliers(container) {
  state.suppliers = (await API.getSuppliers()) || [];
  container.innerHTML = `
    <div class="fade-in space-y-6">
      <div class="flex items-center justify-between bg-[#EAE0D5] p-4 rounded-2xl border border-[#C8B8A8]">
        <div>
          <h3 class="text-base font-semibold text-[#2C221E]">Suppliers & Vendors (${state.suppliers.length})</h3>
          <p class="text-xs text-[#8B7B74]">Vendor directory, contact points, and product line assignments</p>
        </div>
        <button onclick="window.openCreateSupplierModal()" class="px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-[#C86D51]/20 flex items-center gap-2">
          <i data-lucide="plus" class="w-4 h-4"></i> Add Supplier
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        ${state.suppliers.map(s => `
          <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-5 flex flex-col justify-between card-glow">
            <div>
              <div class="flex items-start justify-between gap-3 mb-2">
                <div class="p-2.5 bg-[#7B4F8A]/10 text-[#7B4F8A] rounded-xl">
                  <i data-lucide="building-2" class="w-6 h-6"></i>
                </div>
                <span class="font-mono text-xs text-[#8B7B74]">ID: #${s.supplier_id}</span>
              </div>
              <h4 class="text-lg font-bold text-[#2C221E] mb-2">${esc(s.name)}</h4>
              <div class="space-y-1.5 text-xs text-[#8B7B74] mb-4">
                <div class="flex items-center gap-2"><i data-lucide="mail" class="w-3.5 h-3.5 text-[#C8B8A8] shrink-0"></i><span class="truncate">${esc(s.contact_email || 'No email')}</span></div>
                <div class="flex items-center gap-2"><i data-lucide="phone" class="w-3.5 h-3.5 text-[#C8B8A8] shrink-0"></i><span>${esc(s.contact_phone || 'No phone')}</span></div>
                <div class="flex items-start gap-2"><i data-lucide="map-pin" class="w-3.5 h-3.5 text-[#C8B8A8] shrink-0 mt-0.5"></i><span class="line-clamp-2">${esc(s.address || 'No address')}</span></div>
              </div>
            </div>
            <div class="pt-4 border-t border-[#C8B8A8] space-y-2">
              <button onclick="window.viewSupplierProducts(${s.supplier_id}, '${esc(s.name)}')"
                class="w-full py-2 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#2C221E] text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5">
                <i data-lucide="boxes" class="w-4 h-4 text-[#7B4F8A]"></i> View Supplied SKUs
              </button>
              <div class="flex items-center gap-2">
                <button onclick='window.openEditSupplierModal(${JSON.stringify(s)})'
                  class="flex-1 py-1.5 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#5C4A42] rounded-lg text-xs font-medium transition flex items-center justify-center gap-1">
                  <i data-lucide="edit-3" class="w-3.5 h-3.5"></i> Edit
                </button>
                <button onclick="window.deleteSupplierItem(${s.supplier_id})"
                  class="p-1.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition">
                  <i data-lucide="trash-2" class="w-4 h-4"></i>
                </button>
              </div>
            </div>
          </div>`).join('') || `
          <div class="col-span-full py-16 text-center text-[#8B7B74] bg-[#EAE0D5] rounded-2xl border border-dashed border-[#C8B8A8]">
            <i data-lucide="building-2" class="w-12 h-12 mx-auto mb-3 text-[#C8B8A8]"></i>No suppliers found.
          </div>`}
      </div>
    </div>`;
}

// ── 6. PURCHASE ORDERS ────────────────────────────────────────────────────────
async function renderPurchaseOrders(container) {
  const [pos, suppliers, warehouses] = await Promise.all([
    API.getPurchaseOrders(), API.getSuppliers(), API.getWarehouses()
  ]);
  state.purchaseOrders = pos || []; state.suppliers = suppliers || []; state.warehouses = warehouses || [];

  container.innerHTML = `
    <div class="fade-in space-y-6">
      <div class="flex items-center justify-between bg-[#EAE0D5] p-4 rounded-2xl border border-[#C8B8A8]">
        <div>
          <h3 class="text-base font-semibold text-[#2C221E]">Purchase Orders & Inbound Stock (${state.purchaseOrders.length})</h3>
          <p class="text-xs text-[#8B7B74]">Order from suppliers and receive stock directly into warehouse inventory</p>
        </div>
        <button onclick="window.openCreatePOModal()" class="px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-[#C86D51]/20 flex items-center gap-2">
          <i data-lucide="plus" class="w-4 h-4"></i> Create Purchase Order
        </button>
      </div>
      <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-[#D8CABF] text-[#8B7B74] text-xs uppercase tracking-wider border-b border-[#C8B8A8]">
              <tr>
                <th class="py-3.5 px-4">PO #</th><th class="py-3.5 px-4">Supplier</th>
                <th class="py-3.5 px-4">Receiving Warehouse</th><th class="py-3.5 px-4">Order Date</th>
                <th class="py-3.5 px-4 text-center">Status</th><th class="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#C8B8A8]/60">
              ${state.purchaseOrders.map(po => `
                <tr class="hover:bg-[#F7F4EF]/60 transition">
                  <td class="py-3.5 px-4 font-mono font-bold text-[#2C221E]">#PO-${po.po_id}</td>
                  <td class="py-3.5 px-4 font-semibold text-[#2C221E]">${esc(po.supplier_name)}</td>
                  <td class="py-3.5 px-4 text-[#5C4A42]">
                    <div class="flex items-center gap-1.5"><i data-lucide="map-pin" class="w-3.5 h-3.5 text-[#8B7B74]"></i>${esc(po.warehouse_name)}</div>
                  </td>
                  <td class="py-3.5 px-4 text-[#8B7B74] text-xs">${fmtDate(po.order_date)}</td>
                  <td class="py-3.5 px-4 text-center">${orderStatusBadge(po.status)}</td>
                  <td class="py-3.5 px-4 text-right">
                    <div class="flex items-center justify-end gap-2">
                      <button onclick="window.viewPODetails(${po.po_id})"
                        class="px-3 py-1.5 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#2C221E] rounded-lg text-xs font-semibold transition flex items-center gap-1">
                        <i data-lucide="eye" class="w-3.5 h-3.5"></i> Details
                      </button>
                      ${po.status === 'pending' ? `
                        <button onclick="window.receivePurchaseOrderAction(${po.po_id})"
                          class="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold transition shadow-sm flex items-center gap-1">
                          <i data-lucide="package-check" class="w-3.5 h-3.5"></i> Receive Stock
                        </button>
                        <button onclick="window.cancelPurchaseOrderAction(${po.po_id})"
                          class="p-1.5 text-[#8B7B74] hover:text-red-700 hover:bg-red-100 rounded-lg transition">
                          <i data-lucide="x" class="w-4 h-4"></i>
                        </button>` : ''}
                    </div>
                  </td>
                </tr>`).join('') || `
                <tr><td colspan="6" class="py-12 text-center text-[#8B7B74]">
                  <i data-lucide="file-text" class="w-10 h-10 mx-auto mb-2 text-[#C8B8A8]"></i>
                  No purchase orders found.
                </td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}

// ── 7. SALES ORDERS ───────────────────────────────────────────────────────────
async function renderSalesOrders(container) {
  const [sos, warehouses] = await Promise.all([API.getSalesOrders(), API.getWarehouses()]);
  state.salesOrders = sos || []; state.warehouses = warehouses || [];

  container.innerHTML = `
    <div class="fade-in space-y-6">
      <div class="flex items-center justify-between bg-[#EAE0D5] p-4 rounded-2xl border border-[#C8B8A8]">
        <div>
          <h3 class="text-base font-semibold text-[#2C221E]">Sales Orders & Customer Demand (${state.salesOrders.length})</h3>
          <p class="text-xs text-[#8B7B74]">Manage orders, check available stock, and trigger fulfillment & logistics</p>
        </div>
        <button onclick="window.openCreateSOModal()" class="px-4 py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-[#C86D51]/20 flex items-center gap-2">
          <i data-lucide="plus" class="w-4 h-4"></i> Create Sales Order
        </button>
      </div>
      <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-[#D8CABF] text-[#8B7B74] text-xs uppercase tracking-wider border-b border-[#C8B8A8]">
              <tr>
                <th class="py-3.5 px-4">SO #</th><th class="py-3.5 px-4">Customer Name</th>
                <th class="py-3.5 px-4">Fulfillment Warehouse</th><th class="py-3.5 px-4">Order Date</th>
                <th class="py-3.5 px-4 text-center">Status</th><th class="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#C8B8A8]/60">
              ${state.salesOrders.map(so => `
                <tr class="hover:bg-[#F7F4EF]/60 transition">
                  <td class="py-3.5 px-4 font-mono font-bold text-[#2C221E]">#SO-${so.so_id}</td>
                  <td class="py-3.5 px-4 font-semibold text-[#2C221E]">${esc(so.customer_name)}</td>
                  <td class="py-3.5 px-4 text-[#5C4A42]">
                    <div class="flex items-center gap-1.5"><i data-lucide="map-pin" class="w-3.5 h-3.5 text-[#8B7B74]"></i>${esc(so.warehouse_name)}</div>
                  </td>
                  <td class="py-3.5 px-4 text-[#8B7B74] text-xs">${fmtDate(so.order_date)}</td>
                  <td class="py-3.5 px-4 text-center">${orderStatusBadge(so.status)}</td>
                  <td class="py-3.5 px-4 text-right">
                    <div class="flex items-center justify-end gap-2">
                      <button onclick="window.viewSODetails(${so.so_id})"
                        class="px-3 py-1.5 bg-[#D8CABF] hover:bg-[#C8B8A8] text-[#2C221E] rounded-lg text-xs font-semibold transition flex items-center gap-1">
                        <i data-lucide="eye" class="w-3.5 h-3.5"></i> Details
                      </button>
                      ${so.status === 'pending' ? `
                        <button onclick="window.fulfillSalesOrderAction(${so.so_id})"
                          class="px-3 py-1.5 bg-[#C86D51] hover:bg-[#B35D42] text-white rounded-lg text-xs font-semibold transition shadow-sm flex items-center gap-1">
                          <i data-lucide="box" class="w-3.5 h-3.5"></i> Fulfill Order
                        </button>
                        <button onclick="window.cancelSalesOrderAction(${so.so_id})"
                          class="p-1.5 text-[#8B7B74] hover:text-red-700 hover:bg-red-100 rounded-lg transition">
                          <i data-lucide="x" class="w-4 h-4"></i>
                        </button>` : ''}
                    </div>
                  </td>
                </tr>`).join('') || `
                <tr><td colspan="6" class="py-12 text-center text-[#8B7B74]">
                  <i data-lucide="shopping-cart" class="w-10 h-10 mx-auto mb-2 text-[#C8B8A8]"></i>No sales orders created yet.
                </td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    </div>`;
}

// ── 8. SHIPMENTS ──────────────────────────────────────────────────────────────
async function renderShipments(container) {
  state.shipments = (await API.getShipments()) || [];
  const byStatus = (s) => state.shipments.filter(sh => sh.status === s);

  const shipCard = (sh) => `
    <div class="bg-[#D8CABF] border border-[#C8B8A8] rounded-xl p-4 space-y-3">
      <div class="flex justify-between items-start">
        <div>
          <span class="font-bold text-[#2C221E] font-mono text-sm">#SH-${sh.shipment_id}</span>
          <span class="text-xs text-[#8B7B74] block mt-0.5">SO #${sh.so_id} · ${esc(sh.customer_name || '')}</span>
        </div>
        ${shipStatusBadge(sh.status)}
      </div>`;

  container.innerHTML = `
    <div class="fade-in space-y-6">
      <div class="bg-[#EAE0D5] p-4 rounded-2xl border border-[#C8B8A8]">
        <h3 class="text-base font-semibold text-[#2C221E]">Logistics & Shipments Tracking (${state.shipments.length})</h3>
        <p class="text-xs text-[#8B7B74]">Track shipments generated from fulfilled sales orders</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">

        <!-- Preparing -->
        <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-4 flex flex-col">
          <div class="flex items-center justify-between pb-3 mb-3 border-b border-[#C8B8A8]">
            <span class="font-bold text-sm text-amber-700 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span> Preparing Dispatch
            </span>
            <span class="badge badge-warning">${byStatus('preparing').length}</span>
          </div>
          <div class="space-y-3 flex-1">
            ${byStatus('preparing').map(sh => `
              ${shipCard(sh)}
              <button onclick="window.openShipModal(${sh.shipment_id})"
                class="w-full py-2 bg-[#C86D51] hover:bg-[#B35D42] text-white rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5">
                <i data-lucide="send" class="w-3.5 h-3.5"></i> Dispatch & Add Tracking
              </button>
            </div>`).join('') || '<div class="text-xs text-[#8B7B74] text-center py-8">No orders awaiting dispatch</div>'}
          </div>
        </div>

        <!-- Shipped -->
        <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-4 flex flex-col">
          <div class="flex items-center justify-between pb-3 mb-3 border-b border-[#C8B8A8]">
            <span class="font-bold text-sm text-[#C86D51] flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[#C86D51]"></span> In Transit
            </span>
            <span class="badge badge-info">${byStatus('shipped').length}</span>
          </div>
          <div class="space-y-3 flex-1">
            ${byStatus('shipped').map(sh => `
              ${shipCard(sh)}
              <div class="text-xs bg-[#F7F4EF] p-2.5 rounded-lg space-y-1 border border-[#C8B8A8]">
                <div class="text-[#8B7B74]">Carrier: <strong class="text-[#2C221E]">${esc(sh.carrier || 'Unspecified')}</strong></div>
                <div class="text-[#8B7B74]">Tracking: <strong class="font-mono text-[#C86D51]">${esc(sh.tracking_number || 'N/A')}</strong></div>
                <div class="text-[11px] text-[#8B7B74]">Shipped: ${fmtDate(sh.shipped_date)}</div>
              </div>
              <button onclick="window.markDeliveredAction(${sh.shipment_id})"
                class="w-full py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold transition flex items-center justify-center gap-1.5">
                <i data-lucide="check-circle-2" class="w-3.5 h-3.5"></i> Mark Delivered
              </button>
            </div>`).join('') || '<div class="text-xs text-[#8B7B74] text-center py-8">No shipments in transit</div>'}
          </div>
        </div>

        <!-- Delivered -->
        <div class="bg-[#EAE0D5] border border-[#C8B8A8] rounded-2xl p-4 flex flex-col">
          <div class="flex items-center justify-between pb-3 mb-3 border-b border-[#C8B8A8]">
            <span class="font-bold text-sm text-green-700 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-green-500"></span> Completed Deliveries
            </span>
            <span class="badge badge-success">${byStatus('delivered').length}</span>
          </div>
          <div class="space-y-3 flex-1 max-h-[600px] overflow-y-auto pr-1">
            ${byStatus('delivered').map(sh => `
              ${shipCard(sh)}
              <div class="text-xs text-[#8B7B74]">
                ${esc(sh.carrier || 'Direct')} · <span class="font-mono text-[#5C4A42]">${esc(sh.tracking_number || '')}</span>
                <div class="text-[11px] mt-1">Delivered: ${fmtDate(sh.delivered_date)}</div>
              </div>
            </div>`).join('') || '<div class="text-xs text-[#8B7B74] text-center py-8">No delivered shipments</div>'}
          </div>
        </div>
      </div>
    </div>`;
}

// ── Action Handlers ───────────────────────────────────────────────────────────
window.openQuickAdjustModal = (productId, warehouseId, productName, currentQty) => {
  document.getElementById('adjust-product-id').value = productId;
  document.getElementById('adjust-warehouse-id').value = warehouseId;
  document.getElementById('adjust-product-name').textContent = productName;
  document.getElementById('adjust-current-stock').textContent = currentQty;
  document.getElementById('adjust-change').value = '';
  document.getElementById('adjust-type').value = 'in';
  openModal('modal-quick-adjust');
};

window.handleStockAdjustSubmit = async (e) => {
  e.preventDefault();
  const productId   = parseInt(document.getElementById('adjust-product-id').value);
  const warehouseId = parseInt(document.getElementById('adjust-warehouse-id').value);
  const type        = document.getElementById('adjust-type').value;
  let raw           = parseInt(document.getElementById('adjust-change').value);
  if (isNaN(raw) || raw <= 0) { showToast('Please enter a valid quantity > 0', 'warning'); return; }
  const change = type === 'out' ? -raw : raw;
  try {
    const updated = await API.adjustStock({ product_id: productId, warehouse_id: warehouseId, change });
    showToast(`Stock updated! New quantity: ${updated.quantity}`, 'success');
    closeModal('modal-quick-adjust');
    loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to adjust stock', 'error'); }
};

window.openAddInventoryModal = async () => {
  await refreshBaseLookups();
  document.getElementById('new-inv-product-id').innerHTML =
    state.products.map(p => `<option value="${p.product_id}">${esc(p.name)} (${esc(p.sku)})</option>`).join('');
  document.getElementById('new-inv-warehouse-id').innerHTML =
    state.warehouses.map(w => `<option value="${w.warehouse_id}">${esc(w.name)}</option>`).join('');
  document.getElementById('new-inv-quantity').value = '10';
  openModal('modal-add-inventory');
};
window.handleAddInventorySubmit = async (e) => {
  e.preventDefault();
  try {
    await API.createInventoryRecord({
      product_id:   parseInt(document.getElementById('new-inv-product-id').value),
      warehouse_id: parseInt(document.getElementById('new-inv-warehouse-id').value),
      quantity:     parseInt(document.getElementById('new-inv-quantity').value) || 0,
    });
    showToast('Inventory record created', 'success');
    closeModal('modal-add-inventory'); loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to create record', 'error'); }
};
window.deleteInventoryItem = async (id) => {
  if (!confirm('Remove this inventory record?')) return;
  try { await API.deleteInventoryRecord(id); showToast('Record deleted', 'success'); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to delete', 'error'); }
};

window.openCreateProductModal = async () => {
  await refreshBaseLookups();
  document.getElementById('product-supplier-id').innerHTML =
    `<option value="">-- Select Supplier (Optional) --</option>` +
    state.suppliers.map(s => `<option value="${s.supplier_id}">${esc(s.name)}</option>`).join('');
  ['product-id','product-sku','product-name','product-description','product-price'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('product-reorder').value = '10';
  document.getElementById('product-form-title').textContent = 'Create New Product';
  openModal('modal-product');
};
window.openEditProductModal = async (p) => {
  await refreshBaseLookups();
  document.getElementById('product-supplier-id').innerHTML =
    `<option value="">-- Select Supplier (Optional) --</option>` +
    state.suppliers.map(s => `<option value="${s.supplier_id}" ${s.supplier_id === p.supplier_id ? 'selected' : ''}>${esc(s.name)}</option>`).join('');
  document.getElementById('product-form-title').textContent = 'Edit Product';
  document.getElementById('product-id').value          = p.product_id;
  document.getElementById('product-sku').value         = p.sku;
  document.getElementById('product-name').value        = p.name;
  document.getElementById('product-description').value = p.description || '';
  document.getElementById('product-price').value       = p.unit_price;
  document.getElementById('product-reorder').value     = p.reorder_level;
  openModal('modal-product');
};
window.handleProductSubmit = async (e) => {
  e.preventDefault();
  const id   = document.getElementById('product-id').value;
  const data = {
    sku:           document.getElementById('product-sku').value.trim(),
    name:          document.getElementById('product-name').value.trim(),
    description:   document.getElementById('product-description').value.trim(),
    unit_price:    parseFloat(document.getElementById('product-price').value),
    reorder_level: parseInt(document.getElementById('product-reorder').value) || 10,
    supplier_id:   document.getElementById('product-supplier-id').value ? parseInt(document.getElementById('product-supplier-id').value) : null,
  };
  try {
    if (id) { await API.updateProduct(id, data); showToast('Product updated', 'success'); }
    else     { await API.createProduct(data);    showToast('Product created', 'success'); }
    closeModal('modal-product'); loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to save product', 'error'); }
};
window.deleteProductItem = async (id) => {
  if (!confirm('Delete this product? All linked inventory will be removed.')) return;
  try { await API.deleteProduct(id); showToast('Product deleted', 'success'); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to delete', 'error'); }
};

window.openCreateWarehouseModal = () => {
  document.getElementById('warehouse-form-title').textContent = 'Add New Warehouse';
  ['warehouse-id','warehouse-name','warehouse-location'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('warehouse-capacity').value = '5000';
  openModal('modal-warehouse');
};
window.openEditWarehouseModal = (w) => {
  document.getElementById('warehouse-form-title').textContent = 'Edit Warehouse';
  document.getElementById('warehouse-id').value       = w.warehouse_id;
  document.getElementById('warehouse-name').value     = w.name;
  document.getElementById('warehouse-location').value = w.location || '';
  document.getElementById('warehouse-capacity').value = w.capacity || 0;
  openModal('modal-warehouse');
};
window.handleWarehouseSubmit = async (e) => {
  e.preventDefault();
  const id = document.getElementById('warehouse-id').value;
  const data = {
    name:     document.getElementById('warehouse-name').value.trim(),
    location: document.getElementById('warehouse-location').value.trim(),
    capacity: parseInt(document.getElementById('warehouse-capacity').value) || 0,
  };
  try {
    if (id) { await API.updateWarehouse(id, data); showToast('Warehouse updated', 'success'); }
    else     { await API.createWarehouse(data);    showToast('Warehouse created', 'success'); }
    closeModal('modal-warehouse'); await refreshBaseLookups(); loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to save', 'error'); }
};
window.deleteWarehouseItem = async (id) => {
  if (!confirm('Delete this warehouse?')) return;
  try { await API.deleteWarehouse(id); showToast('Warehouse deleted', 'success'); await refreshBaseLookups(); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to delete', 'error'); }
};
window.viewWarehouseStock = async (id, name) => {
  try {
    const stock = await API.getWarehouseStock(id);
    document.getElementById('warehouse-stock-title').textContent = `Stock at ${name}`;
    document.getElementById('warehouse-stock-list').innerHTML = !stock?.length
      ? `<div class="py-8 text-center text-[#8B7B74]">No items stocked at this location.</div>`
      : `<table class="w-full text-left text-xs">
          <thead class="text-[#8B7B74] uppercase border-b border-[#C8B8A8]">
            <tr><th class="py-2 px-3">SKU</th><th class="py-2 px-3">Product</th><th class="py-2 px-3 text-right">Qty</th><th class="py-2 px-3 text-right">Reorder</th></tr>
          </thead>
          <tbody class="divide-y divide-[#C8B8A8]/60">
            ${stock.map(s => `
              <tr class="hover:bg-[#F7F4EF]/60">
                <td class="py-2.5 px-3 font-mono font-medium text-[#C86D51]">${esc(s.sku)}</td>
                <td class="py-2.5 px-3 font-semibold text-[#2C221E]">${esc(s.name)}</td>
                <td class="py-2.5 px-3 text-right font-bold ${s.quantity <= s.reorder_level ? 'text-amber-700' : 'text-green-700'}">${s.quantity}</td>
                <td class="py-2.5 px-3 text-right text-[#8B7B74]">${s.reorder_level}</td>
              </tr>`).join('')}
          </tbody>
        </table>`;
    openModal('modal-warehouse-stock');
  } catch (err) { showToast('Failed to fetch warehouse stock', 'error'); }
};

window.openCreateSupplierModal = () => {
  document.getElementById('supplier-form-title').textContent = 'Add Supplier';
  ['supplier-id','supplier-name','supplier-email','supplier-phone','supplier-address'].forEach(id => document.getElementById(id).value = '');
  openModal('modal-supplier');
};
window.openEditSupplierModal = (s) => {
  document.getElementById('supplier-form-title').textContent = 'Edit Supplier';
  document.getElementById('supplier-id').value      = s.supplier_id;
  document.getElementById('supplier-name').value    = s.name;
  document.getElementById('supplier-email').value   = s.contact_email || '';
  document.getElementById('supplier-phone').value   = s.contact_phone || '';
  document.getElementById('supplier-address').value = s.address || '';
  openModal('modal-supplier');
};
window.handleSupplierSubmit = async (e) => {
  e.preventDefault();
  const id = document.getElementById('supplier-id').value;
  const data = {
    name:          document.getElementById('supplier-name').value.trim(),
    contact_email: document.getElementById('supplier-email').value.trim(),
    contact_phone: document.getElementById('supplier-phone').value.trim(),
    address:       document.getElementById('supplier-address').value.trim(),
  };
  try {
    if (id) { await API.updateSupplier(id, data); showToast('Supplier updated', 'success'); }
    else     { await API.createSupplier(data);    showToast('Supplier created', 'success'); }
    closeModal('modal-supplier'); await refreshBaseLookups(); loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to save', 'error'); }
};
window.deleteSupplierItem = async (id) => {
  if (!confirm('Delete this supplier?')) return;
  try { await API.deleteSupplier(id); showToast('Supplier deleted', 'success'); await refreshBaseLookups(); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to delete', 'error'); }
};
window.viewSupplierProducts = async (id, name) => {
  try {
    const products = await API.getSupplierProducts(id);
    document.getElementById('supplier-products-title').textContent = `Catalog supplied by ${name}`;
    document.getElementById('supplier-products-list').innerHTML = !products?.length
      ? `<div class="py-8 text-center text-[#8B7B74]">No products mapped to this vendor.</div>`
      : `<table class="w-full text-left text-xs">
          <thead class="text-[#8B7B74] uppercase border-b border-[#C8B8A8]">
            <tr><th class="py-2 px-3">SKU</th><th class="py-2 px-3">Product</th><th class="py-2 px-3 text-right">Unit Price</th><th class="py-2 px-3 text-right">Reorder</th></tr>
          </thead>
          <tbody class="divide-y divide-[#C8B8A8]/60">
            ${products.map(p => `
              <tr class="hover:bg-[#F7F4EF]/60">
                <td class="py-2.5 px-3 font-mono font-medium text-[#7B4F8A]">${esc(p.sku)}</td>
                <td class="py-2.5 px-3 font-semibold text-[#2C221E]">${esc(p.name)}</td>
                <td class="py-2.5 px-3 text-right font-mono text-green-700 font-bold">$${parseFloat(p.unit_price || 0).toFixed(2)}</td>
                <td class="py-2.5 px-3 text-right text-[#8B7B74]">${p.reorder_level}</td>
              </tr>`).join('')}
          </tbody>
        </table>`;
    openModal('modal-supplier-products');
  } catch (err) { showToast('Failed to fetch supplier products', 'error'); }
};

// ── Purchase Order Actions ────────────────────────────────────────────────────
window.openCreatePOModal = async () => {
  await refreshBaseLookups();
  document.getElementById('po-supplier-id').innerHTML  = state.suppliers.map(s => `<option value="${s.supplier_id}">${esc(s.name)}</option>`).join('');
  document.getElementById('po-warehouse-id').innerHTML = state.warehouses.map(w => `<option value="${w.warehouse_id}">${esc(w.name)}</option>`).join('');
  document.getElementById('po-items-container').innerHTML = '';
  window.addPOLineItem();
  openModal('modal-create-po');
};
window.addPOLineItem = () => {
  const container = document.getElementById('po-items-container');
  const rowId = `po-row-${Date.now()}`;
  const row = document.createElement('div');
  row.id = rowId;
  row.className = 'grid grid-cols-12 gap-3 items-end p-3 bg-[#F7F4EF] border border-[#C8B8A8] rounded-xl po-line-item';
  row.innerHTML = `
    <div class="col-span-5">
      <label class="block text-[11px] font-medium text-[#8B7B74] mb-1">Product</label>
      <select class="w-full bg-[#EAE0D5] border border-[#C8B8A8] text-[#2C221E] text-xs rounded-lg px-2.5 py-1.5 po-item-product" onchange="window.updatePOPrice(this)">
        ${state.products.map(p => `<option value="${p.product_id}" data-price="${p.unit_price}">${esc(p.name)} (${esc(p.sku)})</option>`).join('')}
      </select>
    </div>
    <div class="col-span-3">
      <label class="block text-[11px] font-medium text-[#8B7B74] mb-1">Qty</label>
      <input type="number" min="1" value="10" class="w-full bg-[#EAE0D5] border border-[#C8B8A8] text-[#2C221E] text-xs rounded-lg px-2.5 py-1.5 po-item-qty" oninput="window.calcPOTotal()" />
    </div>
    <div class="col-span-3">
      <label class="block text-[11px] font-medium text-[#8B7B74] mb-1">Unit Cost ($)</label>
      <input type="number" step="0.01" min="0" value="${state.products[0]?.unit_price || '0.00'}" class="w-full bg-[#EAE0D5] border border-[#C8B8A8] text-[#2C221E] text-xs rounded-lg px-2.5 py-1.5 po-item-cost" oninput="window.calcPOTotal()" />
    </div>
    <div class="col-span-1 flex justify-end">
      <button type="button" onclick="document.getElementById('${rowId}').remove(); window.calcPOTotal();" class="p-1.5 text-[#8B7B74] hover:text-red-700 hover:bg-red-100 rounded-lg transition">
        <i data-lucide="trash-2" class="w-4 h-4"></i>
      </button>
    </div>`;
  container.appendChild(row);
  lucide.createIcons({ root: row });
  window.calcPOTotal();
};
window.updatePOPrice = (sel) => {
  const price = sel.options[sel.selectedIndex]?.dataset.price || '0.00';
  const cost = sel.closest('.po-line-item')?.querySelector('.po-item-cost');
  if (cost) cost.value = price;
  window.calcPOTotal();
};
window.calcPOTotal = () => {
  let total = 0;
  document.querySelectorAll('.po-line-item').forEach(r => {
    total += (parseFloat(r.querySelector('.po-item-qty').value) || 0) * (parseFloat(r.querySelector('.po-item-cost').value) || 0);
  });
  const el = document.getElementById('po-total-display');
  if (el) el.textContent = `$${total.toFixed(2)}`;
};
window.handleCreatePOSubmit = async (e) => {
  e.preventDefault();
  const items = [];
  document.querySelectorAll('.po-line-item').forEach(r => {
    const product_id = parseInt(r.querySelector('.po-item-product').value);
    const quantity   = parseInt(r.querySelector('.po-item-qty').value);
    const unit_cost  = parseFloat(r.querySelector('.po-item-cost').value);
    if (product_id && quantity > 0 && !isNaN(unit_cost)) items.push({ product_id, quantity, unit_cost });
  });
  if (!items.length) { showToast('Add at least one line item', 'warning'); return; }
  try {
    const res = await API.createPurchaseOrder({
      supplier_id:  parseInt(document.getElementById('po-supplier-id').value),
      warehouse_id: parseInt(document.getElementById('po-warehouse-id').value),
      items,
    });
    showToast(`Purchase Order #PO-${res.po_id} created`, 'success');
    closeModal('modal-create-po'); loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to create PO', 'error'); }
};
window.viewPODetails = async (poId) => {
  try {
    const po = await API.getPurchaseOrder(poId);
    const total = (po.items || []).reduce((s, i) => s + parseFloat(i.unit_cost) * i.quantity, 0);
    document.getElementById('po-details-title').textContent = `Purchase Order #PO-${po.po_id}`;
    document.getElementById('po-details-content').innerHTML = `
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4 bg-[#F7F4EF] p-4 rounded-xl border border-[#C8B8A8] text-xs">
          <div><div class="text-[#8B7B74]">Supplier</div><div class="font-bold text-[#2C221E] text-sm mt-0.5">${esc(po.supplier_name)}</div></div>
          <div><div class="text-[#8B7B74]">Receiving Warehouse</div><div class="font-bold text-[#2C221E] text-sm mt-0.5">${esc(po.warehouse_name)}</div></div>
          <div><div class="text-[#8B7B74]">Order Date</div><div class="font-medium text-[#5C4A42] mt-0.5">${fmtDate(po.order_date)}</div></div>
          <div><div class="text-[#8B7B74]">Status</div><div class="mt-0.5">${orderStatusBadge(po.status)}</div></div>
        </div>
        <table class="w-full text-left text-xs">
          <thead class="text-[#8B7B74] uppercase border-b border-[#C8B8A8]">
            <tr><th class="py-2">SKU</th><th class="py-2">Product</th><th class="py-2 text-right">Qty</th><th class="py-2 text-right">Unit Cost</th><th class="py-2 text-right">Subtotal</th></tr>
          </thead>
          <tbody class="divide-y divide-[#C8B8A8]/60">
            ${(po.items || []).map(i => `
              <tr>
                <td class="py-2.5 font-mono text-[#C86D51]">${esc(i.sku)}</td>
                <td class="py-2.5 font-medium text-[#2C221E]">${esc(i.product_name)}</td>
                <td class="py-2.5 text-right font-mono">${i.quantity}</td>
                <td class="py-2.5 text-right font-mono">$${parseFloat(i.unit_cost).toFixed(2)}</td>
                <td class="py-2.5 text-right font-mono font-bold text-[#2C221E]">$${(i.quantity * parseFloat(i.unit_cost)).toFixed(2)}</td>
              </tr>`).join('')}
          </tbody>
          <tfoot class="border-t border-[#C8B8A8]">
            <tr><td colspan="4" class="py-3 text-right font-bold text-[#5C4A42]">Total Inbound Value:</td>
            <td class="py-3 text-right font-mono font-bold text-green-700 text-sm">$${total.toFixed(2)}</td></tr>
          </tfoot>
        </table>
      </div>`;
    openModal('modal-po-details');
  } catch (err) { showToast('Failed to load PO details', 'error'); }
};
window.receivePurchaseOrderAction = async (id) => {
  if (!confirm(`Mark #PO-${id} as RECEIVED? This will increment warehouse stock.`)) return;
  try { await API.receivePurchaseOrder(id); showToast(`PO #PO-${id} received & inventory updated!`, 'success'); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to receive PO', 'error'); }
};
window.cancelPurchaseOrderAction = async (id) => {
  if (!confirm(`Cancel #PO-${id}?`)) return;
  try { await API.updatePurchaseOrderStatus(id, 'cancelled'); showToast(`PO #PO-${id} cancelled`, 'info'); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to cancel PO', 'error'); }
};

// ── Sales Order Actions ───────────────────────────────────────────────────────
window.openCreateSOModal = async () => {
  await refreshBaseLookups();
  document.getElementById('so-warehouse-id').innerHTML = state.warehouses.map(w => `<option value="${w.warehouse_id}">${esc(w.name)}</option>`).join('');
  document.getElementById('so-customer-name').value = '';
  document.getElementById('so-items-container').innerHTML = '';
  window.addSOLineItem();
  openModal('modal-create-so');
};
window.addSOLineItem = () => {
  const container = document.getElementById('so-items-container');
  const rowId = `so-row-${Date.now()}`;
  const row = document.createElement('div');
  row.id = rowId;
  row.className = 'grid grid-cols-12 gap-3 items-end p-3 bg-[#F7F4EF] border border-[#C8B8A8] rounded-xl so-line-item';
  row.innerHTML = `
    <div class="col-span-5">
      <label class="block text-[11px] font-medium text-[#8B7B74] mb-1">Product</label>
      <select class="w-full bg-[#EAE0D5] border border-[#C8B8A8] text-[#2C221E] text-xs rounded-lg px-2.5 py-1.5 so-item-product" onchange="window.updateSOPrice(this)">
        ${state.products.map(p => `<option value="${p.product_id}" data-price="${p.unit_price}">${esc(p.name)} (${esc(p.sku)})</option>`).join('')}
      </select>
    </div>
    <div class="col-span-3">
      <label class="block text-[11px] font-medium text-[#8B7B74] mb-1">Qty</label>
      <input type="number" min="1" value="1" class="w-full bg-[#EAE0D5] border border-[#C8B8A8] text-[#2C221E] text-xs rounded-lg px-2.5 py-1.5 so-item-qty" oninput="window.calcSOTotal()" />
    </div>
    <div class="col-span-3">
      <label class="block text-[11px] font-medium text-[#8B7B74] mb-1">Unit Price ($)</label>
      <input type="number" step="0.01" min="0" value="${state.products[0]?.unit_price || '0.00'}" class="w-full bg-[#EAE0D5] border border-[#C8B8A8] text-[#2C221E] text-xs rounded-lg px-2.5 py-1.5 so-item-price" oninput="window.calcSOTotal()" />
    </div>
    <div class="col-span-1 flex justify-end">
      <button type="button" onclick="document.getElementById('${rowId}').remove(); window.calcSOTotal();" class="p-1.5 text-[#8B7B74] hover:text-red-700 hover:bg-red-100 rounded-lg transition">
        <i data-lucide="trash-2" class="w-4 h-4"></i>
      </button>
    </div>`;
  container.appendChild(row);
  lucide.createIcons({ root: row });
  window.calcSOTotal();
};
window.updateSOPrice = (sel) => {
  const price = sel.options[sel.selectedIndex]?.dataset.price || '0.00';
  const priceInput = sel.closest('.so-line-item')?.querySelector('.so-item-price');
  if (priceInput) priceInput.value = price;
  window.calcSOTotal();
};
window.calcSOTotal = () => {
  let total = 0;
  document.querySelectorAll('.so-line-item').forEach(r => {
    total += (parseFloat(r.querySelector('.so-item-qty').value) || 0) * (parseFloat(r.querySelector('.so-item-price').value) || 0);
  });
  const el = document.getElementById('so-total-display');
  if (el) el.textContent = `$${total.toFixed(2)}`;
};
window.handleCreateSOSubmit = async (e) => {
  e.preventDefault();
  const customer_name = document.getElementById('so-customer-name').value.trim();
  if (!customer_name) { showToast('Please enter customer name', 'warning'); return; }
  const items = [];
  document.querySelectorAll('.so-line-item').forEach(r => {
    const product_id = parseInt(r.querySelector('.so-item-product').value);
    const quantity   = parseInt(r.querySelector('.so-item-qty').value);
    const unit_price = parseFloat(r.querySelector('.so-item-price').value);
    if (product_id && quantity > 0 && !isNaN(unit_price)) items.push({ product_id, quantity, unit_price });
  });
  if (!items.length) { showToast('Add at least one line item', 'warning'); return; }
  try {
    const res = await API.createSalesOrder({
      customer_name, warehouse_id: parseInt(document.getElementById('so-warehouse-id').value), items,
    });
    showToast(`Sales Order #SO-${res.so_id} created`, 'success');
    closeModal('modal-create-so'); loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to create SO', 'error'); }
};
window.viewSODetails = async (soId) => {
  try {
    const so = await API.getSalesOrder(soId);
    const total = (so.items || []).reduce((s, i) => s + parseFloat(i.unit_price) * i.quantity, 0);
    document.getElementById('so-details-title').textContent = `Sales Order #SO-${so.so_id}`;
    document.getElementById('so-details-content').innerHTML = `
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4 bg-[#F7F4EF] p-4 rounded-xl border border-[#C8B8A8] text-xs">
          <div><div class="text-[#8B7B74]">Customer</div><div class="font-bold text-[#2C221E] text-sm mt-0.5">${esc(so.customer_name)}</div></div>
          <div><div class="text-[#8B7B74]">Fulfillment Warehouse</div><div class="font-bold text-[#2C221E] text-sm mt-0.5">${esc(so.warehouse_name)}</div></div>
          <div><div class="text-[#8B7B74]">Order Date</div><div class="font-medium text-[#5C4A42] mt-0.5">${fmtDate(so.order_date)}</div></div>
          <div><div class="text-[#8B7B74]">Status</div><div class="mt-0.5">${orderStatusBadge(so.status)}</div></div>
        </div>
        ${so.shipment ? `
          <div class="p-3.5 bg-[#C86D51]/10 border border-[#C86D51]/30 rounded-xl text-xs space-y-1.5">
            <div class="flex justify-between items-center">
              <span class="font-bold text-[#C86D51] flex items-center gap-1.5">
                <i data-lucide="truck" class="w-4 h-4"></i> Shipment #SH-${so.shipment.shipment_id}
              </span>
              ${shipStatusBadge(so.shipment.status)}
            </div>
            <div class="text-[#8B7B74]">Carrier: <strong class="text-[#2C221E]">${esc(so.shipment.carrier || 'Pending')}</strong></div>
            <div class="text-[#8B7B74]">Tracking: <strong class="font-mono text-[#C86D51]">${esc(so.shipment.tracking_number || 'Pending')}</strong></div>
          </div>` : ''}
        <table class="w-full text-left text-xs">
          <thead class="text-[#8B7B74] uppercase border-b border-[#C8B8A8]">
            <tr><th class="py-2">SKU</th><th class="py-2">Product</th><th class="py-2 text-right">Qty</th><th class="py-2 text-right">Unit Price</th><th class="py-2 text-right">Subtotal</th></tr>
          </thead>
          <tbody class="divide-y divide-[#C8B8A8]/60">
            ${(so.items || []).map(i => `
              <tr>
                <td class="py-2.5 font-mono text-[#7B4F8A]">${esc(i.sku)}</td>
                <td class="py-2.5 font-medium text-[#2C221E]">${esc(i.product_name)}</td>
                <td class="py-2.5 text-right font-mono">${i.quantity}</td>
                <td class="py-2.5 text-right font-mono">$${parseFloat(i.unit_price).toFixed(2)}</td>
                <td class="py-2.5 text-right font-mono font-bold text-[#2C221E]">$${(i.quantity * parseFloat(i.unit_price)).toFixed(2)}</td>
              </tr>`).join('')}
          </tbody>
          <tfoot class="border-t border-[#C8B8A8]">
            <tr><td colspan="4" class="py-3 text-right font-bold text-[#5C4A42]">Total Order Amount:</td>
            <td class="py-3 text-right font-mono font-bold text-[#C86D51] text-sm">$${total.toFixed(2)}</td></tr>
          </tfoot>
        </table>
      </div>`;
    openModal('modal-so-details');
  } catch (err) { showToast('Failed to load SO details', 'error'); }
};
window.fulfillSalesOrderAction = async (id) => {
  if (!confirm(`Fulfill #SO-${id}? Stock will be deducted and a shipment created.`)) return;
  try {
    const res = await API.fulfillSalesOrder(id);
    showToast(`Order #SO-${id} fulfilled! Shipment #SH-${res.shipment.shipment_id} created.`, 'success');
    loadActiveTabContent();
  } catch (err) {
    if (err.data?.shortages) {
      const details = err.data.shortages.map(s => `Product #${s.product_id}: need ${s.requested}, have ${s.available}`).join('; ');
      showToast(`Stock shortage: ${details}`, 'error', 6000);
    } else showToast(err.message || 'Failed to fulfill SO', 'error');
  }
};
window.cancelSalesOrderAction = async (id) => {
  if (!confirm(`Cancel #SO-${id}?`)) return;
  try { await API.cancelSalesOrder(id); showToast(`SO #SO-${id} cancelled`, 'info'); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to cancel', 'error'); }
};

// ── Shipment Actions ──────────────────────────────────────────────────────────
window.openShipModal = (id) => {
  document.getElementById('ship-id').value       = id;
  document.getElementById('ship-carrier').value  = 'FedEx Express';
  document.getElementById('ship-tracking').value = `TRK-${Math.floor(100000000 + Math.random() * 900000000)}`;
  openModal('modal-ship');
};
window.handleShipSubmit = async (e) => {
  e.preventDefault();
  const id             = document.getElementById('ship-id').value;
  const carrier        = document.getElementById('ship-carrier').value.trim();
  const tracking_number = document.getElementById('ship-tracking').value.trim();
  try {
    await API.markShipped(id, { carrier, tracking_number });
    showToast(`Shipment #SH-${id} dispatched! Tracking: ${tracking_number}`, 'success');
    closeModal('modal-ship'); loadActiveTabContent();
  } catch (err) { showToast(err.message || 'Failed to dispatch', 'error'); }
};
window.markDeliveredAction = async (id) => {
  if (!confirm(`Mark shipment #SH-${id} as DELIVERED?`)) return;
  try { await API.markDelivered(id); showToast(`Shipment #SH-${id} delivered!`, 'success'); loadActiveTabContent(); }
  catch (err) { showToast(err.message || 'Failed to mark delivered', 'error'); }
};

// ── Formatting & Badge Helpers ────────────────────────────────────────────────
function esc(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
function fmtDate(dateStr) {
  if (!dateStr) return 'N/A';
  try { return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return dateStr; }
}
function orderStatusBadge(status) {
  const map = {
    received:  'badge-success',  fulfilled: 'badge-success',
    pending:   'badge-warning',  cancelled: 'badge-danger',
  };
  const icons = { received: 'check-circle', fulfilled: 'check-circle', pending: 'clock', cancelled: 'x-circle' };
  return `<span class="badge ${map[status] || 'badge-gray'}"><i data-lucide="${icons[status] || 'circle'}" class="w-3 h-3"></i> ${status}</span>`;
}
function shipStatusBadge(status) {
  const map   = { delivered: 'badge-success', shipped: 'badge-info', preparing: 'badge-warning' };
  const icons = { delivered: 'package-check', shipped: 'truck', preparing: 'package' };
  const labels = { delivered: 'Delivered', shipped: 'In Transit', preparing: 'Preparing' };
  return `<span class="badge ${map[status] || 'badge-gray'}"><i data-lucide="${icons[status] || 'circle'}" class="w-3 h-3"></i> ${labels[status] || status}</span>`;
}

// ── Initialization ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      if (link.dataset.tab) switchTab(link.dataset.tab);
    });
  });

  const globalFilter = document.getElementById('global-warehouse-filter');
  if (globalFilter) {
    globalFilter.addEventListener('change', (e) => {
      state.selectedWarehouseFilter = e.target.value;
      loadActiveTabContent();
    });
  }

  await refreshBaseLookups();
  switchTab('dashboard');
});
