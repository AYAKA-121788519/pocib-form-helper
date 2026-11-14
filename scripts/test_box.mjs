/* 集装箱选型算法自测：从 app/index.html 抽取 planBox 相关代码执行 */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const a = html.indexOf("/* ---------------- 集装箱选型");
const b = html.indexOf("function derived(){");
if (a < 0 || b < 0) { console.error("抽取失败"); process.exit(1); }
const src = html.slice(a, b);

const pre = "const n0=v=>Math.round(v).toLocaleString('en-US');\nconst n3=v=>(v||0).toFixed(3);\nconst nW=v=>String((v||0).toFixed(2));\n";
const make = new Function(pre + src + "\n return {planBox,boxLabel,boxEnLabel,boxField};");
const { planBox, boxLabel, boxEnLabel, boxField } = make();

let bad = 0;
const t = (name, vol, tne, rf, expect) => {
  const r = planBox(vol, tne, rf);
  const got = r ? boxLabel(r) : "null";
  const ok = expect === null ? !r : got === expect;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name.padEnd(26)} ${String(vol).padStart(8)} CBM / `
    + `${String(tne).padStart(6)} TNE → ${got}`
    + (r ? `  (${r.n}柜, 装载${(r.util * 100).toFixed(1)}%)` : "  (空)")
    + (ok ? "" : `  期望 ${expect}`));
};

console.log("— 普柜 —");
t("零体积", 0, 0, 0, null);
t("A 案例 1000×咖啡机", 232.39, 22, 0, "4×40'普柜");
t("B 案例 20000×龙眼罐头", 225.88, 224, 0, "8×40'普柜");
t("小货 30 CBM", 30, 20, 0, "1×20'普柜");
t("重货 30 CBM/24TNE", 30, 24, 0, "1×20'普柜");
t("中货 40 CBM", 40, 5, 0, "1×40'普柜");
t("90 CBM", 90, 10, 0, "2×40'普柜");
t("74 CBM 临界高柜", 74, 10, 0, "1×40'高柜");
t("155 CBM", 155, 24, 0, "3×40'普柜");
t("拼箱 6 CBM", 6, 1, 0, "1×20'普柜");
t("1000 CBM", 1000, 120, 0, "14×40'高柜");

console.log("\n— 冻柜 —");
t("冻货 100 CBM/50TNE", 100, 50, 1, "2×40'冻柜");
t("冻货 200 CBM/100TNE", 200, 100, 1, "4×40'冻柜");
t("冻货 20 CBM", 20, 12, 1, "1×20'冻柜");

console.log("\n— 成文口径 —");
const d1 = { box: planBox(232.39, 22, 0), total_vol: 232.39, total_gw: 22000 };
const d2 = { box: planBox(6, 1, 0), total_vol: 6, total_gw: 1000 };
console.log("整箱：" + boxField(d1));
console.log("拼箱：" + boxField(d2));
console.log("英文：" + boxEnLabel(planBox(232.39, 22, 0)));

/* 性能：连续调用 200 次 */
const t0 = performance.now();
for (let i = 0; i < 200; i++) planBox(1000 + i, 120, i % 2);
console.log(`\n性能：200 次大货选型 ${(performance.now() - t0).toFixed(1)} ms`);
console.log(bad ? `\n${bad} 项不符` : "\n全部通过");
process.exit(bad ? 1 : 0);
