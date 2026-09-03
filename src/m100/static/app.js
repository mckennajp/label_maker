import { BluetoothLink, SerialLink, bluetoothAvailable, serialAvailable } from "./printer.js";
import { BORDERS, drawBorder } from "./borders.js";

const W = 320;
const H = 240;
const MIN_SIZE = 8;

function handleSize() {
  return window.matchMedia("(pointer: coarse)").matches ? 16 : 7;
}

const canvas = document.getElementById("label");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
const propsEl = document.getElementById("props");
const toastEl = document.getElementById("toast");
const printBtn = document.getElementById("print");
const deleteBtn = document.getElementById("delete");
const frontBtn = document.getElementById("bring-front");
const backBtn = document.getElementById("send-back");
const btBtn = document.getElementById("connect-bt");
const serialBtn = document.getElementById("connect-serial");
const discBtn = document.getElementById("disconnect");

let link = null;
let lastError = "";

let objects = [];
let selected = -1;
let drag = null;

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

function toast(msg, ms = 4000) {
  toastEl.hidden = false;
  toastEl.textContent = msg;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => { toastEl.hidden = true; }, ms);
}

function lastImageIndex() {
  let i = -1;
  objects.forEach((o, n) => { if (o.type === "image" || o.type === "border") i = n; });
  return i;
}

function applyBorder(kind) {
  objects = objects.filter((o) => o.type !== "border");
  objects.unshift({
    id: uid(),
    type: "border",
    kind,
    x: 4,
    y: 4,
    w: W - 8,
    h: H - 8,
  });
  selected = 0;
  draw();
  renderProps();
}

function openBorderGallery() {
  const modal = document.getElementById("border-modal");
  for (const group of ["Decorative", "Holiday"]) {
    const host = document.getElementById("borders-" + group);
    host.replaceChildren();
    for (const spec of BORDERS.filter((b) => b.group === group)) {
      const btn = document.createElement("button");
      btn.type = "button";
      const preview = document.createElement("canvas");
      preview.width = 160;
      preview.height = 120;
      const pctx = preview.getContext("2d");
      pctx.fillStyle = "#fff";
      pctx.fillRect(0, 0, 160, 120);
      pctx.save();
      pctx.scale(160 / W, 120 / H);
      drawBorder(pctx, spec.id, 6, 6, W - 12, H - 12);
      pctx.restore();
      const label = document.createElement("span");
      label.textContent = spec.name;
      btn.append(preview, label);
      btn.onclick = () => {
        applyBorder(spec.id);
        modal.hidden = true;
      };
      host.append(btn);
    }
  }
  modal.hidden = false;
}

function addText() {
  objects.push({
    id: uid(),
    type: "text",
    x: 24,
    y: 90,
    text: "Text",
    fontSize: 36,
    font: "Arial",
  });
  selected = objects.length - 1;
  draw();
  renderProps();
}

function addImageFile(file) {
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.onload = () => {
    const scale = Math.min(1, 200 / img.width, 160 / img.height);
    const obj = {
      id: uid(),
      type: "image",
      x: 20,
      y: 20,
      w: Math.max(MIN_SIZE, Math.round(img.width * scale)),
      h: Math.max(MIN_SIZE, Math.round(img.height * scale)),
      img,
    };
    // Keep photos under text so labels can sit on top of a picture.
    const insertAt = lastImageIndex() + 1;
    objects.splice(insertAt, 0, obj);
    selected = insertAt;
    draw();
    renderProps();
  };
  img.src = url;
}

function fontSpec(o) {
  return `${o.fontSize}px ${o.font}`;
}

function textSize(o) {
  ctx.save();
  ctx.font = fontSpec(o);
  const m = ctx.measureText(o.text || " ");
  ctx.restore();
  return { w: Math.max(MIN_SIZE, m.width), h: o.fontSize };
}

function bounds(o) {
  if (o.type === "text") {
    const s = textSize(o);
    return { x: o.x, y: o.y, w: s.w, h: s.h };
  }
  return { x: o.x, y: o.y, w: o.w, h: o.h };
}

function handles(b) {
  return {
    nw: { x: b.x, y: b.y },
    ne: { x: b.x + b.w, y: b.y },
    sw: { x: b.x, y: b.y + b.h },
    se: { x: b.x + b.w, y: b.y + b.h },
  };
}

function hitHandle(mx, my, b) {
  const pad = handleSize();
  const hs = handles(b);
  for (const [name, pt] of Object.entries(hs)) {
    if (Math.abs(mx - pt.x) <= pad && Math.abs(my - pt.y) <= pad) return name;
  }
  return null;
}

