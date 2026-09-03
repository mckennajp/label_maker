/** 1-bit decorative and holiday frames for the 40×30 mm label. */

export const BORDERS = [
  { id: "thin", name: "Thin", group: "Decorative" },
  { id: "bold", name: "Bold", group: "Decorative" },
  { id: "double", name: "Double", group: "Decorative" },
  { id: "triple", name: "Triple", group: "Decorative" },
  { id: "dashed", name: "Dashed", group: "Decorative" },
  { id: "dotted", name: "Dotted", group: "Decorative" },
  { id: "scallop", name: "Scallop", group: "Decorative" },
  { id: "wave", name: "Wave", group: "Decorative" },
  { id: "stamp", name: "Postage", group: "Decorative" },
  { id: "brackets", name: "Corners", group: "Decorative" },
  { id: "deco", name: "Ornate", group: "Decorative" },
  { id: "diamonds", name: "Diamonds", group: "Decorative" },
  { id: "hearts", name: "Hearts", group: "Holiday" },
  { id: "stars", name: "Stars", group: "Holiday" },
  { id: "snow", name: "Snowflakes", group: "Holiday" },
  { id: "trees", name: "Christmas", group: "Holiday" },
  { id: "holly", name: "Holly", group: "Holiday" },
  { id: "cane", name: "Candy cane", group: "Holiday" },
  { id: "pumpkin", name: "Halloween", group: "Holiday" },
  { id: "ghost", name: "Ghosts", group: "Holiday" },
  { id: "balloon", name: "Birthday", group: "Holiday" },
  { id: "shamrock", name: "Shamrock", group: "Holiday" },
  { id: "flower", name: "Spring", group: "Holiday" },
  { id: "egg", name: "Easter", group: "Holiday" },
  { id: "spark", name: "Celebrate", group: "Holiday" },
  { id: "gift", name: "Gifts", group: "Holiday" },
];

function ink(ctx) {
  ctx.strokeStyle = "#000";
  ctx.fillStyle = "#000";
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
}

function frame(ctx, x, y, w, h, lw) {
  ink(ctx);
  ctx.lineWidth = lw;
  ctx.strokeRect(x + lw / 2, y + lw / 2, w - lw, h - lw);
}

function perimeter(x, y, w, h, step, fn) {
  for (let t = step / 2; t < w; t += step) fn(x + t, y, 0);
  for (let t = step / 2; t < h; t += step) fn(x + w, y + t, Math.PI / 2);
  for (let t = step / 2; t < w; t += step) fn(x + w - t, y + h, Math.PI);
  for (let t = step / 2; t < h; t += step) fn(x, y + h - t, -Math.PI / 2);
}

function heart(ctx, x, y, s) {
  ctx.beginPath();
  ctx.moveTo(x, y + s * 0.3);
  ctx.bezierCurveTo(x, y - s * 0.35, x - s, y - s * 0.1, x, y + s * 0.7);
  ctx.bezierCurveTo(x + s, y - s * 0.1, x, y - s * 0.35, x, y + s * 0.3);
  ctx.fill();
}

function star(ctx, x, y, r, n = 5) {
  ctx.beginPath();
  for (let i = 0; i < n * 2; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / n;
    const rr = i % 2 ? r * 0.4 : r;
    const fn = i ? "lineTo" : "moveTo";
    ctx[fn](x + Math.cos(a) * rr, y + Math.sin(a) * rr);
  }
  ctx.closePath();
  ctx.fill();
}

function snowflake(ctx, x, y, r) {
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3;
    ctx.moveTo(x, y);
    ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
    const mx = x + Math.cos(a) * r * 0.55;
    const my = y + Math.sin(a) * r * 0.55;
    ctx.moveTo(mx, my);
    ctx.lineTo(mx + Math.cos(a + 0.7) * r * 0.28, my + Math.sin(a + 0.7) * r * 0.28);
    ctx.moveTo(mx, my);
    ctx.lineTo(mx + Math.cos(a - 0.7) * r * 0.28, my + Math.sin(a - 0.7) * r * 0.28);
  }
  ctx.stroke();
}

function tree(ctx, x, y, s) {
  ctx.beginPath();
  ctx.moveTo(x, y - s);
  ctx.lineTo(x + s * 0.7, y + s * 0.15);
  ctx.lineTo(x - s * 0.7, y + s * 0.15);
  ctx.closePath();
  ctx.fill();
  ctx.fillRect(x - s * 0.12, y + s * 0.15, s * 0.24, s * 0.28);
}

