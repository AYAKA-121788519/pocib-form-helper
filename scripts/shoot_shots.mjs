/**
 * 为介绍片抓界面截图 + 量分区坐标。
 * 输出：video/assets/shots/*.png 与 video/regions.json
 * 用法：node scripts/shoot_shots.mjs
 */
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const ROOT = "D:/pocib-helper";
const OUT = path.join(ROOT, "video/assets/shots");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const APP = "file:///" + path.join(ROOT, "app/index.html").replace(/\\/g, "/");

fs.mkdirSync(OUT, { recursive: true });

const hideAuthor = `
  .author{visibility:hidden !important}
  html{scrollbar-width:none}
  body::-webkit-scrollbar{display:none}
`;

const box = (el) => {
  const r = el.getBoundingClientRect();
  return {
    x: Math.round(r.left + window.scrollX),
    y: Math.round(r.top + window.scrollY),
    w: Math.round(r.width),
    h: Math.round(r.height),
  };
};

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--allow-file-access-from-files", "--hide-scrollbars", "--force-device-scale-factor=2"],
});
const ctx = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 2,
});
const page = await ctx.newPage();
page.on("console", (m) => {
  if (m.type() === "error") console.log("[page]", m.text().slice(0, 160));
});

await page.goto(APP, { waitUntil: "load" });
await page.addStyleTag({ content: hideAuthor });
await page.waitForTimeout(1200);

/* ---------- 1. 主面板 ---------- */
await page.screenshot({ path: path.join(OUT, "panel.png"), fullPage: true });

const panelRegions = await page.evaluate((boxSrc) => {
  const box = eval("(" + boxSrc + ")");
  const secs = [...document.querySelectorAll("main > section")];
  const names = ["trade", "flow", "derive", "pair", "tariff"];
  const out = { panel: { x: 0, y: 0, w: 1920, h: Math.round(document.body.scrollHeight) } };
  secs.slice(0, 5).forEach((s, i) => (out[names[i]] = box(s)));
  return out;
}, box.toString());

/* ---------- 2. 税则查询结果 ---------- */
await page.fill("#tfQ", "8516710000").catch(() => {});
await page.click("#tfGo").catch(() => {});
await page.waitForTimeout(900);
await page.screenshot({ path: path.join(OUT, "panel-tariff.png"), fullPage: true });
const tariffRegion = await page.evaluate((boxSrc) => {
  const box = eval("(" + boxSrc + ")");
  const secs = [...document.querySelectorAll("main > section")];
  return { tariff: box(secs[4]), h: Math.round(document.body.scrollHeight) };
}, box.toString());

/* ---------- 3. 函电与预算 ---------- */
await page.click('.mode[data-mode="letter"]');
await page.waitForFunction(() => {
  const f = document.getElementById("lettersFrame");
  return f && f.contentDocument && f.contentDocument.querySelectorAll(".card").length > 4;
}, null, { timeout: 20000 });
await page.waitForTimeout(1500);

const frameEl = await page.$("#lettersFrame");
const frame = await frameEl.contentFrame();

// 算预算 + 生成九封函电
await frame.evaluate(() => {
  try { calcBudget(); } catch (e) { console.log("calcBudget fail", e.message); }
  try { genAll(); } catch (e) { console.log("genAll fail", e.message); }
});
await page.waitForTimeout(2500);

// 函电区是 position:fixed + overflow:clip，得先解开才能整页截图
const letterH = await frame.evaluate(() => document.body.scrollHeight);
await page.evaluate((h) => {
  document.documentElement.style.overflow = "visible";
  document.body.style.overflow = "visible";
  document.body.style.height = "auto";
  const w = document.getElementById("letterWrap");
  if (w) {
    w.style.position = "static";
    w.style.height = "auto";
    w.style.overflow = "visible";
  }
  const f = document.getElementById("lettersFrame");
  f.style.height = h + "px";
  f.style.overflow = "visible";
  f.style.flex = "none";
}, letterH);
await page.waitForTimeout(1000);
await page.screenshot({ path: path.join(OUT, "letters.png"), fullPage: true });

const letters = await page.evaluate((boxSrc) => {
  const box = eval("(" + boxSrc + ")");
  const f = document.getElementById("lettersFrame");
  const fr = f.getBoundingClientRect();
  const d = f.contentDocument;
  const at = (sel) => {
    const el = d.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      x: Math.round(fr.left + r.left),
      y: Math.round(fr.top + window.scrollY + r.top),
      w: Math.round(r.width),
      h: Math.round(r.height),
    };
  };
  return {
    page: { x: 0, y: 0, w: 1920, h: Math.round(document.body.scrollHeight) },
    lettersTop: at(".cols"),
    freight: at("#freightCard"),
    budget: at("#budgetCard"),
    result: at("#resultCard"),
    docH: d.body.scrollHeight,
  };
}, box.toString());

const regions = {
  panel: { img: "assets/shots/panel.png", ...panelRegions.panel },
  trade: { img: "assets/shots/panel.png", ...panelRegions.trade },
  flow: { img: "assets/shots/panel.png", ...panelRegions.flow },
  derive: { img: "assets/shots/panel.png", ...panelRegions.derive },
  pair: { img: "assets/shots/panel.png", ...panelRegions.pair },
  tariff: { img: "assets/shots/panel-tariff.png", ...tariffRegion.tariff },
  lettersTop: { img: "assets/shots/letters.png", ...letters.lettersTop },
  freight: { img: "assets/shots/letters.png", ...letters.freight },
  budget: { img: "assets/shots/letters.png", ...letters.budget },
  result: { img: "assets/shots/letters.png", ...letters.result },
};

fs.writeFileSync(
  path.join(ROOT, "video/regions.json"),
  JSON.stringify(regions, null, 2),
  "utf8"
);

console.log("panel", panelRegions);
console.log("tariff", tariffRegion.tariff);
console.log("letters", letters);
await browser.close();
