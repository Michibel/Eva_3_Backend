/**
 * DULCE ARTE - Main JavaScript Module
 * Modular JS for API, UI, Charts, Forms, Kanban, Signature
 */

// ========================================
// API MODULE
// ========================================
const API = (function() {
  const API_BASE = '/api/v1/';
  let accessToken = null;
  let refreshToken = null;

  // Initialize tokens from localStorage immediately
  function init() {
    accessToken = localStorage.getItem('access_token');
    refreshToken = localStorage.getItem('refresh_token');
  }
  init();

  // Get current access token
  function getAccessToken() {
    return accessToken;
  }

  // Set tokens
  function setTokens(access, refresh) {
    accessToken = access;
    refreshToken = refresh;
    if (access) localStorage.setItem('access_token', access);
    if (refresh) localStorage.setItem('refresh_token', refresh);
  }

  // Clear tokens
  function clearTokens() {
    accessToken = null;
    refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  // Helper to get cookies
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Build headers
  function buildHeaders(options = {}) {
    const headers = { ...options.headers };
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    const csrf = getCookie('csrftoken');
    if (csrf && !headers['X-CSRFToken']) {
      headers['X-CSRFToken'] = csrf;
    }
    return headers;
  }

  // Main fetch wrapper with auto-refresh
  async function fetch(endpoint, options = {}) {
    const headers = buildHeaders(options);
    const url = `${API_BASE}${endpoint}`;

    const response = await window.fetch(url, {
      ...options,
      headers,
      credentials: 'include',
    });

    // Handle 401 - token expired
    if (response.status === 401) {
      let refreshed = await refreshAccessToken();
      if (!refreshed) {
        // Try obtaining new tokens from existing Django session
        await initJWTTokens();
        if (accessToken) refreshed = true;
      }
      if (refreshed) {
        // Retry original request
        const newHeaders = buildHeaders(options);
        return window.fetch(url, { ...options, headers: newHeaders, credentials: 'include' });
      }
      // If we're not already on login page, redirect to login
      if (!window.location.pathname.includes('/login')) {
        clearTokens();
        window.location.href = '/login/';
      }
      return response;
    }

    return response;
  }

  // Refresh access token
  async function refreshAccessToken() {
    if (!refreshToken) return false;

    try {
      const response = await window.fetch(`${API_BASE}auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        setTokens(data.access, data.refresh);
        return true;
      }
    } catch (e) {
      console.error('Token refresh failed:', e);
    }
    return false;
  }

  let initTokensPromise = null;

  // Initialize JWT tokens from session (after Django login)
  async function initJWTTokens() {
    if (initTokensPromise) return initTokensPromise;

    initTokensPromise = (async () => {
      // Check if we already have valid tokens
      if (accessToken && refreshToken) {
        try {
          const testResponse = await window.fetch(`${API_BASE}users/me/`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
          });
          if (testResponse.ok) return;
        } catch (e) {
          // Token might be expired
        }
      }

      // Try to get tokens from session via API
      try {
        const response = await window.fetch(`${API_BASE}accounts/jwt-tokens/`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
        });
        if (response.ok) {
          const data = await response.json();
          if (data.access && data.refresh) {
            setTokens(data.access, data.refresh);
          }
        }
      } catch (e) {
        console.debug('Could not get tokens from session:', e);
      }
    })().finally(() => {
      initTokensPromise = null;
    });

    return initTokensPromise;
  }

  // Convenience methods
  const methods = ['get', 'post', 'put', 'patch', 'delete'];
  const api = { init, getAccessToken, setTokens, clearTokens, fetch, initJWTTokens };

  methods.forEach(method => {
    api[method] = (endpoint, data, options = {}) => {
      const opts = { method: method.toUpperCase(), ...options };
      if (data && method !== 'get' && method !== 'delete') {
        opts.body = JSON.stringify(data);
      }
      return api.fetch(endpoint, opts);
    };
  });

  // FormData support for file uploads
  api.upload = (endpoint, formData, options = {}) => {
    const headers = {};
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    // Don't set Content-Type for FormData - browser sets it with boundary
    return api.fetch(endpoint, {
      method: 'POST',
      body: formData,
      headers: { ...headers, ...options.headers },
      ...options,
    });
  };

  return api;
})();

// ========================================
// UI MODULE
// ========================================
const UI = (function() {
  // Toast notifications
  function showToast(message, type = 'info', duration = 5000) {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <div class="toast-body">${message}</div>
      <button class="toast-close" aria-label="Cerrar">&times;</button>
    `;

    container.appendChild(toast);

    // Auto remove
    const timeout = setTimeout(() => removeToast(toast), duration);

    // Manual close
    toast.querySelector('.toast-close').addEventListener('click', () => {
      clearTimeout(timeout);
      removeToast(toast);
    });

    // Animate in
    requestAnimationFrame(() => toast.classList.add('show'));
  }

  function removeToast(toast) {
    toast.classList.add('hiding');
    toast.addEventListener('transitionend', () => toast.remove());
  }

  // Loading states
  function showLoading(element, text = 'Cargando...') {
    if (!element) return;
    element.disabled = true;
    element.dataset.originalHtml = element.innerHTML;
    element.innerHTML = `<span class="spinner spinner-sm me-2"></span>${text}`;
  }

  function hideLoading(element) {
    if (!element) return;
    element.disabled = false;
    if (element.dataset.originalHtml) {
      element.innerHTML = element.dataset.originalHtml;
      delete element.dataset.originalHtml;
    }
  }

  // Modal helpers
  function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    const overlay = modal.closest('.modal-overlay') || createModalOverlay(modal);
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
    // Focus first focusable element
    const focusable = modal.querySelector('input, select, textarea, button:not([disabled])');
    if (focusable) focusable.focus();
  }

  function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    const overlay = modal.closest('.modal-overlay');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  function createModalOverlay(modal) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Close on backdrop click
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) hideModal(modal.id);
    });

    // Close on Escape
    document.addEventListener('keydown', function escHandler(e) {
      if (e.key === 'Escape') {
        hideModal(modal.id);
        document.removeEventListener('keydown', escHandler);
      }
    });

    return overlay;
  }

  // Confirm dialog
  function confirm(message, title = 'Confirmar') {
    return new Promise((resolve) => {
      const modal = document.createElement('div');
      modal.className = 'modal';
      modal.innerHTML = `
        <div class="modal-header">
          <h5 class="modal-title">${title}</h5>
        </div>
        <div class="modal-body">
          <p>${message}</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" data-action="cancel">Cancelar</button>
          <button class="btn btn-danger" data-action="confirm">Confirmar</button>
        </div>
      `;
      const overlay = createModalOverlay(modal);
      overlay.classList.add('show');

      modal.querySelector('[data-action="cancel"]').onclick = () => {
        hideModal(modal.id);
        resolve(false);
      };
      modal.querySelector('[data-action="confirm"]').onclick = () => {
        hideModal(modal.id);
        resolve(true);
      };
    });
  }

  // Helper to parse multiple date formats safely (ISO, DD/MM/YYYY, DD/MM/YYYY HH:MM)
  function parseCustomDate(str) {
    if (!str) return null;
    if (str instanceof Date) return isNaN(str.getTime()) ? null : str;
    if (typeof str !== 'string') return new Date(str);
    const trimmed = str.trim();
    const parts = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?: (\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?/);
    if (parts) {
      const d = parseInt(parts[1], 10);
      const m = parseInt(parts[2], 10) - 1;
      const y = parseInt(parts[3], 10);
      const h = parts[4] ? parseInt(parts[4], 10) : 0;
      const min = parts[5] ? parseInt(parts[5], 10) : 0;
      const s = parts[6] ? parseInt(parts[6], 10) : 0;
      const parsed = new Date(y, m, d, h, min, s);
      return isNaN(parsed.getTime()) ? null : parsed;
    }
    let parsed = new Date(trimmed);
    if (!isNaN(parsed.getTime())) return parsed;
    parsed = new Date(trimmed.replace(' ', 'T'));
    return isNaN(parsed.getTime()) ? null : parsed;
  }

  // Formatters
  function formatCLP(amount) {
    if (amount === null || amount === undefined || amount === '') return '$0';
    const num = typeof amount === 'number' ? amount : (parseFloat(String(amount).replace(/[^0-9.-]+/g, '')) || 0);
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num);
  }

  function formatNumber(amount) {
    if (amount === null || amount === undefined || amount === '') return '0';
    const num = typeof amount === 'number' ? amount : (parseFloat(String(amount).replace(/[^0-9.-]+/g, '')) || 0);
    return new Intl.NumberFormat('es-CL').format(num);
  }

  function formatDate(dateString) {
    if (!dateString) return '—';
    const date = parseCustomDate(dateString);
    if (!date) {
      if (typeof dateString === 'string' && dateString.includes('/')) {
        return dateString.split(' ')[0];
      }
      return String(dateString);
    }
    return new Intl.DateTimeFormat('es-CL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(date);
  }

  function formatDateTime(dateString) {
    if (!dateString) return '—';
    const date = parseCustomDate(dateString);
    if (!date) return String(dateString);
    return new Intl.DateTimeFormat('es-CL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Status helpers
  const statusConfig = {
    orders: {
      COTIZACION: { label: 'Cotización', color: 'warning' },
      CONFIRMADO: { label: 'Confirmado', color: 'info' },
      EN_PRODUCCION: { label: 'En Producción', color: 'primary' },
      LISTO: { label: 'Listo', color: 'success' },
      DESPACHADO: { label: 'Despachado', color: 'info' },
      ENTREGADO: { label: 'Entregado', color: 'success' },
      CANCELADO: { label: 'Cancelado', color: 'danger' },
      RECHAZADO: { label: 'Rechazado', color: 'danger' },
    },
    payments: {
      PENDIENTE: { label: 'Pendiente', color: 'warning' },
      PAGADO_PARCIAL: { label: 'Parcial', color: 'info' },
      PAGADO_TOTAL: { label: 'Pagado', color: 'success' },
    },
    dispatch: {
      PENDIENTE: { label: 'Pendiente', color: 'secondary' },
      EN_RUTA: { label: 'En Ruta', color: 'info' },
      ENTREGADO: { label: 'Entregado', color: 'success' },
      FALLIDO: { label: 'Fallido', color: 'danger' },
    },
    route: {
      PROGRAMADA: { label: 'Programada', color: 'warning' },
      EN_CURSO: { label: 'En Curso', color: 'info' },
      COMPLETADA: { label: 'Completada', color: 'success' },
      CANCELADA: { label: 'Cancelada', color: 'danger' },
    },
    kanban: {
      RECIBIDO: { label: 'Recibido', color: 'warning' },
      EN_PREPARACION: { label: 'En Preparación', color: 'info' },
      HORNEADO_DECORADO: { label: 'Horneado/Decorad', color: 'warning' },
      CONTROL_CALIDAD: { label: 'Control Calidad', color: 'danger' },
      LISTO: { label: 'Listo', color: 'success' },
    },
    stock: {
      OK: { label: 'OK', color: 'success' },
      BAJO_STOCK: { label: 'Stock Bajo', color: 'warning' },
      SIN_STOCK: { label: 'Sin Stock', color: 'danger' },
    },
  };

  function getStatusBadge(status, type = 'orders') {
    const config = statusConfig[type] || statusConfig.orders;
    const cfg = config[status] || { label: status, color: 'secondary' };
    return `<span class="badge badge-${cfg.color}">${cfg.label}</span>`;
  }

  function getStatusColor(status, type = 'orders') {
    const config = statusConfig[type] || statusConfig.orders;
    return config[status]?.color || 'secondary';
  }

  function getStatusLabel(status, type = 'orders') {
    const config = statusConfig[type] || statusConfig.orders;
    return config[status]?.label || status;
  }

  // Skeleton loading
  function showSkeleton(container, type = 'card', count = 3) {
    const skeletons = {
      card: '<div class="skeleton skeleton-card"></div>',
      row: '<div class="skeleton skeleton-text" style="width: 60%;"></div><div class="skeleton skeleton-text" style="width: 40%;"></div>',
      list: '<div class="skeleton" style="height: 60px; width: 100%;"></div>',
      table: Array.from({ length: count }, () =>
        '<tr><td><div class="skeleton skeleton-text"></div></td><td><div class="skeleton skeleton-text" style="width: 40%"></div></td><td><div class="skeleton skeleton-text" style="width: 30%"></div></td><td><div class="skeleton skeleton-text" style="width: 50%"></div></td></tr>'
      ).join(''),
    };
    container.innerHTML = Array.from({ length: count }, () => skeletons[type] || skeletons.card).join('');
  }

  // Empty state
  function showEmptyState(container, options = {}) {
    const {
      icon = 'icon-box',
      title = 'No hay datos',
      message = 'No se encontraron registros',
      actionText,
      actionCallback,
    } = options;

    container.innerHTML = `
      <div class="text-center py-5">
        <i class="bi ${icon} fs-1 text-muted mb-3" style="color: var(--color-dorado-claro) !important;"></i>
        <h5 class="text-muted">${escapeHtml(title)}</h5>
        <p class="text-muted small">${escapeHtml(message)}</p>
        ${actionText ? `<button class="btn btn-primary mt-3" onclick="${actionCallback}">${escapeHtml(actionText)}</button>` : ''}
      </div>
    `;
  }

  // Debounce
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Throttle
  function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }

  return {
    showToast,
    showLoading,
    hideLoading,
    showModal,
    hideModal,
    confirm,
    formatCLP,
    formatNumber,
    formatDate,
    formatDateTime,
    parseCustomDate,
    escapeHtml,
    getStatusBadge,
    getStatusColor,
    getStatusLabel,
    showSkeleton,
    showEmptyState,
    debounce,
    throttle,
  };
})();