function hit(mx, my) {
  const pad = handleSize();
  for (let i = objects.length - 1; i >= 0; i--) {
    const b = bounds(objects[i]);
    if (mx >= b.x - pad && mx <= b.x + b.w + pad && my >= b.y - pad && my <= b.y + b.h + pad) {
      return i;
    }
  }
  return -1;
}

function cursorFor(ev) {
  const p = canvasPoint(ev);
  if (selected >= 0) {
    const h = hitHandle(p.x, p.y, bounds(objects[selected]));
    if (h === "nw" || h === "se") return "nwse-resize";
    if (h === "ne" || h === "sw") return "nesw-resize";
  }
  if (hit(p.x, p.y) >= 0) return "move";
  return "default";
}

function draw(exporting = false) {
  ctx.save();
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, W, H);
  for (const o of objects) {
    if (o.type === "text") {
      ctx.fillStyle = "#000";
      ctx.font = fontSpec(o);
      ctx.textBaseline = "top";
      ctx.fillText(o.text, o.x, o.y);
    } else if (o.type === "image" && o.img) {
      ctx.drawImage(o.img, o.x, o.y, o.w, o.h);
    } else if (o.type === "border") {
      drawBorder(ctx, o.kind, o.x, o.y, o.w, o.h);
    }
  }
  if (!exporting && selected >= 0) {
    const b = bounds(objects[selected]);
    ctx.strokeStyle = "#2f6feb";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.strokeRect(b.x, b.y, b.w, b.h);
    ctx.setLineDash([]);
    ctx.fillStyle = "#fff";
    ctx.strokeStyle = "#2f6feb";
    const hs = Math.max(6, Math.round(handleSize() * 0.45));
    for (const pt of Object.values(handles(b))) {
      ctx.fillRect(pt.x - hs / 2, pt.y - hs / 2, hs, hs);
      ctx.strokeRect(pt.x - hs / 2, pt.y - hs / 2, hs, hs);
    }
  }
  ctx.restore();
}

function renderProps() {
  const on = selected >= 0;
  deleteBtn.disabled = !on;
  frontBtn.disabled = !on;
  backBtn.disabled = !on;
  const o = objects[selected];
  if (!o) {
    propsEl.className = "props muted";
    propsEl.textContent = "Select an object";
    return;
  }
  propsEl.className = "props";
  if (o.type === "text") {
    propsEl.innerHTML = `
      <label>Text</label>
      <input id="p-text" value="${o.text.replaceAll('"', "&quot;")}" />
      <label>Size</label>
      <input id="p-size" type="number" min="8" max="200" value="${Math.round(o.fontSize)}" />
      <label>Font</label>
      <select id="p-font">
        <option>Arial</option>
        <option>Georgia</option>
        <option>Courier New</option>
        <option>Segoe UI</option>
        <option>Times New Roman</option>
      </select>`;
    propsEl.querySelector("#p-font").value = o.font;
    propsEl.querySelector("#p-text").oninput = (e) => { o.text = e.target.value; draw(); };
    propsEl.querySelector("#p-size").oninput = (e) => { o.fontSize = +e.target.value || 12; draw(); };
    propsEl.querySelector("#p-font").onchange = (e) => { o.font = e.target.value; draw(); };
  } else {
    propsEl.innerHTML = `
      <label>Width</label>
      <input id="p-w" type="number" min="8" value="${Math.round(o.w)}" />
      <label>Height</label>
      <input id="p-h" type="number" min="8" value="${Math.round(o.h)}" />`;
    propsEl.querySelector("#p-w").oninput = (e) => { o.w = +e.target.value || MIN_SIZE; draw(); };
    propsEl.querySelector("#p-h").oninput = (e) => { o.h = +e.target.value || MIN_SIZE; draw(); };
  }
}

function canvasPoint(ev) {
  const r = canvas.getBoundingClientRect();
  return {
    x: (ev.clientX - r.left) * (W / r.width),
    y: (ev.clientY - r.top) * (H / r.height),
  };
}

function applyScale(o, start, scale, corner) {
  const s = Math.max(0.05, scale);
  const w = Math.max(MIN_SIZE, start.w * s);
  const h = Math.max(MIN_SIZE, start.h * s);
  const anchor = {
    nw: { x: start.x + start.w, y: start.y + start.h },
    ne: { x: start.x, y: start.y + start.h },
    sw: { x: start.x + start.w, y: start.y },
    se: { x: start.x, y: start.y },
  }[corner];
  if (o.type === "text") {
    o.fontSize = Math.max(8, start.fontSize * (h / start.h));
    const now = textSize(o);
    if (corner.includes("n")) o.y = anchor.y - now.h;
    else o.y = start.y;
    if (corner.includes("w")) o.x = anchor.x - now.w;
    else o.x = start.x;
  } else {
    o.w = w;
    o.h = h;
    o.x = corner.includes("w") ? anchor.x - w : start.x;
    o.y = corner.includes("n") ? anchor.y - h : start.y;
  }
}

