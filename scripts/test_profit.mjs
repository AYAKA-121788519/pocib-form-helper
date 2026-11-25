import { chromium } from "playwright-core";
import path from "node:path";
import fs from "node:fs";

const ROOT = "D:/pocib-helper";
const OUT = path.join(ROOT, "video/hf1440p/renders/qa");
fs.mkdirSync(OUT, { recursive: true });
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const APP = "file:///" + path.join(ROOT, "app/index.html").replace(/\\/g, "/");

const browser = await chromium.launch({ executablePath: CHROME, headless: true,
  args: ["--allow-file-access-from-files", "--hide-scrollbars"] });
const ctx = await browser.newContext({ viewport: { width: 2000, height: 1200 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
page.on("pageerror", (e) => console.log("[page err]", e.message.slice(0, 200)));
await page.goto(APP, { waitUntil: "load" });
await page.waitForTimeout(1500);
await page.click('.mode[data-mode="letter"]');
await page.waitForTimeout(3000);

const frame = page.frames().find((f) => f !== page.mainFrame());
if (!frame) { console.log("no iframe"); process.exit(1); }

const read = () => frame.evaluate(() => {
  const b = window.__BUDGET || {};
  const g = (id) => {
    const e = document.getElementById(id);
    return e ? e.textContent.trim() : null;
  };
  return {
    hasPanel: !!document.getElementById("pftBalAbs"),
    price: document.getElementById("bPrice").value,
    exRate: g("pftExRate"), imRate: g("pftImRate"),
    exAmt: g("pftExAmt"), imAmt: g("pftImAmt"),
    relL: g("pftRelL"), relR: g("pftRelR"),
    note: g("pftNote"),
    sliders: [document.getElementById("pftExSlider").value,
              document.getElementById("pftImSlider").value,
              document.getElementById("pftRelSlider").value],
    B: b.N ? { N: b.N, UP: +b.UP.toFixed(2), exRG: +(b.exPftRG * 100).toFixed(2),
               imRG: +(b.imPftRG * 100).toFixed(2), exG: +b.exPftG.toFixed(2),
               imG: +b.imPftG.toFixed(2) } : null,
    resultShown: document.getElementById("bResult").style.display,
  };
});

const setSlider = (id, v) => frame.evaluate(([i, val]) => {
  const el = document.getElementById(i);
  el.value = String(val);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}, [id, v]);

console.log("=== 初始 ===");
console.log(JSON.stringify(await read(), null, 1));

console.log("=== 点「计算预算」 ===");
await frame.evaluate(() => document.querySelector('button[onclick="calcBudget()"]').click());
await page.waitForTimeout(700);
console.log(JSON.stringify(await read(), null, 1));

console.log("=== 出口滑块 → 30% ===");
await setSlider("pftExSlider", 30);
await page.waitForTimeout(800);
console.log(JSON.stringify(await read(), null, 1));

console.log("=== 进口滑块 → 12% ===");
await setSlider("pftImSlider", 12);
await page.waitForTimeout(800);
console.log(JSON.stringify(await read(), null, 1));

console.log("=== 相对滑轨 → 70% ===");
await setSlider("pftRelSlider", 70);
await page.waitForTimeout(800);
console.log(JSON.stringify(await read(), null, 1));

console.log("=== 一键平衡绝对盈亏 ===");
await frame.evaluate(() => document.getElementById("pftBalAbs").click());
await page.waitForTimeout(900);
console.log(JSON.stringify(await read(), null, 1));

console.log("=== 一键平衡相对盈亏 ===");
await frame.evaluate(() => document.getElementById("pftBalRel").click());
await page.waitForTimeout(1200);
console.log(JSON.stringify(await read(), null, 1));

const shot = path.join(OUT, "pft_panel.png");
const el = await page.$("#lettersFrame");
await el.screenshot({ path: shot });
console.log("截图", shot);

await browser.close();