// ========================================
// CHARTS MODULE (Chart.js wrapper)
// ========================================
const Charts = (function() {
  const colorPalette = [
    '#5D2E0C', '#8B4513', '#C9A86C', '#D4AF37', '#E8D5B7',
    '#2D6A4F', '#3A6B8C', '#B8860B', '#8B2635', '#6B4E3D',
  ];

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          font: { family: "'DM Sans', sans-serif", size: 12 },
          padding: 20,
          usePointStyle: true,
        },
      },
      tooltip: {
        backgroundColor: '#2D1B0E',
        titleFont: { family: "'Playfair Display', serif", size: 14 },
        bodyFont: { family: "'DM Sans', sans-serif", size: 12 },
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { family: "'DM Sans', sans-serif", size: 11 } },
      },
      y: {
        grid: { color: '#F5EDE3' },
        ticks: { font: { family: "'DM Sans', sans-serif", size: 11 } },
      },
    },
  };

  let charts = {};

  function create(ctx, type, data, options = {}) {
    const config = {
      type,
      data: {
        ...data,
        datasets: data.datasets.map((ds, i) => ({
          ...ds,
          borderColor: ds.borderColor || colorPalette[i % colorPalette.length],
          backgroundColor: ds.backgroundColor || colorPalette[i % colorPalette.length] + '33',
          borderWidth: ds.borderWidth || 2,
          tension: ds.tension ?? 0.4,
          pointRadius: ds.pointRadius ?? 4,
          pointHoverRadius: ds.pointHoverRadius ?? 6,
        })),
      },
      options: { ...defaultOptions, ...options },
    };

    if (charts[ctx.id]) {
      charts[ctx.id].destroy();
    }
    charts[ctx.id] = new Chart(ctx, config);
    return charts[ctx.id];
  }

  function destroy(canvasId) {
    if (charts[canvasId]) {
      charts[canvasId].destroy();
      delete charts[canvasId];
    }
  }

  function update(canvasId, newData) {
    if (charts[canvasId]) {
      charts[canvasId].data = newData;
      charts[canvasId].update();
    }
  }

  // Chart types
  function line(canvasId, labels, datasets, options = {}) {
    return create(document.getElementById(canvasId), 'line', { labels, datasets }, options);
  }

  function bar(canvasId, labels, datasets, options = {}) {
    return create(document.getElementById(canvasId), 'bar', { labels, datasets }, {
      ...options,
      scales: {
        ...defaultOptions.scales,
        y: { ...defaultOptions.scales.y, beginAtZero: true },
      },
    });
  }

  function doughnut(canvasId, labels, data, options = {}) {
    return create(document.getElementById(canvasId), 'doughnut', {
      labels,
      datasets: [{ data, borderWidth: 0 }],
    }, {
      ...defaultOptions,
      cutout: '70%',
      plugins: { ...defaultOptions.plugins, legend: { position: 'right' } },
    }, options);
  }

  function area(canvasId, labels, datasets, options = {}) {
    return line(canvasId, labels, datasets.map(ds => ({
      ...ds,
      fill: true,
      backgroundColor: ds.backgroundColor || (ds.borderColor || colorPalette[0]) + '33',
    })), options);
  }

  return { line, bar, doughnut, area, update, destroy };
})();