function onPointerMove(ev) {
  if (drag) ev.preventDefault();
  canvas.style.cursor = drag ? canvas.style.cursor : cursorFor(ev);
  if (!drag || selected < 0) return;
  const p = canvasPoint(ev);
  const o = objects[selected];
  if (drag.mode === "move") {
    o.x = Math.round(p.x - drag.dx);
    o.y = Math.round(p.y - drag.dy);
  } else {
    const ax = drag.anchor.x;
    const ay = drag.anchor.y;
    const startDist = Math.hypot(drag.startX - ax, drag.startY - ay) || 1;
    const dist = Math.hypot(p.x - ax, p.y - ay);
    applyScale(o, drag.start, dist / startDist, drag.mode);
  }
  draw();
}

function endDrag() {
  if (!drag) return;
  drag = null;
  renderProps();
}

canvas.addEventListener("pointerdown", (ev) => {
  ev.preventDefault();
  const p = canvasPoint(ev);
  let handle = null;
  if (selected >= 0) handle = hitHandle(p.x, p.y, bounds(objects[selected]));
  if (!handle) {
    selected = hit(p.x, p.y);
    if (selected >= 0) handle = hitHandle(p.x, p.y, bounds(objects[selected]));
  }
  if (selected >= 0) {
    const o = objects[selected];
    const b = bounds(o);
    const hs = handles(b);
    if (handle) {
      const opposite = { nw: "se", ne: "sw", sw: "ne", se: "nw" }[handle];
      drag = {
        mode: handle,
        startX: p.x,
        startY: p.y,
        start: { x: b.x, y: b.y, w: b.w, h: b.h, fontSize: o.fontSize },
        anchor: hs[opposite],
      };
      canvas.style.cursor = (handle === "nw" || handle === "se") ? "nwse-resize" : "nesw-resize";
    } else {
      drag = { mode: "move", dx: p.x - o.x, dy: p.y - o.y };
      canvas.style.cursor = "move";
    }
    try { canvas.setPointerCapture(ev.pointerId); } catch { /* older WebViews */ }
  } else {
    drag = null;
  }
  draw();
  renderProps();
}, { passive: false });

canvas.addEventListener("pointermove", onPointerMove, { passive: false });
window.addEventListener("pointermove", (ev) => {
  if (drag) onPointerMove(ev);
}, { passive: false });
canvas.addEventListener("pointerup", endDrag);
canvas.addEventListener("pointercancel", (ev) => {
  ev.preventDefault();
  endDrag();
});
window.addEventListener("pointerup", endDrag);

canvas.addEventListener("dblclick", () => {
  if (selected < 0 || objects[selected].type !== "text") return;
  const next = prompt("Text", objects[selected].text);
  if (next != null) {
    objects[selected].text = next;
    draw();
    renderProps();
  }
});

function moveLayer(toFront) {
  if (selected < 0) return;
  const [obj] = objects.splice(selected, 1);
  if (toFront) {
    objects.push(obj);
    selected = objects.length - 1;
  } else {
    objects.unshift(obj);
    selected = 0;
  }
  draw();
  renderProps();
}

document.querySelector("[data-add=text]").onclick = addText;
document.getElementById("add-image").onclick = () => document.getElementById("file").click();
document.getElementById("add-border").onclick = openBorderGallery;
document.getElementById("border-close").onclick = () => {
  document.getElementById("border-modal").hidden = true;
};
document.getElementById("border-modal").addEventListener("click", (e) => {
  if (e.target.id === "border-modal") e.currentTarget.hidden = true;
});
document.getElementById("file").onchange = (e) => {
  const f = e.target.files[0];
  if (f) addImageFile(f);
  e.target.value = "";
};
deleteBtn.onclick = () => {
  if (selected < 0) return;
  objects.splice(selected, 1);
  selected = -1;
  draw();
  renderProps();
};
frontBtn.onclick = () => moveLayer(true);
backBtn.onclick = () => moveLayer(false);

document.addEventListener("keydown", (e) => {
  if (e.target !== document.body && e.target !== canvas) return;
  if ((e.key === "Delete" || e.key === "Backspace") && selected >= 0) deleteBtn.click();
  if ((e.key === "]" || e.key === ".") && selected >= 0) moveLayer(true);
  if ((e.key === "[" || e.key === ",") && selected >= 0) moveLayer(false);
});

