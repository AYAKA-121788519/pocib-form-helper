/* 流程单据清单自测：核对 POCIB 百科《各流程提交单据列表》
   重点：保险单只随 CIF/CIP 出现、空运换单、鉴定书只对指定品目 */
import fs from "fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const cut = (from, to) => {
  const a = html.indexOf(from), b = html.indexOf(to);
  if (a < 0 || b < 0) { console.error("抽取失败：", from); process.exit(1); }
  return html.slice(a, b);
};
const src = 'let CASE="A";\n'
  + cut("const CASES = {", "/* 21 个环节")
  + cut("const EXCISE_ZH=", "/* 单据随运输方式换名")
  + cut("const FLOW = [", "/* ---------------- 工具")
  + cut("/* 单据随运输方式换名", "function renderFlow");
const { CASES, FLOW, docsOf, setCase } =
  new Function(src + "\n return {CASES,FLOW,docsOf,setCase:v=>{CASE=v;}};")();

let bad = 0;
const is = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "✓" : "✗"} ${name}`);
  if (!ok) console.log(`   得：${JSON.stringify(got)}\n   期：${JSON.stringify(want)}`);
};
const at = (s) => FLOW.find(f => f.s === s);
const docs = (s) => docsOf(at(s)).d;
const who = (s) => docsOf(at(s)).by;
const has = (s, name) => docs(s).indexOf(name) >= 0;

console.log("— B 案例：CIP + L/C + 海运 —");
setCase("B");                                     // 出口美国，CIP
is("7 办理保险由出口商投", who(7), "出口商");
is("7 办理保险带商业发票", docs(7), ["商业发票", "投保单"]);
is("11 交单带保险单（CIP）", has(11, "货物运输保险单"), true);
is("11 交单带海运提单", has(11, "海运提单"), true);
is("11 交单带押汇申请书", has(11, "出口押汇申请书（办押汇才交）"), true);
is("11 商检证书按合同条款", [has(11, "商检证书-品质证书"), has(11, "商检证书-健康证书")], [true, true]);
is("8 送货：01007 不要鉴定书", docs(8), []);

console.log("\n— B 案例改空运 —");
CASES.B.transport = "空运";
is("3 订舱换空运委托书", docs(3)[0], "国际空运委托书");
is("9 出口报关加航空运单", has(9, "航空运单"), true);
is("10 取回提单：空运无此步", docs(10), []);
is("11 交单换航空运单", [has(11, "海运提单"), has(11, "航空运单")], [false, true]);
is("16 取提货单：空运无需单据", docs(16), []);
is("18 进口报检：提货通知单 + 航空运单", docs(18).slice(0, 2), ["提货通知单", "航空运单"]);
is("19 进口报关：同上", docs(19).slice(0, 2), ["提货通知单", "航空运单"]);
is("21 提货：同上", docs(21), ["提货通知单", "航空运单"]);
CASES.B.transport = "海运";

console.log("\n— A 案例：FOB + D/A + 海运 —");
setCase("A");
is("7 办理保险由进口商投", who(7), "进口商");
is("7 只交投保单（FOB 出口商不投保）", docs(7), ["投保单"]);
is("11 交单不带保险单（FOB）", has(11, "货物运输保险单"), false);
is("11 交单首两单是托收委托书与汇票", docs(11).slice(0, 2), ["托收委托书", "汇票"]);
is("11 交单带押汇申请书", has(11, "出口押汇申请书（办押汇才交）"), true);

console.log("\n— T/T 不押汇 —");
CASES.A.payment = "T/T";
is("11 交单无押汇申请书", has(11, "出口押汇申请书（办押汇才交）"), false);
is("11 交单无汇票", has(11, "汇票"), false);
CASES.A.payment = "D/A";

console.log("\n— 送货鉴定书只认四个品目 —");
[["21001", true], ["40001", true], ["40002", true], ["06002", true], ["26006", false]].forEach(([no, want]) => {
  CASES.A.goods_no = no;
  is(`${no} 送货要鉴定书`, has(8, "货物运输条件鉴定书"), want);
  is(`${no} 出口报关${want ? "要" : "不要"}鉴定书`, has(9, "货物运输条件鉴定书"), want);
});
CASES.A.goods_no = "26006";

console.log("\n— 进口缴税 —");
setCase("B");                                      // 龙眼罐头，不征消费税
is("01007 只出两张缴款书", docs(20).length, 2);
CASES.B.hs_zh = "十年陈酿红葡萄酒";
is("葡萄酒出三张（含消费税）", docs(20).length, 3);
CASES.B.hs_zh = "龙眼罐头";

console.log("");
console.log(bad ? `${bad} 项不通过` : "全部通过");
process.exit(bad ? 1 : 0);
