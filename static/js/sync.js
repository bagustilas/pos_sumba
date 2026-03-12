/**
 * POS SUMBA — Sync Manager
 * Auto-sync: langsung kirim ke server saat koneksi tersedia
 */

const SYNC_INTERVAL = 10000; // cek pending tiap 10 detik
let syncTimer = null;
let isSyncing = false;

// ── STATUS KONEKSI ──────────────────────────────────────────

function isOnline() {
  return navigator.onLine;
}

function updateConnectionUI(online) {
  const chip  = document.getElementById('sync-chip');
  const label = document.getElementById('conn-label');
  const text  = document.getElementById('sync-status-text');
  if (!chip) return;

  chip.classList.remove('online', 'offline', 'pending', 'syncing');
  if (online) {
    chip.classList.add('online');
    label.textContent = 'Online';
    if (text) text.textContent = '';
  } else {
    chip.classList.add('offline');
    label.textContent = 'Offline';
    if (text) text.textContent = 'Transaksi disimpan lokal';
  }
}

async function updatePendingBadge() {
  const count = await window.PosDB.countPending();
  const badge = document.getElementById('pending-badge');
  const chip  = document.getElementById('sync-chip');
  const label = document.getElementById('conn-label');
  if (!badge || !chip) return;

  if (count > 0) {
    badge.textContent   = count + ' pending';
    badge.style.display = 'inline-flex';
    if (!chip.classList.contains('syncing') && !chip.classList.contains('offline')) {
      chip.classList.remove('online');
      chip.classList.add('pending');
      label.textContent = 'Menunggu sync';
    }
  } else {
    badge.style.display = 'none';
    if (chip.classList.contains('pending')) {
      chip.classList.remove('pending');
      chip.classList.add(isOnline() ? 'online' : 'offline');
      label.textContent = isOnline() ? 'Online' : 'Offline';
    }
  }
}

// ── AUTO SYNC ───────────────────────────────────────────────

async function syncPendingTransactions() {
  if (isSyncing || !isOnline()) return;

  const pending = await window.PosDB.getPendingTransactions();
  if (!pending.length) return;

  isSyncing = true;

  // Update chip ke state syncing
  const chip  = document.getElementById('sync-chip');
  const label = document.getElementById('conn-label');
  const text  = document.getElementById('sync-status-text');
  if (chip) {
    chip.classList.remove('online', 'offline', 'pending');
    chip.classList.add('syncing');
    label.textContent = 'Syncing';
    text.textContent  = `${pending.length} transaksi...`;
  }

  let successCount = 0;
  let failCount    = 0;

  for (const tx of pending) {
    try {
      const res = await fetch('/api/sync', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          local_id:       tx.local_id,
          items:          tx.items,
          payment_method: tx.payment_method,
          amount_paid:    tx.amount_paid,
          created_at:     tx.created_at,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        await window.PosDB.markTransactionSynced(tx.local_id, data);
        successCount++;
      } else {
        await window.PosDB.markTransactionFailed(tx.local_id, `HTTP ${res.status}`);
        failCount++;
      }
    } catch (err) {
      await window.PosDB.markTransactionFailed(tx.local_id, err.message);
      failCount++;
    }
  }

  isSyncing = false;

  if (successCount > 0 && failCount === 0) {
    // Kembali ke online, bersihkan status
    if (chip) {
      chip.classList.remove('syncing');
      chip.classList.add('online');
      label.textContent = 'Online';
      text.textContent  = `✓ ${successCount} transaksi tersinkron`;
      setTimeout(() => { if (text) text.textContent = ''; }, 4000);
    }
    showToast(`✅ ${successCount} transaksi offline berhasil disinkronkan!`, 'success');
  } else if (failCount > 0) {
    if (chip) {
      chip.classList.remove('syncing');
      chip.classList.add('pending');
      label.textContent = 'Sebagian gagal';
      text.textContent  = `${successCount} OK, ${failCount} gagal`;
    }
  }

  await updatePendingBadge();
}

// ── TOAST ───────────────────────────────────────────────────

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `pos-toast pos-toast-${type}`;
  toast.innerHTML = `
    <span>${msg}</span>
    <button onclick="this.parentElement.remove()"
      style="background:none;border:none;color:inherit;cursor:pointer;font-size:16px;padding:0 0 0 10px;">✕</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity   = '0';
    toast.style.transform = 'translateX(110%)';
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}

// ── SIMPAN TRANSAKSI (OFFLINE-AWARE) ────────────────────────

async function submitTransaction(txData) {
  if (isOnline()) {
    try {
      const res = await fetch('/api/transaksi', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(txData),
      });
      if (res.ok) {
        const data = await res.json();
        return { success: true, data, offline: false };
      }
      throw new Error(`Server error ${res.status}`);
    } catch (err) {
      console.warn('[POS] Online gagal, simpan offline:', err);
    }
  }

  // Simpan ke IndexedDB — akan auto-sync saat online
  const localId = await window.PosDB.savePendingTransaction(txData);
  await updatePendingBadge();

  showToast('📶 Offline — Transaksi disimpan, akan sync otomatis saat online', 'warning');

  const total = txData.items.reduce((s, i) => s + i.price * i.qty, 0);
  return {
    success:  true,
    offline:  true,
    local_id: localId,
    data: {
      invoice: `OFFLINE-${Date.now()}`,
      total,
      change: Math.max((txData.amount_paid || 0) - total, 0),
    }
  };
}

// ── CACHE PRODUK ─────────────────────────────────────────────

async function refreshProductCache() {
  if (!isOnline()) return;
  try {
    const res = await fetch('/api/kasir/produk?page=1&per_page=1000');
    if (!res.ok || !res.headers.get('content-type')?.includes('application/json')) return;
    const data = await res.json();
    if (data.data?.length) {
      await window.PosDB.cacheProducts(data.data);
      console.log(`[POS Cache] ${await window.PosDB.getCacheSize()} produk di-cache`);
    }
  } catch (e) {
    console.warn('[POS Cache] Gagal:', e);
  }
}

// ── INIT ────────────────────────────────────────────────────

function initSync() {
  // Saat koneksi kembali → langsung auto-sync tanpa perlu klik
  window.addEventListener('online', async () => {
    updateConnectionUI(true);
    showToast('🟢 Koneksi kembali, mensinkronkan data...', 'success');
    await syncPendingTransactions();
    startSyncTimer();
    refreshProductCache();
    // Reload grid produk pakai data server (bukan cache)
    if (typeof loadProduk === 'function') loadProduk();
  });

  window.addEventListener('offline', () => {
    updateConnectionUI(false);
    stopSyncTimer();
    showToast('🔴 Koneksi terputus. Mode offline aktif.', 'warning');
  });

  // Init status awal
  updateConnectionUI(isOnline());
  updatePendingBadge();

  if (isOnline()) {
    syncPendingTransactions(); // auto-sync saat halaman dibuka
    startSyncTimer();
    refreshProductCache();
  }
}

function startSyncTimer() {
  stopSyncTimer();
  syncTimer = setInterval(async () => {
    const count = await window.PosDB.countPending();
    if (count > 0) syncPendingTransactions();
  }, SYNC_INTERVAL);
}

function stopSyncTimer() {
  if (syncTimer) { clearInterval(syncTimer); syncTimer = null; }
}

window.PosSync = {
  submitTransaction,
  syncPendingTransactions,
  refreshProductCache,
  isOnline,
  showToast,
  initSync,
};