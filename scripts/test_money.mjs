/* 金额大写自测：所有单据必须走同一个出口 amtWords
   规则：整数 = 前缀 + 英文 + ONLY；小数 = 前缀 + 英文 + CENTS + 英文（不加 ONLY） */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const cut = (from, to) => {
  const a = html.indexOf(from), b = html.indexOf(to);
  if (a < 0 || b < 0) { console.error("抽取失败：", from); process.exit(1); }
  return html.slice(a, b);
};
const src = cut("const ONES=", "/* 单位复数");
const { words, amtWords, words0 } = new Function(src + "\n return {words,amtWords,words0};")();

let bad = 0;
const is = (name, got, want) => {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}`);
  if (!ok) console.log(`   得：${JSON.stringify(got)}\n   期：${JSON.stringify(want)}`);
};

console.log("— 整数金额 —");
is("89615（POCIB 例）", amtWords(89615, "USD"),
  "USD EIGHTY NINE THOUSAND SIX HUNDRED AND FIFTEEN ONLY");
is("76220（A 案例合同额）", amtWords(76220, "USD"),
  "USD SEVENTY SIX THOUSAND TWO HUNDRED AND TWENTY ONLY");
is("152600（B 案例合同额）", amtWords(152600, "USD"),
  "USD ONE HUNDRED AND FIFTY TWO THOUSAND SIX HUNDRED ONLY");
is("0 也给 ONLY", amtWords(0, "USD"), "USD ZERO ONLY");
is("不传前缀默认 USD", amtWords(100), "USD ONE HUNDRED ONLY");
is("可换前缀", amtWords(100, "EUR"), "EUR ONE HUNDRED ONLY");

console.log("\n— 带小数 —");
is("1007.5（POCIB 例）", amtWords(1007.5, "USD"), "USD ONE THOUSAND AND SEVEN CENTS FIFTY");
is("0.05 只有分", amtWords(0.05, "USD"), "USD ZERO CENTS FIVE");
is("小数结尾不加 ONLY", /ONLY$/.test(amtWords(1007.5, "USD")), false);

console.log("\n— 连字符 —");
is("21 不带连字符", amtWords(21, "USD"), "USD TWENTY ONE ONLY");
is("words0 去掉所有连字符", words0(99), "NINETY NINE");
is("words 仍保留连字符（件数大写要用原样）", words(99), "NINETY-NINE");

console.log("\n— 全程序只走一个出口 —");
is("没有 words(D.amount) 的漏网用例", html.indexOf("words(D.amount)") < 0, true);
is("没有 mWords 旧函数", html.indexOf("function mWords") < 0, true);
const sites = (html.match(/amtWords\(/g) || []).length;
is("amtWords 调用点数量（≥6 处单据）", sites >= 6, true);

console.log("");
console.log(bad ? `${bad} 项不通过` : "全部通过");
process.exit(bad ? 1 : 0);
