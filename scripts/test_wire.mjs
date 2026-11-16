/* 境外汇款申请书：定金 / 尾款拆分口径自测
   例文取自 POCIB「境外汇款申请书填写说明」：合同 15656.76，付 30% 定金 → 4697.03 / 10959.73 */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const cut = (from, to) => {
  const a = html.indexOf(from), b = html.indexOf(to);
  if (a < 0 || b < 0) { console.error("抽取失败：", from); process.exit(1); }
  return html.slice(a, b);
};
const src = cut("/* 单位归一", "function derived(){");
const { paySplit, contractDate, countryCode } = new Function(
  src + "\n return {paySplit,contractDate,countryCode};")();

const r2 = v => Math.round((+v || 0) * 100) / 100;
let bad = 0;
const is = (name, got, want) => {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}${ok ? "" : `\n   得 ${JSON.stringify(got)}　期 ${JSON.stringify(want)}`}`);
};

console.log("— 支付条款拆比例 —");
is("40/60 两段式", JSON.stringify(paySplit("40% IN ADVANCE AND 60% WITHIN 30DAYS AFTER SHIPMENT DATE")),
  JSON.stringify({ pre: 40, post: 60 }));
is("30/70 两段式", JSON.stringify(paySplit("30% IN ADVANCE AND 70% WITHIN 30DAYS AFTER SHIPMENT")),
  JSON.stringify({ pre: 30, post: 70 }));
is("100% 全额 → null", paySplit("T/T 100% IN ADVANCE"), null);
is("两个数不凑 100 → null", paySplit("30% IN ADVANCE AND 30% AFTER"), null);
is("无百分比 → null", paySplit("L/C AT SIGHT"), null);

console.log("\n— 定金 / 尾款（官方例：合同 15656.76，定金 30%）—");
{
  const amt = 15656.76, sp = paySplit("30% IN ADVANCE AND 70% WITHIN 30DAYS");
  const dep = r2(amt * sp.pre / 100);
  const bal = r2(amt - dep);
  is("定金四舍五入到分", dep, 4697.03);
  is("尾款 = 合同 − 定金", bal, 10959.73);
  is("两笔合计回到合同额", r2(dep + bal), 15656.76);
}

console.log("\n— 合同日期 / 国别代码 —");
is("合同号取前 8 位", contractDate({ contract: "2026110302" }), "2026-11-03");
is("非数字合同号", contractDate({ contract: "SC-001" }), "");
is("德国", countryCode("Germany"), "304");
is("美国", countryCode("America"), "502");
is("大小写不敏感", countryCode("GERMANY"), "304");
is("未知国家", countryCode("Atlantis"), "");

console.log(bad ? `\n${bad} 项不通过` : "\n全部通过");
process.exit(bad ? 1 : 0);