function holly(ctx, x, y, s) {
  ctx.beginPath();
  ctx.ellipse(x - s * 0.25, y, s * 0.35, s * 0.18, -0.6, 0, Math.PI * 2);
  ctx.ellipse(x + s * 0.25, y, s * 0.35, s * 0.18, 0.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(x, y + s * 0.12, s * 0.12, 0, Math.PI * 2);
  ctx.arc(x + s * 0.18, y + s * 0.18, s * 0.1, 0, Math.PI * 2);
  ctx.fill();
}

function pumpkin(ctx, x, y, s) {
  ctx.beginPath();
  ctx.ellipse(x, y + s * 0.08, s * 0.55, s * 0.42, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillRect(x - s * 0.08, y - s * 0.45, s * 0.16, s * 0.22);
}

function ghost(ctx, x, y, s) {
  ctx.beginPath();
  ctx.arc(x, y - s * 0.1, s * 0.42, Math.PI, 0);
  ctx.lineTo(x + s * 0.42, y + s * 0.45);
  ctx.lineTo(x + s * 0.2, y + s * 0.28);
  ctx.lineTo(x, y + s * 0.45);
  ctx.lineTo(x - s * 0.2, y + s * 0.28);
  ctx.lineTo(x - s * 0.42, y + s * 0.45);
  ctx.closePath();
  ctx.fill();
}

function balloon(ctx, x, y, s) {
  ctx.beginPath();
  ctx.ellipse(x, y - s * 0.1, s * 0.32, s * 0.42, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(x, y + s * 0.28);
  ctx.quadraticCurveTo(x + s * 0.15, y + s * 0.55, x, y + s * 0.7);
  ctx.stroke();
}

function shamrock(ctx, x, y, s) {
  for (const a of [-0.7, 0, 0.7]) {
    ctx.beginPath();
    ctx.ellipse(x + Math.sin(a) * s * 0.22, y - Math.cos(a) * s * 0.18, s * 0.2, s * 0.14, a, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillRect(x - s * 0.05, y, s * 0.1, s * 0.4);
}

function flower(ctx, x, y, s) {
  for (let i = 0; i < 5; i++) {
    const a = (i * Math.PI * 2) / 5;
    ctx.beginPath();
    ctx.ellipse(x + Math.cos(a) * s * 0.28, y + Math.sin(a) * s * 0.28, s * 0.18, s * 0.12, a, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.beginPath();
  ctx.arc(x, y, s * 0.14, 0, Math.PI * 2);
  ctx.fill();
}

function egg(ctx, x, y, s) {
  ctx.beginPath();
  ctx.ellipse(x, y, s * 0.28, s * 0.38, 0, 0, Math.PI * 2);
  ctx.fill();
}

function spark(ctx, x, y, s) {
  star(ctx, x, y, s * 0.45, 4);
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i < 8; i++) {
    const a = (i * Math.PI) / 4;
    ctx.moveTo(x + Math.cos(a) * s * 0.2, y + Math.sin(a) * s * 0.2);
    ctx.lineTo(x + Math.cos(a) * s * 0.7, y + Math.sin(a) * s * 0.7);
  }
  ctx.stroke();
}

function gift(ctx, x, y, s) {
  ctx.fillRect(x - s * 0.4, y - s * 0.15, s * 0.8, s * 0.55);
  ctx.fillRect(x - s * 0.08, y - s * 0.15, s * 0.16, s * 0.55);
  ctx.fillRect(x - s * 0.4, y + s * 0.05, s * 0.8, s * 0.1);
  ctx.beginPath();
  ctx.arc(x - s * 0.12, y - s * 0.28, s * 0.14, Math.PI, 0);
  ctx.arc(x + s * 0.12, y - s * 0.28, s * 0.14, Math.PI, 0);
  ctx.stroke();
}

function cane(ctx, x, y, s) {
  ctx.lineWidth = Math.max(2, s * 0.28);
  ctx.beginPath();
  ctx.arc(x, y - s * 0.15, s * 0.28, Math.PI, 0);
  ctx.lineTo(x + s * 0.28, y + s * 0.55);
  ctx.stroke();
}

const ICONS = {
  hearts: (c, x, y, s) => heart(c, x, y, s),
  stars: (c, x, y, s) => star(c, x, y, s * 0.7),
  snow: snowflake,
  trees: tree,
  holly,
  cane,
  pumpkin,
  ghost,
  balloon,
  shamrock,
  flower,
  egg,
  spark,
  gift,
};

export function drawBorder(ctx, kind, x, y, w, h) {
  ctx.save();
  ink(ctx);
  const m = Math.max(2, Math.min(w, h) * 0.02);

  if (kind === "thin") frame(ctx, x, y, w, h, 1.5);
  else if (kind === "bold") frame(ctx, x, y, w, h, 4);
  else if (kind === "double") {
    frame(ctx, x, y, w, h, 1.5);
    frame(ctx, x + 5, y + 5, w - 10, h - 10, 1.5);
  } else if (kind === "triple") {
    frame(ctx, x, y, w, h, 1.2);
    frame(ctx, x + 4, y + 4, w - 8, h - 8, 1.2);
    frame(ctx, x + 8, y + 8, w - 16, h - 16, 1.2);
  } else if (kind === "dashed") {
    ctx.setLineDash([6, 4]);
    frame(ctx, x, y, w, h, 2);
    ctx.setLineDash([]);
  } else if (kind === "dotted") {
    ctx.setLineDash([1.5, 4]);
    frame(ctx, x, y, w, h, 2.5);
    ctx.setLineDash([]);
  } else if (kind === "scallop") {
    const r = 6;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let t = r; t < w - r; t += r * 2) {
      ctx.moveTo(x + t - r, y + r);
      ctx.arc(x + t, y + r, r, Math.PI, 0);
    }
    for (let t = r; t < h - r; t += r * 2) {
      ctx.moveTo(x + w - r, y + t - r);
      ctx.arc(x + w - r, y + t, r, -Math.PI / 2, Math.PI / 2);
    }
    for (let t = r; t < w - r; t += r * 2) {
      ctx.moveTo(x + w - (t - r), y + h - r);
      ctx.arc(x + w - t, y + h - r, r, 0, Math.PI);
    }
    for (let t = r; t < h - r; t += r * 2) {
      ctx.moveTo(x + r, y + h - (t - r));
      ctx.arc(x + r, y + h - t, r, Math.PI / 2, -Math.PI / 2);
    }
    ctx.stroke();
  } else if (kind === "wave") {
    const amp = 3, per = 14;
    ctx.lineWidth = 1.6;
    const wave = (x0, y0, len, horiz) => {
      ctx.beginPath();
      for (let t = 0; t <= len; t++) {
        const o = Math.sin((t / per) * Math.PI * 2) * amp;
        const px = horiz ? x0 + t : x0 + o;
        const py = horiz ? y0 + o : y0 + t;
        if (t === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    };
    wave(x + 4, y + 5, w - 8, true);
    wave(x + 4, y + h - 5, w - 8, true);
    wave(x + 5, y + 4, h - 8, false);
    wave(x + w - 5, y + 4, h - 8, false);
  } else if (kind === "stamp") {
    const r = 3.2;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    for (let t = r; t < w; t += r * 2) {
      ctx.moveTo(x + t - r, y + r);
      ctx.arc(x + t, y + r, r, Math.PI, 0, true);
    }
    for (let t = r; t < h; t += r * 2) {
      ctx.arc(x + w - r, y + t, r, -Math.PI / 2, Math.PI / 2, true);
    }
    for (let t = r; t < w; t += r * 2) {
      ctx.arc(x + w - t, y + h - r, r, 0, Math.PI, true);
    }
    for (let t = r; t < h; t += r * 2) {
      ctx.arc(x + r, y + h - t, r, Math.PI / 2, -Math.PI / 2, true);
    }
    ctx.closePath();
    ctx.stroke();
    frame(ctx, x + 7, y + 7, w - 14, h - 14, 1);
  } else if (kind === "brackets") {
    const L = Math.min(22, w * 0.18, h * 0.22);
    ctx.lineWidth = 3;
    const corner = (cx, cy, dx, dy) => {
      ctx.beginPath();
      ctx.moveTo(cx + dx * L, cy);
      ctx.lineTo(cx, cy);
      ctx.lineTo(cx, cy + dy * L);
      ctx.stroke();
    };
    corner(x + 3, y + 3, 1, 1);
    corner(x + w - 3, y + 3, -1, 1);
    corner(x + 3, y + h - 3, 1, -1);
    corner(x + w - 3, y + h - 3, -1, -1);
  } else if (kind === "deco") {
    frame(ctx, x + 6, y + 6, w - 12, h - 12, 1.4);
    const L = 14;
    ctx.lineWidth = 2;
    const orn = (cx, cy) => {
      ctx.beginPath();
      ctx.moveTo(cx - L, cy);
      ctx.lineTo(cx, cy);
      ctx.lineTo(cx, cy - L);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, 3, 0, Math.PI * 2);
      ctx.fill();
    };
    orn(x + 16, y + 16);
    ctx.save();
    ctx.translate(x + w - 16, y + 16); ctx.rotate(Math.PI / 2); ctx.translate(- (x + 16), -(y + 16));
    orn(x + 16, y + 16);
    ctx.restore();
    ctx.save();
    ctx.translate(x + 16, y + h - 16); ctx.rotate(-Math.PI / 2); ctx.translate(- (x + 16), -(y + 16));
    orn(x + 16, y + 16);
    ctx.restore();
    ctx.save();
    ctx.translate(x + w - 16, y + h - 16); ctx.rotate(Math.PI); ctx.translate(- (x + 16), -(y + 16));
    orn(x + 16, y + 16);
    ctx.restore();
  } else if (kind === "diamonds") {
    frame(ctx, x + 8, y + 8, w - 16, h - 16, 1.3);
    const diamond = (dx, dy) => {
      ctx.beginPath();
      ctx.moveTo(dx, dy - 5);
      ctx.lineTo(dx + 4, dy);
      ctx.lineTo(dx, dy + 5);
      ctx.lineTo(dx - 4, dy);
      ctx.closePath();
      ctx.fill();
    };
    perimeter(x + 4, y + 4, w - 8, h - 8, 12, (px, py) => diamond(px, py));
  } else if (ICONS[kind]) {
    frame(ctx, x + 10, y + 10, w - 20, h - 20, 1.2);
    const s = Math.max(7, Math.min(w, h) * 0.055);
    perimeter(x + s + 2, y + s + 2, w - 2 * s - 4, h - 2 * s - 4, s * 2.4, (px, py) => {
      ICONS[kind](ctx, px, py, s);
    });
  } else {
    frame(ctx, x, y, w, h, 2);
  }
  ctx.restore();
}
