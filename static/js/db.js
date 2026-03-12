/**
 * POS SUMBA — IndexedDB Manager
 * Menyimpan transaksi offline ke browser database
 */

const DB_NAME    = 'pos_sumba_db';
const DB_VERSION = 1;
const STORE_TX   = 'pending_transactions';
const STORE_PROD = 'products_cache';

let _db = null;

function openDB() {
  if (_db) return Promise.resolve(_db);

  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = e => {
      const db = e.target.result;

      // Store transaksi pending
      if (!db.objectStoreNames.contains(STORE_TX)) {
        const txStore = db.createObjectStore(STORE_TX, { keyPath: 'local_id', autoIncrement: true });
        txStore.createIndex('status', 'status', { unique: false });
        txStore.createIndex('created_at', 'created_at', { unique: false });
      }

      // Store cache produk (untuk dipakai saat offline)
      if (!db.objectStoreNames.contains(STORE_PROD)) {
        const pStore = db.createObjectStore(STORE_PROD, { keyPath: 'id' });
        pStore.createIndex('category_id', 'category_id', { unique: false });
        pStore.createIndex('name', 'name', { unique: false });
      }
    };

    req.onsuccess = e => {
      _db = e.target.result;
      resolve(_db);
    };

    req.onerror = () => reject(req.error);
  });
}

// ── TRANSAKSI PENDING ───────────────────────────────────────

async function savePendingTransaction(txData) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx   = db.transaction(STORE_TX, 'readwrite');
    const store = tx.objectStore(STORE_TX);
    const record = {
      ...txData,
      status:     'pending',
      created_at: new Date().toISOString(),
      retry_count: 0,
    };
    const req = store.add(record);
    req.onsuccess = () => resolve(req.result); // returns local_id
    req.onerror   = () => reject(req.error);
  });
}

async function getPendingTransactions() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_TX, 'readonly');
    const store = tx.objectStore(STORE_TX);
    const index = store.index('status');
    const req   = index.getAll('pending');
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

async function getAllTransactions() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_TX, 'readonly');
    const store = tx.objectStore(STORE_TX);
    const req   = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

async function markTransactionSynced(localId, serverData) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_TX, 'readwrite');
    const store = tx.objectStore(STORE_TX);
    const getReq = store.get(localId);
    getReq.onsuccess = () => {
      const record = getReq.result;
      if (record) {
        record.status      = 'synced';
        record.synced_at   = new Date().toISOString();
        record.server_data = serverData;
        store.put(record);
      }
      resolve();
    };
    getReq.onerror = () => reject(getReq.error);
  });
}

async function markTransactionFailed(localId, error) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_TX, 'readwrite');
    const store = tx.objectStore(STORE_TX);
    const getReq = store.get(localId);
    getReq.onsuccess = () => {
      const record = getReq.result;
      if (record) {
        record.retry_count = (record.retry_count || 0) + 1;
        record.last_error  = error;
        if (record.retry_count >= 3) record.status = 'failed';
        store.put(record);
      }
      resolve();
    };
    getReq.onerror = () => reject(getReq.error);
  });
}

async function countPending() {
  const pending = await getPendingTransactions();
  return pending.length;
}

async function clearSynced() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_TX, 'readwrite');
    const store = tx.objectStore(STORE_TX);
    const index = store.index('status');
    const req   = index.openCursor(IDBKeyRange.only('synced'));
    req.onsuccess = e => {
      const cursor = e.target.result;
      if (cursor) { cursor.delete(); cursor.continue(); }
      else resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

// ── CACHE PRODUK ────────────────────────────────────────────

async function cacheProducts(products) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_PROD, 'readwrite');
    const store = tx.objectStore(STORE_PROD);
    store.clear();
    products.forEach(p => store.put(p));
    tx.oncomplete = resolve;
    tx.onerror    = () => reject(tx.error);
  });
}

async function getCachedProducts(search = '', categoryId = '') {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_PROD, 'readonly');
    const store = tx.objectStore(STORE_PROD);
    const req   = store.getAll();
    req.onsuccess = () => {
      let data = req.result;
      if (search)     data = data.filter(p => p.name.toLowerCase().includes(search.toLowerCase()));
      if (categoryId) data = data.filter(p => String(p.category_id) === String(categoryId));
      resolve(data.slice(0, 60));
    };
    req.onerror = () => reject(req.error);
  });
}

async function getCacheSize() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_PROD, 'readonly');
    const store = tx.objectStore(STORE_PROD);
    const req   = store.count();
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

// Export global
window.PosDB = {
  savePendingTransaction,
  getPendingTransactions,
  getAllTransactions,
  markTransactionSynced,
  markTransactionFailed,
  countPending,
  clearSynced,
  cacheProducts,
  getCachedProducts,
  getCacheSize,
};