// ========================================
// FORMS MODULE
// ========================================
const Forms = (function() {
  // Initialize form validation (Bootstrap 5)
  function initValidation(formSelector = 'form[novalidate]') {
    document.querySelectorAll(formSelector).forEach(form => {
      form.addEventListener('submit', function(event) {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }
        form.classList.add('was-validated');
      });
    });
  }

  // Handle form submission with API
  async function handleSubmit(form, apiEndpoint, options = {}) {
    const {
      method = 'POST',
      onSuccess,
      onError,
      successMessage = 'Guardado correctamente',
      errorMessage = 'Error al guardar',
      showToast = true,
      resetForm = false,
      closeModal = null,
    } = options;

    const submitBtn = form.querySelector('[type="submit"]');
    const formData = new FormData(form);

    // Check if form has file inputs
    const hasFiles = form.querySelector('input[type="file"]');

    UI.showLoading(submitBtn);

    try {
      let response;
      if (hasFiles) {
        response = await API.upload(apiEndpoint, formData);
      } else {
        // Convert FormData to JSON
        const data = {};
        formData.forEach((value, key) => {
          if (data[key]) {
            if (!Array.isArray(data[key])) data[key] = [data[key]];
            data[key].push(value);
          } else {
            data[key] = value;
          }
        });
        response = await API[method.toLowerCase()](apiEndpoint, data);
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(JSON.stringify(error));
      }

      if (showToast) UI.showToast(successMessage, 'success');
      if (onSuccess) await onSuccess(await response.json());
      if (resetForm) form.reset();
      if (closeModal) UI.hideModal(closeModal);

      form.classList.remove('was-validated');
      return response;
    } catch (error) {
      console.error('Form submit error:', error);
      if (showToast) UI.showToast(errorMessage, 'danger');
      if (onError) onError(error);
      throw error;
    } finally {
      UI.hideLoading(submitBtn);
    }
  }

  // Populate form with data
  function populate(form, data) {
    Object.entries(data).forEach(([key, value]) => {
      const field = form.querySelector(`[name="${key}"]`);
      if (!field) return;

      if (field.type === 'checkbox') {
        field.checked = Boolean(value);
      } else if (field.type === 'radio') {
        const radio = form.querySelector(`[name="${key}"][value="${value}"]`);
        if (radio) radio.checked = true;
      } else if (field.tagName === 'SELECT' && field.multiple) {
        Array.from(field.options).forEach(opt => {
          opt.selected = Array.isArray(value) && value.includes(opt.value);
        });
      } else {
        field.value = value ?? '';
      }
    });
  }

  // Clear form
  function clear(form) {
    form.reset();
    form.classList.remove('was-validated');
  }

  return { initValidation, handleSubmit, populate, clear };
})();

