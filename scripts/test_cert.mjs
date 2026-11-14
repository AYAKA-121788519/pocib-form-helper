/* 产地证 6~10 栏成文自测：从 app/index.html 抽取真代码执行
   用例取自 POCIB「普惠制产地证」填制说明里的 25002 黄金项链例子 */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const cut = (from, to) => {
  const a = html.indexOf(from), b = html.indexOf(to);
  if (a < 0 || b < 0) { console.error("抽取失败：", from); process.exit(1); }
  return html.slice(a, b);
};
const src = cut("const ONES=", "/* 金额大写")
          + cut("const PLURAL_MAP=", "/* ---------------- 渲染")
          + cut("/* 单位归一", "function derived(){");

const make = new Function(src + "\n return {words,plur,uq,packWords,goodsDescField,gwOrQty};");
const { words, packWords, goodsDescField, gwOrQty } = make();

let bad = 0;
const is = (name, got, want) => {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}`);
  if (!ok) console.log(`   得：${JSON.stringify(got)}\n   期：${JSON.stringify(want)}`);
};

console.log("— 包装数量英文大写 —");
is("99", packWords(99), "NINETY NINE (99)");
is("100", packWords(100), "ONE HUNDRED (100)");
is("800", packWords(800), "EIGHT HUNDRED (800)");
is("1237", packWords(1237), "ONE THOUSAND TWO HUNDRED AND THIRTY SEVEN (1237)");
is("1", packWords(1), "ONE (1)");

console.log("\n— 7 栏：包装数量 + 种类 + OF + 品名 + 规格（官方 25002 例）—");
const c1 = {
  goods: "24K Gold Pendant Necklace",
  desc: "24K Pure gold, Gold Weight: 9.50g, Length: 40CM, Packaging: 1pc/box, 10boxes/carton",
  pack_unit: "CARTON", unit: "PC", qty: 990,
};
is("7 栏", goodsDescField(c1, { packs: 99 }),
  "NINETY NINE (99) CARTONS OF 24K Gold Pendant Necklace\n"
  + "24K Pure gold, Gold Weight: 9.50g, Length: 40CM, Packaging: 1pc/box, 10boxes/carton");

console.log("\n— 9 栏：以「件」为销售单位填数量 —");
is("2000 件", gwOrQty({ qty: 2000, unit: "PC" }, { total_gw: 40000, total_nw: 38000, gw1: 20 }),
  "2000PCS");
is("1 件（单数）", gwOrQty({ qty: 1, unit: "PC" }, { total_gw: 20, total_nw: 19, gw1: 20 }), "1PC");
is("500 辆", gwOrQty({ qty: 500, unit: "UNIT" }, { total_gw: 1000, total_nw: 900, gw1: 5 }), "500UNITS");

console.log("\n— 9 栏：以重量为销售单位填毛重（官方 23001 例：2625KGS）—");
is("20 MT 原蔗糖", gwOrQty({ qty: 20, unit: "MT" }, { total_gw: 2625, total_nw: 2600, gw1: 20 }),
  "2625KGS");
is("只有净重 → N.W.", gwOrQty({ qty: 5, unit: "MT" }, { total_gw: 500, total_nw: 500, gw1: 0 }),
  "N.W. 500 KGS");
is("≤1 公斤用单数 KG", gwOrQty({ qty: 1, unit: "KG" }, { total_gw: 1, total_nw: 1, gw1: 1 }), "1KG");

console.log("\n— 英文数字拼写兜底 —");
is("words(3834) 原始带连字符", words(3834), "THREE THOUSAND EIGHT HUNDRED AND THIRTY-FOUR");
is("packWords(3834) 去掉连字符", packWords(3834),
  "THREE THOUSAND EIGHT HUNDRED AND THIRTY FOUR (3834)");

console.log(bad ? `\n${bad} 项不通过` : "\n全部通过");
process.exit(bad ? 1 : 0);
