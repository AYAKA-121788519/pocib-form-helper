/* POCIB 重量/体积/报价数量口径自测：从 app/index.html 抽取真代码执行
   用例取自官方「商品相关规则」的 5 个例题 + 报价数量核算的 2 个例题 */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const a = html.indexOf("/* ---------------- 集装箱选型");
const b = html.indexOf("function renderCap(d){");
if (a < 0 || b < 0) { console.error("抽取失败"); process.exit(1); }
const src = html.slice(a, b);

const n0 = v => Math.round(v).toLocaleString("en-US");
const n3 = v => (v || 0).toFixed(3);
const nW = v => String((v || 0).toFixed(2));
const make = new Function(src + "\n return {calcWeights,capOf,planBox,BOXES};");
const { calcWeights, capOf, BOXES } = make();

const B = k => BOXES.find(x => x.k === k);
let bad = 0;

const eq = (name, got, want, tol = 0.005) => {
  const ok = Math.abs(got - want) <= tol;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name.padEnd(30)} 得 ${got}　期望 ${want}`);
};

console.log("— 例1 02002：5000 件，20 件/箱 → 250 箱 —");
{
  const w = calcWeights(5000, 20, 22, 20, 0.1, "PC", "CARTON");
  eq("包装箱数", w.packs, 250);
}

console.log("\n— 例2 04006：9000 块，30 块/箱，毛 10.5 净 8.5 体积 0.2904 —");
{
  const w = calcWeights(9000, 30, 10.5, 8.5, 0.2904, "块", "CARTON");
  console.log("   注：9000/30 整除，两种口径同值");
  eq("毛重 KGS", w.total_gw, 3150, 0.01);
  eq("净重 KGS", w.total_nw, 2550, 0.01);
  eq("体积 CBM", w.total_vol, 87.12, 0.001);
}

console.log("\n— 例3 08001：1000 辆，6 辆/箱，毛 23 净 21 体积 0.08052（不能整除）—");
{
  const w = calcWeights(1000, 6, 23, 21, 0.08052, "UNIT", "CARTON");
  eq("包装箱数", w.packs, 167);
  eq("净重 KGS", w.total_nw, 3500, 0.01);
  eq("毛重 KGS", w.total_gw, 3834, 0.01);   // 3500 + 167×2，不是 167×23=3841
  eq("体积 CBM", w.total_vol, 13.447, 0.001);
}

console.log("\n— 例4 01001：2000 箱，销售单位=包装单位 —");
{
  const w = calcWeights(2000, 1, 11.2, 10.2, 0.014739, "CARTON", "CARTON");
  console.log("   同单位判定:", w.sameUnit);
  eq("毛重 KGS", w.total_gw, 22400, 0.01);
  eq("净重 KGS", w.total_nw, 20400, 0.01);
  eq("体积 CBM", w.total_vol, 29.478, 0.001);
}

console.log("\n— 例5 22006：20 MT，1 包装单位 = 0.02 销售单位 —");
{
  const w = calcWeights(20, 0.02, 20.4, 20, 0.0367, "MT", "CARTON");
  eq("包装箱数", w.packs, 1000);
  eq("毛重 KGS", w.total_gw, 20400, 0.01);
  eq("净重 KGS", w.total_nw, 20000, 0.01);
  eq("体积 CBM", w.total_vol, 36.7, 0.001);
}

console.log("\n— 报价数量 例1 01005：销售=包装，0.025736CBM / 20.196KGS —");
{
  const w = calcWeights(1237, 1, 20.196, 19.0, 0.025736, "CARTON", "CARTON");
  eq("20' 可装箱数", capOf(B("20GP"), 0.025736, 20.196), 1237);
  eq("40' 可装箱数", capOf(B("40GP"), 0.025736, 20.196), 1435);
  console.log("   同单位，报价数量 = 箱数", w.sameUnit);
}

console.log("\n— 报价数量 例2 08003：6 辆/箱，0.0576CBM / 21KGS —");
{
  const w = calcWeights(572, 6, 21, 20, 0.0576, "UNIT", "CARTON");
  eq("20' 可装箱数", capOf(B("20GP"), 0.0576, 21), 572);
  eq("20' 折销售数量", 572 * 6, 3432);
  eq("40' 可装箱数", capOf(B("40GP"), 0.0576, 21), 1163);
  eq("40' 折销售数量", 1163 * 6, 6978);
  console.log("   不同单位判定:", !w.sameUnit);
}

console.log("\n— 边界 —");
{
  const w0 = calcWeights(0, 6, 23, 21, 0.08, "UNIT", "CARTON");
  eq("数量为 0 时箱数", w0.packs, 0);
  const w1 = calcWeights(6, 6, 23, 21, 0.08, "UNIT", "CARTON");
  eq("刚好整箱 6/6", w1.packs, 1);
  const w2 = calcWeights(7, 6, 23, 21, 0.08, "UNIT", "CARTON");
  eq("7/6 进位", w2.packs, 2);
  eq("7 辆净重 3.5×7", w2.total_nw, 24.5, 0.01);
  eq("7 辆毛重 24.5+2×2", w2.total_gw, 28.5, 0.01);
  const w3 = calcWeights(2000, 1, 11.2, 11.2, 0.01, "CARTON", "CARTON");
  eq("皮重为 0 时毛重=净重", w3.total_gw, 2000 * 11.2, 0.01);
}

console.log(bad ? `\n${bad} 项不符` : "\n全部通过");
process.exit(bad ? 1 : 0);