// ========================================
// KANBAN MODULE
// ========================================
const Kanban = (function() {
  let board = null;
  let draggedCard = null;

  function init(boardSelector, options = {}) {
    board = document.querySelector(boardSelector);
    if (!board) return;

    const columns = board.querySelectorAll('.kanban-column');
    columns.forEach(column => {
      const cardsContainer = column.querySelector('.kanban-cards');
      if (!cardsContainer) return;

      // Drag over
      cardsContainer.addEventListener('dragover', handleDragOver);
      cardsContainer.addEventListener('dragleave', handleDragLeave);
      cardsContainer.addEventListener('drop', handleDrop);
      cardsContainer.addEventListener('dragend', handleDragEnd);
    });

    // Make cards draggable
    makeCardsDraggable();

    // Expose API
    board.kanban = {
      refresh: () => makeCardsDraggable(),
      moveCard: moveCard,
    };
  }

  function makeCardsDraggable() {
    if (!board) return;
    board.querySelectorAll('.kanban-card').forEach(card => {
      card.setAttribute('draggable', 'true');
      card.addEventListener('dragstart', handleDragStart);
      card.addEventListener('dragend', handleDragEnd);
    });
  }

  function handleDragStart(e) {
    draggedCard = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', this.dataset.cardId);
  }

  function handleDragEnd(e) {
    this.classList.remove('dragging');
    document.querySelectorAll('.kanban-cards.over').forEach(c => c.classList.remove('over'));
    draggedCard = null;
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    this.classList.add('over');
  }

  function handleDragLeave(e) {
    if (!this.contains(e.relatedTarget)) {
      this.classList.remove('over');
    }
  }

  async function handleDrop(e) {
    e.preventDefault();
    this.classList.remove('over');

    const cardId = e.dataTransfer.getData('text/plain');
    const card = document.querySelector(`.kanban-card[data-card-id="${cardId}"]`);
    if (!card || card === draggedCard) return;

    const columnId = this.closest('.kanban-column').dataset.column;
    await moveCard(cardId, columnId);
  }

  async function moveCard(cardId, newColumn) {
    const card = document.querySelector(`.kanban-card[data-card-id="${cardId}"]`);
    if (!card) return;

    const oldColumn = card.closest('.kanban-column').dataset.column;
    if (oldColumn === newColumn) return;

    // Optimistic UI update
    const targetColumn = board.querySelector(`.kanban-column[data-column="${newColumn}"] .kanban-cards`);
    targetColumn.appendChild(card);

    // Update counts
    updateColumnCounts();

    // API call
    try {
      await API.patch(`production/cards/${cardId}/`, { column: newColumn });
    } catch (error) {
      // Revert on error
      const oldColumnEl = board.querySelector(`.kanban-column[data-column="${oldColumn}"] .kanban-cards`);
      oldColumnEl.appendChild(card);
      updateColumnCounts();
      UI.showToast('Error al mover la tarjeta', 'danger');
    }
  }

  function updateColumnCounts() {
    board.querySelectorAll('.kanban-column').forEach(column => {
      const count = column.querySelectorAll('.kanban-card').length;
      const countEl = column.querySelector('.kanban-column-count');
      if (countEl) countEl.textContent = count;
    });
  }

  return { init };
})();

