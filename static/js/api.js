/**
 * API client module for Warehouse Management System
 */

const BASE_URL = window.location.origin;

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers
    }
  };

  try {
    const response = await fetch(url, config);
    let data;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorMsg = (data && data.error) ? data.error : `HTTP error: ${response.status} ${response.statusText}`;
      const err = new Error(errorMsg);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    console.error(`API Error on [${options.method || 'GET'}] ${endpoint}:`, error);
    throw error;
  }
}

export const API = {
  // Health
  checkHealth: () => request('/api/health'),

  // Products
  getProducts: () => request('/api/products'),
  getProduct: (id) => request(`/api/products/${id}`),
  createProduct: (data) => request('/api/products', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id, data) => request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProduct: (id) => request(`/api/products/${id}`, { method: 'DELETE' }),
  getLowStockProducts: () => request('/api/products/reports/low-stock'),

  // Inventory
  getInventory: () => request('/api/inventory'),
  getInventoryItem: (id) => request(`/api/inventory/${id}`),
  createInventoryRecord: (data) => request('/api/inventory', { method: 'POST', body: JSON.stringify(data) }),
  deleteInventoryRecord: (id) => request(`/api/inventory/${id}`, { method: 'DELETE' }),
  adjustStock: (data) => request('/api/inventory/adjust', { method: 'PATCH', body: JSON.stringify(data) }),

  // Warehouses
  getWarehouses: () => request('/api/warehouses'),
  getWarehouse: (id) => request(`/api/warehouses/${id}`),
  createWarehouse: (data) => request('/api/warehouses', { method: 'POST', body: JSON.stringify(data) }),
  updateWarehouse: (id, data) => request(`/api/warehouses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteWarehouse: (id) => request(`/api/warehouses/${id}`, { method: 'DELETE' }),
  getWarehouseStock: (id) => request(`/api/warehouses/${id}/stock`),

  // Suppliers
  getSuppliers: () => request('/api/suppliers'),
  getSupplier: (id) => request(`/api/suppliers/${id}`),
  createSupplier: (data) => request('/api/suppliers', { method: 'POST', body: JSON.stringify(data) }),
  updateSupplier: (id, data) => request(`/api/suppliers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSupplier: (id) => request(`/api/suppliers/${id}`, { method: 'DELETE' }),
  getSupplierProducts: (id) => request(`/api/suppliers/${id}/products`),

  // Purchase Orders
  getPurchaseOrders: () => request('/api/purchase-orders'),
  getPurchaseOrder: (id) => request(`/api/purchase-orders/${id}`),
  createPurchaseOrder: (data) => request('/api/purchase-orders', { method: 'POST', body: JSON.stringify(data) }),
  updatePurchaseOrderStatus: (id, status) => request(`/api/purchase-orders/${id}`, { method: 'PUT', body: JSON.stringify({ status }) }),
  deletePurchaseOrder: (id) => request(`/api/purchase-orders/${id}`, { method: 'DELETE' }),
  receivePurchaseOrder: (id) => request(`/api/purchase-orders/${id}/receive`, { method: 'POST' }),

  // Sales Orders
  getSalesOrders: () => request('/api/sales-orders'),
  getSalesOrder: (id) => request(`/api/sales-orders/${id}`),
  createSalesOrder: (data) => request('/api/sales-orders', { method: 'POST', body: JSON.stringify(data) }),
  deleteSalesOrder: (id) => request(`/api/sales-orders/${id}`, { method: 'DELETE' }),
  cancelSalesOrder: (id) => request(`/api/sales-orders/${id}/cancel`, { method: 'POST' }),
  fulfillSalesOrder: (id) => request(`/api/sales-orders/${id}/fulfill`, { method: 'POST' }),

  // Shipments
  getShipments: () => request('/api/shipments'),
  getShipment: (id) => request(`/api/shipments/${id}`),
  markShipped: (id, data) => request(`/api/shipments/${id}/ship`, { method: 'POST', body: JSON.stringify(data) }),
  markDelivered: (id) => request(`/api/shipments/${id}/deliver`, { method: 'POST' }),

  // Query Lab (SELECT / INSERT / UPDATE catalogue)
  queryLabCatalog: () => request('/api/query-lab/catalog'),
  runSelectQuery: (id, params = {}) => request(`/api/query-lab/select/${id}?${new URLSearchParams(params)}`),
  runDmlQuery: (id, data) => request(`/api/query-lab/dml/${id}`, { method: 'POST', body: JSON.stringify(data) }),
  seedDemoData: () => request('/api/query-lab/seed', { method: 'POST' })
};
