/**
 * POS SUMBA — ESC/POS Thermal Printer (58mm)
 * Menggunakan Web Serial API (Chrome/Edge)
 * Lebar kertas: 58mm = 32 karakter per baris
 */

const ESC  = 0x1B;
const GS   = 0x1D;
const COLS = 32; // karakter per baris untuk 58mm

const CMD = {
  INIT:         [ESC, 0x40],               // init printer
  ALIGN_LEFT:   [ESC, 0x61, 0x00],
  ALIGN_CENTER: [ESC, 0x61, 0x01],
  ALIGN_RIGHT:  [ESC, 0x61, 0x02],
  BOLD_ON:      [ESC, 0x45, 0x01],
  BOLD_OFF:     [ESC, 0x45, 0x00],
  DOUBLE_HEIGHT:[ESC, 0x21, 0x10],         // teks 2x tinggi
  NORMAL_SIZE:  [ESC, 0x21, 0x00],
  CUT:          [GS,  0x56, 0x41, 0x00],   // partial cut
  FEED:         [ESC, 0x64, 0x03],         // feed 3 baris
  LF:           [0x0A],                    // line feed
};

// ── HELPER TEKS ──────────────────────────────────────────────

function textBytes(str) {
  // Encode ke ASCII — ganti karakter non-ASCII umum
  const clean = str
    .replace(/Rp\s*/g, 'Rp ')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // strip aksen
    .replace(/[^\x00-\x7F]/g, '?'); // ganti non-ASCII
  return Array.from(clean).map(c => c.charCodeAt(0));
}

function line(str = '') {
  return [...textBytes(str.slice(0, COLS)), ...CMD.LF];
}

function center(str) {
  const pad = Math.max(0, Math.floor((COLS - str.length) / 2));
  return line(' '.repeat(pad) + str);
}

function divider(char = '-') {
  return line(char.repeat(COLS));
}

// Baris dua kolom: kiri & kanan rata kanan
function row(left, right) {
  const maxLeft = COLS - right.length - 1;
  const l = left.slice(0, maxLeft).padEnd(maxLeft);
  return line(l + ' ' + right);
}

// ── BUILD STRUK BYTES ────────────────────────────────────────

function buildStrukBytes(data) {
  const bytes = [];
  const push  = (...cmds) => cmds.forEach(cmd => bytes.push(...cmd));

  const now = new Date().toLocaleString('id-ID', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

  push(CMD.INIT);

  // ── Header ──
  push(CMD.ALIGN_CENTER);
  push(CMD.BOLD_ON, CMD.DOUBLE_HEIGHT);
  push(line(data.store_name || 'POS SUMBA'));
  push(CMD.NORMAL_SIZE, CMD.BOLD_OFF);
  if (data.store_address) push(line(data.store_address));
  if (data.store_phone)   push(line('Tel: ' + data.store_phone));
  push(CMD.ALIGN_LEFT);
  push(divider());

  // ── Info transaksi ──
  push(...row('Invoice :', data.invoice || '-'));
  push(...row('Tanggal :', now));
  push(...row('Kasir   :', data.cashier || '-'));
  push(divider());

  // ── Items ──
  (data.items || []).forEach(item => {
    // Nama produk (wrap jika panjang)
    const nama = item.name.slice(0, COLS);
    push(line(nama));
    // Qty x harga = subtotal (rata kanan)
    const qtyStr  = `${item.qty} x ${fmtNum(item.price)}`;
    const subStr  = 'Rp ' + fmtNum(item.price * item.qty);
    push(...row('  ' + qtyStr, subStr));
  });

  push(divider());

  // ── Total ──
  push(CMD.BOLD_ON);
  push(...row('TOTAL', 'Rp ' + fmtNum(data.total)));
  push(CMD.BOLD_OFF);
  push(...row('Bayar', 'Rp ' + fmtNum(data.amount_paid || data.total)));
  push(CMD.BOLD_ON);
  push(...row('Kembalian', 'Rp ' + fmtNum(data.change || 0)));
  push(CMD.BOLD_OFF);
  push(divider());

  // ── Footer ──
  push(CMD.ALIGN_CENTER);
  push(line(data.footer || 'Terima kasih!'));
  if (data.offline) {
    push(line('** TRANSAKSI OFFLINE **'));
  }
  push(CMD.ALIGN_LEFT);

  // Feed & cut
  push(CMD.FEED);
  push(CMD.CUT);

  return new Uint8Array(bytes);
}

function fmtNum(n) {
  return Number(n).toLocaleString('id-ID');
}

// ── WEB SERIAL API ────────────────────────────────────────────

let _port   = null;
let _writer = null;

async function connectPrinter() {
  if (!('serial' in navigator)) {
    throw new Error('Browser tidak mendukung Web Serial API. Gunakan Chrome/Edge.');
  }

  try {
    // Minta user pilih port serial (printer thermal biasanya 9600 atau 115200 baud)
    _port = await navigator.serial.requestPort();
    await _port.open({ baudRate: 9600 });
    _writer = _port.writable.getWriter();
    console.log('[Printer] Terhubung');
    return true;
  } catch (e) {
    console.error('[Printer] Gagal connect:', e);
    throw e;
  }
}

async function disconnectPrinter() {
  try {
    if (_writer) { await _writer.close(); _writer = null; }
    if (_port)   { await _port.close();   _port   = null; }
  } catch (e) { /* ignore */ }
}

async function printStruk(data) {
  // Auto-connect jika belum
  if (!_port || !_writer) {
    // Coba reconnect ke port yang sudah pernah dipilih
    if ('serial' in navigator) {
      const ports = await navigator.serial.getPorts();
      if (ports.length > 0) {
        _port = ports[0];
        try {
          await _port.open({ baudRate: 9600 });
          _writer = _port.writable.getWriter();
        } catch (e) {
          // Port mungkin sudah open, coba langsung
        }
      }
    }
    if (!_writer) {
      throw new Error('Printer belum terhubung');
    }
  }

  const bytes = buildStrukBytes(data);
  await _writer.write(bytes);
  console.log('[Printer] Struk dicetak:', bytes.length, 'bytes');
}

// ── STATUS ────────────────────────────────────────────────────

function isPrinterConnected() {
  return _port !== null && _writer !== null;
}

// ── EXPORT ────────────────────────────────────────────────────

window.PosPrinter = {
  connect:     connectPrinter,
  disconnect:  disconnectPrinter,
  print:       printStruk,
  isConnected: isPrinterConnected,
  buildBytes:  buildStrukBytes, // untuk debug
};