// ========================================
// SIGNATURE MODULE
// ========================================
const Signature = (function() {
  function init(canvasSelector, options = {}) {
    const canvas = document.querySelector(canvasSelector);
    if (!canvas) return null;

    const pad = canvas.closest('.signature-pad');
    const ctx = canvas.getContext('2d');
    let drawing = false;
    let lastX = 0;
    let lastY = 0;

    // Set canvas size
    function resize() {
      const rect = pad.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      ctx.scale(dpr, dpr);
    }

    resize();
    window.addEventListener('resize', resize);

    // Draw line
    function draw(x, y) {
      ctx.beginPath();
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(x, y);
      ctx.strokeStyle = '#2D1B0E';
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.stroke();
      lastX = x;
      lastY = y;
    }

    // Get coordinates
    function getCoords(e) {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      return {
        x: clientX - rect.left,
        y: clientY - rect.top,
      };
    }

    // Mouse events
    canvas.addEventListener('mousedown', (e) => {
      drawing = true;
      const { x, y } = getCoords(e);
      lastX = x;
      lastY = y;
      pad.classList.add('drawing', 'has-signature');
    });

    canvas.addEventListener('mousemove', (e) => {
      if (!drawing) return;
      const { x, y } = getCoords(e);
      draw(x, y);
    });

    canvas.addEventListener('mouseup', () => {
      drawing = false;
    });

    canvas.addEventListener('mouseleave', () => {
      drawing = false;
    });

    // Touch events
    canvas.addEventListener('touchstart', (e) => {
      e.preventDefault();
      drawing = true;
      const { x, y } = getCoords(e);
      lastX = x;
      lastY = y;
      pad.classList.add('drawing', 'has-signature');
    }, { passive: false });

    canvas.addEventListener('touchmove', (e) => {
      if (!drawing) return;
      e.preventDefault();
      const { x, y } = getCoords(e);
      draw(x, y);
    }, { passive: false });

    canvas.addEventListener('touchend', () => {
      drawing = false;
    });

    // Clear function
    function clear() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pad.classList.remove('has-signature');
    }

    // Get signature as data URL
    function toDataURL(type = 'image/png') {
      return canvas.toDataURL(type);
    }

    // Check if empty
    function isEmpty() {
      const pixelData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      for (let i = 3; i < pixelData.length; i += 4) {
        if (pixelData[i] > 0) return false;
      }
      return true;
    }

    return { clear, toDataURL, isEmpty, canvas, ctx };
  }

  return { init };
})();

