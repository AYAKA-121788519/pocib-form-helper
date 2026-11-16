/* 多币种账号取号自测：按单据币种选账号，缺币种不许拿别的币种顶 */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const cut = (from, to) => {
  const a = html.indexOf(from), b = html.indexOf(to);
  if (a < 0 || b < 0) { console.error("抽取失败：", from); process.exit(1); }
  return html.slice(a, b);
};
const src = cut("/* 多币种账号：按单据上的币种", "const LS_KEY=")
          + cut("function normUnit", "/* POCIB 重量体积口径");
const { acctOf, acctMiss } = new Function(src + "\n return {acctOf,acctMiss};")();

let bad = 0;
const is = (name, got, want) => {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}${ok ? "" : `\n   得 ${JSON.stringify(got)}　期 ${JSON.stringify(want)}`}`);
};

const de = { currency: "EUR", account_no: "6101000014043",
             accts: { EUR: "6101000014043", USD: "6222020012345678" } };
const us = { currency: "USD", account_no: "6101000014317" };

console.log("— 按币种取号 —");
is("有该币种 → 取该币种", acctOf(de, "USD"), "6222020012345678");
is("小写币种也能取", acctOf(de, "usd"), "6222020012345678");
is("本币走 account_no（无 accts 时）", acctOf(us, "USD"), "6101000014317");
is("本币同时在 accts 里以 accts 为准", acctOf(de, "EUR"), "6101000014043");
is("缺该币种 → 空，不拿本币顶", acctOf(de, "JPY"), "");
is("空公司 → 空", acctOf(null, "USD"), "");
is("空币种 → 空", acctOf(de, ""), "");
is("币种大小写对不上也不误取", acctOf({ currency: "RMB", account_no: "X1" }, "USD"), "");

console.log("\n— 缺号提示 —");
is("提示带上币种", acctMiss("JPY").indexOf("JPY") >= 0, true);
is("提示指向账户列表", acctMiss("USD").indexOf("账户列表") >= 0, true);
is("空币种兜底不报错", acctMiss("").indexOf("该币种") >= 0, true);

console.log(bad ? `\n${bad} 项不符` : "\n全部通过");
process.exit(bad ? 1 : 0);
