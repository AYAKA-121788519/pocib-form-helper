/* 选品比价自测：汇率折算、交集、价差与毛利率 */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const cut = (from, to) => {
  const a = html.indexOf(from), b = html.indexOf(to);
  if (a < 0 || b < 0) { console.error("抽取失败：", from); process.exit(1); }
  return html.slice(a, b);
};
const src = "const PRICE={};\n"
  + cut("/* __PRICE_DATA_BEGIN__ */", "/* __PRICE_DATA_END__ */")
  + cut("const FX_KEY=", "function syncPair")
  + cut("function money(", "function renderPair");
const { PNAME, PRICE, fxUsd, pairCalc, FX_DEF } =
  new Function(src + "\n return {PNAME,PRICE,fxUsd,pairCalc,FX_DEF};")();

let bad = 0;
const is = (name, got, want) => {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}${ok ? "" : `\n   得 ${JSON.stringify(got)}　期 ${JSON.stringify(want)}`}`);
};
const near = (name, got, want, tol = 0.01) => {
  const ok = Math.abs(got - want) <= tol;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}${ok ? "" : `\n   得 ${got}　期 ${want}`}`);
};

const FX = { ...FX_DEF };

console.log("— 汇率折算 —");
is("美元恒为 1", fxUsd("USD", FX), 1);
near("1 CNY = 1/6.8 USD", fxUsd("CNY", FX), 1 / 6.8);
near("1 EUR = 1/0.91 USD", fxUsd("EUR", FX), 1 / 0.91);
near("1 RUB = 1/33.3 USD", fxUsd("RUB", FX), 1 / 33.3);
is("汇率填 0 不除零", fxUsd("CNY", { ...FX, CNY: 0 }), 0);

console.log("\n— 价格表完整性 —");
is("五个国家", Object.keys(PRICE).sort().join(","), "中国,俄罗斯,德国,澳大利亚,美国");
is("商品名都有", Object.keys(PNAME).length >= 200, true);
let miss = 0;
for (const cn in PRICE) for (const k of ["m", "f"])
  for (const c in PRICE[cn][k]) if (!PNAME[c]) miss++;
is("价格表里的编号都有名字", miss, 0);
let pos = 0;
for (const cn in PRICE) for (const c in PRICE[cn].f) if (!(PRICE[cn].f[c] > 0)) pos++;
is("工厂价都是正数", pos, 0);

console.log("\n— 交集与排序 —");
const rows = pairCalc("美国", "德国", FX);
is("美国工厂 → 德国市场有交集", rows.length > 10, true);
let sorted = true;
const s = [...rows].sort((a, b) => b.rate - a.rate);
for (let i = 1; i < s.length; i++) if (s[i].rate > s[i - 1].rate) sorted = false;
is("按毛利率能降序排", sorted, true);
is("不存在的国家返回空", pairCalc("火星", "美国", FX).length, 0);

console.log("\n— 单条换算 —");
const one = rows.find(r => r.code === "25019");
if (!one) {
  console.log("✗ 找不到 25019"); bad++;
} else {
  near("金玫瑰花 成本 = 20.20 USD", one.cost, 20.20);
  near("金玫瑰花 售价 = 38.39 EUR 折美元", one.sell, 38.39 / 0.91);
  near("价差", one.diff, 38.39 / 0.91 - 20.20);
  near("毛利率", one.rate, (38.39 / 0.91 - 20.20) / 20.20);
}

console.log("\n— 人民币国别键 —");
is("中国用 RMB 计价", PRICE["中国"].cur, "RMB");
is("中国工厂价带小数", typeof PRICE["中国"].f["01001"], "number");

console.log(bad ? `\n${bad} 项不通过` : "\n全部通过");
process.exit(bad ? 1 : 0);