// ========================================
// MAIN INITIALIZATION
// ========================================
document.addEventListener('DOMContentLoaded', function() {
  // Initialize API tokens
  API.initJWTTokens();

  // Initialize form validation
  Forms.initValidation();

  // Initialize sidebar toggle
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const mainContent = document.getElementById('mainContent');

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function() {
      sidebar.classList.toggle('show');
      if (sidebarBackdrop) sidebarBackdrop.classList.toggle('show');
    });
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', function() {
      sidebar.classList.remove('show');
      sidebarBackdrop.classList.remove('show');
    });
  }

  // Close sidebar on link click (mobile)
  if (sidebar) {
    sidebar.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', function() {
        if (window.innerWidth < 992) {
          sidebar.classList.remove('show');
          if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');
        }
      });
    });
  }

  // Handle sidebar collapse
  const collapseBtn = document.getElementById('sidebarCollapse');
  if (collapseBtn && sidebar) {
    collapseBtn.addEventListener('click', function() {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    });

    // Restore collapsed state
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      sidebar.classList.add('collapsed');
    }
  }

  // Auto-hide alerts
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Initialize tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // Initialize popovers
  document.querySelectorAll('[data-bs-toggle="popover"]').forEach(el => {
    new bootstrap.Popover(el);
  });

  // Handle logout: clear JWT tokens and storage
  document.querySelectorAll('a[href*="/logout/"], #sidebarLogoutBtn').forEach(btn => {
    btn.addEventListener('click', function() {
      if (API && API.clearTokens) {
        API.clearTokens();
      }
      try {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        sessionStorage.clear();
      } catch (e) {}
    });
  });

  console.log('Dulce Arte JS initialized');
});

// Global apiFetch function for templates that use it
window.apiFetch = function(endpoint, options = {}) {
    return API.fetch(endpoint, options);
};

// Global aliases for UI functions used directly in templates
window.formatCLP = UI.formatCLP;
window.formatNumber = UI.formatNumber;
window.formatDate = UI.formatDate;
window.formatDateTime = UI.formatDateTime;
window.parseCustomDate = UI.parseCustomDate;
window.escapeHtml = UI.escapeHtml;
window.getStatusBadge = UI.getStatusBadge;
window.getStatusColor = UI.getStatusColor;
window.getStatusLabel = UI.getStatusLabel;
window.showToast = UI.showToast;
window.showLoading = UI.showLoading;
window.hideLoading = UI.hideLoading;
window.showModal = UI.showModal;
window.hideModal = UI.hideModal;
window.confirm = UI.confirm;
window.showSkeleton = UI.showSkeleton;
window.showEmptyState = UI.showEmptyState;
window.debounce = UI.debounce;
window.throttle = UI.throttle;

// Export modules to window for global access
window.API = API;
window.UI = UI;
window.Charts = Charts;
window.Forms = Forms;
window.Kanban = Kanban;
window.Signature = Signature;