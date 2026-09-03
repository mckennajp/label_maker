/** Browser transports for the Ponek M100 — Web Bluetooth and Web Serial. */

const SVC = "0000ff00-0000-1000-8000-00805f9b34fb";
const TX = "0000ff02-0000-1000-8000-00805f9b34fb";
const RX = "0000ff03-0000-1000-8000-00805f9b34fb";
const ADV_AF30 = "0000af30-0000-1000-8000-00805f9b34fb";

const HEAD_PX = 384;
const SHIFT_X = Math.round(3.5 / 25.4 * 203);
const SPEED = 3;
const DENSITY = 10;
const MEDIA_GAP = 0x0a;
const HOLD_MS = 12000;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function concatBytes(parts) {
  const n = parts.reduce((s, p) => s + p.length, 0);
  const out = new Uint8Array(n);
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
}

export function encodeFromCanvas(canvas) {
  const srcW = canvas.width;
  const srcH = canvas.height;
  const ctx = canvas.getContext("2d");
  const { data } = ctx.getImageData(0, 0, srcW, srcH);
  const widthBytes = Math.ceil(HEAD_PX / 8);
  const raster = new Uint8Array(widthBytes * srcH);
  for (let y = 0; y < srcH; y++) {
    for (let x = 0; x < srcW; x++) {
      const dx = x + SHIFT_X;
      if (dx < 0 || dx >= HEAD_PX) continue;
      const i = (y * srcW + x) * 4;
      const lum = (data[i] + data[i + 1] + data[i + 2]) / 3;
      if (lum < 128) raster[y * widthBytes + (dx >> 3)] |= 0x80 >> (dx & 7);
    }
  }
  const job = [
    [0x1b, 0x40],
    [0x1b, 0x4e, 0x0d, SPEED],
    [0x1b, 0x4e, 0x04, DENSITY],
    [0x1f, 0x11, MEDIA_GAP],
    [0x1d, 0x76, 0x30, 0x00, widthBytes & 0xff, widthBytes >> 8, srcH & 0xff, srcH >> 8],
    raster,
    [0x1f, 0xf0, 0x05, 0x00, 0x1f, 0xf0, 0x03, 0x00],
  ].map((p) => (p instanceof Uint8Array ? p : new Uint8Array(p)));
  return concatBytes(job);
}

function parseStatus(buf) {
  const st = {};
  let i = 0;
  const lens = { 0x03: 1, 0x04: 1, 0x05: 1, 0x06: 1, 0x07: 3, 0x08: 15, 0x0c: 1, 0x0f: 1, 0x17: 1 };
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  while (i < u8.length) {
    if (u8[i] !== 0x1a) { i++; continue; }
    if (i + 1 >= u8.length) break;
    const tag = u8[i + 1];
    const n = Math.min(lens[tag] ?? 1, u8.length - i - 2);
    const p = u8.subarray(i + 2, i + 2 + n);
    if (tag === 0x08) st.serial = String.fromCharCode(...p).replace(/[^\x20-\x7e]/g, "");
    if (tag === 0x07 && p.length >= 3) st.firmware = `${p[0]}.${p[1]}.${p[2]}`;
    if (tag === 0x04) st.battery = p[0] === 0 ? 100 : p[0];
    if (tag === 0x06) st.paper = p[0] === 0x89 ? "ok" : "empty";
    if (tag === 0x05) st.cover = p[0] === 0x98 ? "closed" : "open";
    if (tag === 0x0f && p[0] === 0x0c) st.printComplete = true;
    i += 2 + n;
  }
  return st;
}

class BaseLink {
  constructor() {
    this.onStatus = () => {};
    this._status = {};
    this._waiters = [];
  }
  _feed(bytes) {
    const extra = parseStatus(bytes);
    Object.assign(this._status, extra);
    this.onStatus({ ...this._status });
    if (extra.printComplete) {
      for (const w of this._waiters.splice(0)) w();
    }
  }
  waitComplete(ms = HOLD_MS) {
    if (this._status.printComplete) return Promise.resolve(true);
    return new Promise((resolve) => {
      const t = setTimeout(() => {
        this._waiters = this._waiters.filter((w) => w !== done);
        resolve(false);
      }, ms);
      const done = () => { clearTimeout(t); resolve(true); };
      this._waiters.push(done);
    });
  }
}

function bleHint(err) {
  const msg = err?.message || String(err);
  return (
    msg +
    " Windows often keeps a Classic/SPP bond (COM10) which blocks Web Bluetooth. " +
    "Use Connect serial and pick the M100 COM port, or remove M100 in Windows Bluetooth settings and pair it from this dialog."
  );
}

async function connectGatt(device) {
  let last = new Error("GATT connect failed");
  for (let i = 0; i < 2; i++) {
    try {
      await sleep(i === 0 ? 400 : 600);
      const server = await device.gatt.connect();
      await sleep(250);
      if (server?.connected) return server;
    } catch (e) {
      last = e;
    }
  }
  throw last;
}

async function findTxRx(server) {
  if (!server.connected) {
    throw new Error("GATT dropped right after connect");
  }
  const svc = await server.getPrimaryService(SVC);
  const tx = await svc.getCharacteristic(TX);
  let rx = null;
  try { rx = await svc.getCharacteristic(RX); } catch { /* notify optional */ }
  return { tx, rx };
}

