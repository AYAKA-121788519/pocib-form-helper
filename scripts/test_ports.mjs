/* 港口中文名 / 中文国别自测（入境检验检疫要中文港名与中文国别） */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const cut = (from, to) => {
  const a = html.indexOf(from), b = html.indexOf(to);
  if (a < 0 || b < 0) { console.error("抽取失败：", from); process.exit(1); }
  return html.slice(a, b);
};
const src = cut("const PORTS = [", "const TERMS=")
          + cut("/* 港口中文名", "/* 以重量作为销售单位");
const { portZh, countryZhOf } = new Function(src + "\n return {portZh,countryZhOf};")();

let bad = 0;
const is = (name, got, want) => {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}${ok ? "" : `\n   得 ${JSON.stringify(got)}　期 ${JSON.stringify(want)}`}`);
};

console.log("— 港口中文名 —");
is("汉堡", portZh("HAMBURG, GERMANY"), "汉堡");
is("纽约", portZh("NEW YORK, AMERICA"), "纽约");
is("小写也认", portZh("new york, america"), "纽约");
is("里约热内卢", portZh("RIO DE JANEIRO, BRAZIL"), "里约热内卢");
is("自定义港原样", portZh("OSAKA, JAPAN"), "OSAKA, JAPAN");
is("空值", portZh(""), "");

console.log("\n— 中文国别 —");
is("优先公司档案 country_zh", countryZhOf({ country_zh: "德国" }, "NEW YORK, AMERICA"), "德国");
is("档案没中文国名时从港口取", countryZhOf({}, "HAMBURG, GERMANY"), "德国");
is("都没有时回退英文国名", countryZhOf({ country: "Germany" }, ""), "Germany");
is("空公司不报错", countryZhOf(null, ""), "");

console.log(bad ? `\n${bad} 项不符` : "\n全部通过");
process.exit(bad ? 1 : 0);