function showLinkStatus(s) {
  if (s && s.connected !== false && (s.serial || s.name || s.transport)) {
    lastError = "";
    statusEl.className = "status ok";
    const bits = [
      s.transport === "bluetooth" ? "Bluetooth" : s.transport === "serial" ? "Serial" : null,
      s.serial || s.name,
      s.battery != null ? `${s.battery}%` : null,
      s.paper ? `paper ${s.paper}` : null,
    ].filter(Boolean);
    statusEl.textContent = bits.join(" · ");
  } else {
    statusEl.className = "status bad";
    statusEl.textContent = (s && s.error) || lastError || "not connected";
  }
  const on = Boolean(link);
  btBtn.hidden = on;
  serialBtn.hidden = on || !serialAvailable();
  discBtn.hidden = !on;
}

async function refreshStatus() {
  if (link) {
    showLinkStatus(link._status);
    return;
  }
  if (lastError) return;
  try {
    const r = await fetch("/api/status");
    const s = await r.json();
    if (s.connected) {
      statusEl.className = "status ok";
      statusEl.textContent = `Server · ${s.serial || "M100"} · ${s.battery_percent ?? "?"}% · paper ${s.paper || "?"}`;
    } else {
      statusEl.className = "status unknown";
      statusEl.textContent = "not connected — Connect Bluetooth, or Connect serial for COM10";
    }
  } catch {
    statusEl.className = "status unknown";
    statusEl.textContent = "not connected — Connect Bluetooth, or Connect serial for COM10";
  }
}

async function connectWith(make, prompt) {
  lastError = "";
  try {
    if (link) await link.disconnect?.();
    link = make();
    link.onStatus = showLinkStatus;
    if (prompt) toast(prompt);
    await link.connect();
    lastError = "";
    showLinkStatus(link._status);
    toast("Connected");
    return true;
  } catch (e) {
    const msg = e.message || String(e);
    lastError = msg;
    console.error("connect failed", e);
    link = null;
    showLinkStatus({ error: msg });
    toast(msg, 12000);
    return false;
  }
}

const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
const isAndroid = /Android/i.test(navigator.userAgent);
const isWinDesktop = /Windows/i.test(navigator.userAgent) && !isAndroid;

btBtn.hidden = !bluetoothAvailable();
serialBtn.hidden = isAndroid || isIOS || !serialAvailable();
if (isIOS && !bluetoothAvailable()) {
  statusEl.textContent = "iPhone Safari cannot use Bluetooth. Use Android Chrome, or Bluefy.";
} else if (!bluetoothAvailable() && !serialAvailable()) {
  statusEl.textContent = "Need Chrome/Edge. Phones require HTTPS (python -m m100 serve --lan).";
} else if (isAndroid && !window.isSecureContext) {
  statusEl.textContent = "Phone Web Bluetooth needs HTTPS. On the PC run: python -m m100 serve --lan";
}
btBtn.onclick = async () => {
  // Windows Classic SPP bond blocks GATT; phones speak BLE like Print Master.
  if (isWinDesktop && serialAvailable()) {
    toast("On this Windows PC, pick COM10. On a phone, open the HTTPS LAN URL instead.", 10000);
    await connectWith(() => new SerialLink(), "Select COM10 (Bluetooth serial)…");
    return;
  }
  const ok = await connectWith(() => new BluetoothLink(), "Pick M100… allow Bluetooth if asked");
  if (ok || !serialAvailable() || isAndroid || isIOS) return;
  toast("LE failed. Select the Bluetooth COM port (COM10).", 10000);
  await connectWith(() => new SerialLink(), "Select COM10 (Bluetooth serial)…");
};
serialBtn.onclick = () => connectWith(() => new SerialLink(), "Select the M100 COM port (COM10)…");
discBtn.onclick = async () => {
  try { await link?.disconnect?.(); } catch {}
  link = null;
  showLinkStatus({});
};

printBtn.onclick = async () => {
  printBtn.disabled = true;
  const copies = Math.max(1, +document.getElementById("copies").value || 1);
  try {
    if (link) {
      draw(true);
      const st = await link.printCanvas(canvas, copies);
      draw();
      toast(st.printComplete ? "Printed" : "Sent — check the printer");
    } else {
      draw(true);
      const blob = await new Promise((res) => canvas.toBlob(res, "image/png"));
      draw();
      const r = await fetch("/api/print?copies=" + copies, {
        method: "POST",
        headers: { "Content-Type": "image/png" },
        body: blob,
      });
      const s = await r.json();
      if (s.ok && s.print_complete) toast("Printed via server");
      else toast(s.error || "Connect Bluetooth, or start serve with a COM port");
    }
  } catch (e) {
    toast(String(e.message || e));
  } finally {
    printBtn.disabled = false;
    refreshStatus();
  }
};

addText();
objects[0].text = "Hello";
draw();
renderProps();
refreshStatus();
setInterval(refreshStatus, 8000);