export class BluetoothLink extends BaseLink {
  constructor() {
    super();
    this.chunk = 128;
    this.paceMs = 20;
    this.device = null;
    this.tx = null;
  }
  async connect() {
    if (!navigator.bluetooth) throw new Error("Web Bluetooth needs Chrome or Edge on https/localhost");
    this.device = await navigator.bluetooth.requestDevice({
      filters: [{ namePrefix: "M100" }, { name: "M100" }],
      optionalServices: [SVC, ADV_AF30, "00001800-0000-1000-8000-00805f9b34fb"],
    });
    this._connecting = true;
    this.device.addEventListener("gattserverdisconnected", () => {
      this.tx = null;
      this._status = { ...this._status, connected: false, error: "Bluetooth dropped" };
      if (this._connecting) return;
      this.onStatus({ ...this._status });
    });
    let server;
    try {
      server = await connectGatt(this.device);
    } catch (e) {
      throw new Error(bleHint(e));
    }
    try {
      const chars = await findTxRx(server);
      this.tx = chars.tx;
      if (chars.rx) {
        try {
          await chars.rx.startNotifications();
          chars.rx.addEventListener("characteristicvaluechanged", (ev) => {
            this._feed(new Uint8Array(ev.target.value.buffer));
          });
        } catch (e) {
          console.warn("notify failed", e);
        }
      }
    } catch (e) {
      throw new Error(bleHint(e));
    }
    if (!this.device.gatt.connected || !this.tx) {
      throw new Error("GATT dropped before a write characteristic was ready");
    }
    try {
      await this.write(new Uint8Array([0x1f, 0x11, 0x09]));
    } catch (e) {
      throw new Error(bleHint(e));
    }
    this._connecting = false;
    this._status = { connected: true, name: this.device.name || "M100", transport: "bluetooth" };
    this.onStatus({ ...this._status });
    try { await this._query(); } catch (e) { console.warn("status query failed", e); }
    if (!this.device.gatt.connected || !this.tx) {
      throw new Error("GATT dropped immediately after connect");
    }
    return this._status;
  }
  async _query() {
    const cmds = [0x38, 0x11, 0x12, 0x13, 0x09, 0x07, 0x08, 0x19];
    for (const c of cmds) {
      await this.write(new Uint8Array([0x1f, 0x11, c]));
      await sleep(80);
    }
  }
  async write(bytes) {
    if (!this.tx || !this.device?.gatt?.connected) {
      throw new Error("Bluetooth GATT is not connected — use Connect serial and pick COM10");
    }
    const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    for (let i = 0; i < u8.length; i += this.chunk) {
      const slice = u8.subarray(i, i + this.chunk);
      try {
        await this.tx.writeValueWithoutResponse(slice);
      } catch {
        await this.tx.writeValue(slice);
      }
      if (i + this.chunk < u8.length) await sleep(this.paceMs);
    }
  }
  async printCanvas(canvas, copies = 1) {
    const job = encodeFromCanvas(canvas);
    for (let n = 0; n < copies; n++) {
      this._status.printComplete = false;
      await this.write(job);
      const ok = await this.waitComplete();
      if (!ok) await sleep(1500);
    }
    return this._status;
  }
  disconnect() {
    try { this.device?.gatt?.disconnect(); } catch {}
    this.tx = null;
    this.device = null;
  }
}

export class SerialLink extends BaseLink {
  constructor() {
    super();
    this.chunk = 256;
    this.paceMs = 20;
    this.port = null;
    this.writer = null;
    this._closed = false;
  }
  async connect() {
    if (!navigator.serial) throw new Error("Web Serial needs Chrome or Edge on https/localhost");
    this.port = await navigator.serial.requestPort();
    await this.port.open({ baudRate: 115200 });
    try {
      await this.port.setSignals({ dataTerminalReady: true, requestToSend: true });
    } catch { /* some Bluetooth COM ports reject signal changes */ }
    this.writer = this.port.writable.getWriter();
    this._closed = false;
    this._readLoop();
    this._status = { connected: true, name: "Serial", transport: "serial" };
    this.onStatus({ ...this._status });
    try {
      await this._query();
    } catch (e) {
      throw new Error("Opened the port but writes failed: " + (e.message || e));
    }
    return this._status;
  }
  async _readLoop() {
    const reader = this.port.readable.getReader();
    try {
      while (!this._closed) {
        const { value, done } = await reader.read();
        if (done) break;
        if (value) this._feed(value);
      }
    } catch {
      /* port closed */
    } finally {
      try { reader.releaseLock(); } catch {}
    }
  }
  async _query() {
    const cmds = [0x38, 0x11, 0x12, 0x13, 0x09, 0x07, 0x08, 0x19];
    for (const c of cmds) {
      await this.write(new Uint8Array([0x1f, 0x11, c]));
      await sleep(80);
    }
  }
  async write(bytes) {
    if (!this.writer || !this.port) {
      throw new Error("Serial port is not connected — click Connect serial and pick COM10");
    }
    const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    for (let i = 0; i < u8.length; i += this.chunk) {
      await this.writer.write(u8.subarray(i, i + this.chunk));
      if (i + this.chunk < u8.length) await sleep(this.paceMs);
    }
  }
  async printCanvas(canvas, copies = 1) {
    const job = encodeFromCanvas(canvas);
    for (let n = 0; n < copies; n++) {
      this._status.printComplete = false;
      await this.write(job);
      const ok = await this.waitComplete();
      if (!ok) await sleep(1500);
    }
    return this._status;
  }
  async disconnect() {
    this._closed = true;
    try { this.writer?.releaseLock(); } catch {}
    try { await this.port?.close(); } catch {}
    this.writer = null;
    this.port = null;
  }
}

export function bluetoothAvailable() {
  return Boolean(navigator.bluetooth);
}
export function serialAvailable() {
  return Boolean(navigator.serial);
}
