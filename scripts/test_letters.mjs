/* 函电模块（iframe 内嵌）自测：
   1) index.html 里的 LETTERS_B64 必须与 app/_letters_src.html 完全一致（改完忘了重嵌就会报错）
   2) 关键联动代码必须在：件数/毛重/体积带入、装量、公司国别、结果行
   3) 运费卡的可重算输入已绑事件
   用法：node scripts/test_letters.mjs
*/
import fs from "fs";
import path from "path";
import crypto from "crypto";

const ROOT = path.resolve(process.cwd());
const APP = fs.readFileSync(path.join(ROOT, "app", "index.html"));
const SRC = fs.readFileSync(path.join(ROOT, "app", "_letters_src.html"));

let pass = 0, fail = 0;
const is = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log(`${ok ? "  ✓" : "  ✗"} ${name}${ok ? "" : ` → 期望 ${JSON.stringify(want)}，实际 ${JSON.stringify(got)}`}`);
  ok ? pass++ : fail++;
};

const m = APP.toString("utf8").match(/const LETTERS_B64="([^"]*)"/);
is("index.html 里有 LETTERS_B64", !!m, true);
const embedded = m ? Buffer.from(m[1], "base64") : Buffer.alloc(0);
const md5 = b => crypto.createHash("md5").update(b).digest("hex");
is("内嵌函电与源码一致（不一致就跑 scripts/build_letters.py）", md5(embedded), md5(SRC));

const h = SRC.toString("utf8");
is("运费卡有件数输入", h.includes('id="fQty"'), true);
is("运费卡有结果商品行", h.includes('id="foGoods"'), true);
is("有装量全局量 PACK_QTY", h.includes("var PACK_QTY"), true);
is("有公司国别全局量 CO_COUNTRY", h.includes("var CO_COUNTRY"), true);
is("预算国别优先用公司国别", /portOptionOf\(lSel, CO_COUNTRY\.ex\)/.test(h) && /coCut\(lSel\.value\)\s*\|\|\s*CO_COUNTRY\.ex/.test(h), true);
is("手改港口后清掉公司国别覆盖", /CO_COUNTRY\[id==="portLoad"\?"ex":"im"\]=""/.test(h), true);
is("缺工厂价时不硬算报价", h.includes('"缺工厂价"'), true);
is("港口选项带运价表键名", (h.match(/data-key="/g) || []).length >= 20, true);
is("有按航线刷新单价", h.includes("function refreshFreightRates"), true);
is("运费卡不再有「计算商品运费」按钮", !/onclick="calcFreight\(\)"/.test(h), true);
is("运费不再有「一键填入运费」按钮", !/onclick="autoFreight\(\)"/.test(h), true);
is("运费结果区常显", !/id="fResult"[^>]*display:none/.test(h), true);
is("算完自动写进预算", h.includes("syncFreightToBudget"), true);
is("函电改港口会回传主程序", h.includes("LETTERS_ADOPT_PORTS"), true);

const ids = ["fQty", "fWt", "fVol", "r20", "r40", "r40h", "rLCLv", "rLCLw", "rr20", "rr40", "rr40h", "rrLCLv", "rrLCLw", "rMin", "ra45", "ra100", "ra300", "ra300p"];
const bind = h.match(/\["fQty","fWt","fVol",[\s\S]{0,400}?\]\.forEach/);
is("运费卡输入已绑定重算", !!bind, true);
for (const id of ids) is(`  ${id} 存在`, h.includes(`id="${id}"`), true);

const main = APP.toString("utf8");
is("带入时填件数（取 derived().packs）", /set\("fQty", n0\(D\.packs\)/.test(main), true);
is("带入时填单件毛重体积", /set\("fWt", D\.gw1\)[\s\S]{0,40}set\("fVol", D\.vol1\)/.test(main), true);
is("带入时传装量给函电", /PACK_QTY=\+\$\("pack_qty"\)\.value/.test(main), true);
is("带入时填市场价", /autoFill\("bMarket"/.test(main), true);
is("工厂价按出口国出厂价带一次（主面板不再硬推）", main.includes("window.LETTERS_FACTORY_PRICE")
   && !/autoFill\("bFactory"/.test(main) && h.includes("function autoFactoryPrice"), true);
is("带入时按术语方向填运费", /buyerFrt\?0:frt/.test(main), true);
is("主面板改动会自动同步", (main.match(/lettersLiveSync\(\)/g) || []).length >= 2, true);
is("有实时同步开关", main.includes('id="liveSyncChk"'), true);
is("同步受开关控制", /if\(!LMOUNTED \|\| !liveOn\(\)\) return;/.test(main), true);
is("给函电暴露运价查询", main.includes("window.LETTERS_FREIGHT"), true);
is("给函电暴露港口回传", main.includes("window.LETTERS_ADOPT_PORTS"), true);

console.log(`\n${pass} 项通过${fail ? `，${fail} 项失败` : ""}`);
process.exit(fail ? 1 : 0);
