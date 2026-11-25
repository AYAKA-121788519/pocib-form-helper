import { chromium } from "playwright-core";
import path from "node:path";
import fs from "node:fs";

const ROOT = "D:/pocib-helper";
const OUT = path.join(ROOT, "video/hf1440p/renders/qa");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const APP = "file:///" + path.join(ROOT, "app/index.html").replace(/\\/g, "/");

const browser = await chromium.launch({ executablePath: CHROME, headless: true,
  args: ["--allow-file-access-from-files", "--hide-scrollbars"] });
const ctx = await browser.newContext({ viewport: { width: 2560, height: 1440 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
page.on("pageerror", (e) => console.log("[err]", e.message.slice(0, 160)));
await page.goto(APP, { waitUntil: "load" });
await page.waitForTimeout(1600);

// 说明书区域
const box = await page.evaluate(() => {
  const g = document.getElementById("guide");
  const r = g.getBoundingClientRect();
  return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
});
console.log("说明书尺寸", JSON.stringify(box));
await page.screenshot({ path: path.join(OUT, "guide_top.png"), clip: { x: 0, y: 0, width: 2560, height: Math.min(880, box.h + 120) } });

// 与三栏对齐检查
const align = await page.evaluate(() => {
  const secs = [...document.querySelectorAll("main > section")].slice(0, 3).map((e) => {
    const r = e.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.width)];
  });
  const lg = [...document.querySelectorAll(".gd-legend .lg")].map((e) => {
    const r = e.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.width)];
  });
  return { secs, lg };
});
console.log("栏位", JSON.stringify(align.secs), "\n图例", JSON.stringify(align.lg));

// 收起/展开
await page.click("#gdToggle");
await page.waitForTimeout(300);
const hidden = await page.evaluate(() => document.getElementById("gdBody").style.display);
console.log("收起后 display =", hidden);
await page.click("#gdToggle");
await page.waitForTimeout(300);

// 整页高度
const h = await page.evaluate(() => Math.round(document.body.scrollHeight));
console.log("页面总高", h);

await browser.close();
