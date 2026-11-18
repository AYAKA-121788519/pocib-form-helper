/* POCIB 机构价目（邮局 / 化学材料测试中心 / 银行 / 海关）落到预算里的自测：
   1) 邮局寄单费、运输条件鉴定费按国家取值（抓自 institutions 页面）
   2) 银行最低手续费 EUR19 / 押汇 EUR190 按各国本币折算
   3) 海关商检证书按份收（品质 10、数量/重量 4、植物检疫 4、健康 4 EUR），产地证 3 EUR
   4) 出口「其他费用」自动汇总，可手改、清空恢复
   5) DAP / DPU 在出口侧加 USD300 内陆运费 + USD20 卸货费
   用法：node scripts/test_charges.mjs
*/
import fs from "fs";
import { execFileSync } from "child_process";

const html = fs.readFileSync("app/index.html", "utf8");

const probe = `
<script>
window.__out=[];
window.__ok=(n,cond,extra)=>window.__out.push((cond?"PASS ":"FAIL ")+n+(extra!==undefined?" :: "+extra:""));
window.__done=()=>{
  if(document.getElementById("OUT")) return;
  const pre=document.createElement("pre"); pre.id="OUT";
  pre.textContent=["%%CH","G%%"].join("")+window.__out.join("\\n")+["%%CH","E%%"].join("");
  document.body.appendChild(pre);
};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const until=async(fn,ms=6000)=>{ const t0=Date.now(); while(Date.now()-t0<ms){ try{ const v=fn(); if(v) return v; }catch(e){} await sleep(100);} return null; };

(async()=>{
 try{
  const ok=window.__ok;
  CASE="A"; const c=CASES[CASE];

  document.querySelector('.mode[data-mode="letter"]').click();
  const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("bX7") ? x : null; }, 8000);
  if(!f){ ok("函电模块加载", false); window.__done(); return; }
  await sleep(700);
  const d=f.contentDocument, w=f.contentWindow;
  const val=id=>parseFloat(d.getElementById(id).value);
  const setSel=async(id,v)=>{ const el=d.getElementById(id); el.value=v; el.dispatchEvent(new Event("change",{bubbles:true})); await sleep(250); };

  /* ---------- 1. 价目表：10 国齐全 ---------- */
  const P=w.POSTAGE, C=w.CHEM;
  ok("邮局价目 10 国", P && Object.keys(P).length===10, P&&Object.keys(P).length);
  ok("化工鉴定价目 10 国", C && Object.keys(C).length===10, C&&Object.keys(C).length);
  ok("美国寄单 USD5 / 化工 USD173", P["美国"].amt===5 && C["美国"]===173, P["美国"].amt+"/"+C["美国"]);
  ok("德国寄单 EUR2 / 化工 EUR130", P["德国"].amt===2 && C["德国"]===130, P["德国"].amt+"/"+C["德国"]);
  ok("日本寄单 JPY662 / 化工 JPY20446", P["日本"].amt===662 && C["日本"]===20446, P["日本"].amt+"/"+C["日本"]);

  /* ---------- 2. 欧元折本币：报关费就是 EUR9 折出来的 ---------- */
  ok("德国 1EUR = 1EUR（customs 9）", Math.abs(w.eurLocal("德国")-1)<1e-9, w.eurLocal("德国"));
  ok("美国 1EUR ≈ 1.333 USD（customs 12）", Math.abs(w.eurLocal("美国")-12/9)<1e-9, w.eurLocal("美国"));
  ok("日本 1EUR ≈ 172 JPY（customs 1550）", Math.abs(w.eurLocal("日本")-1550/9)<1e-9, w.eurLocal("日本"));

  /* ---------- 3. 银行最低手续费 ---------- */
  await setSel("bExCountry","德国");
  await setSel("bPay","LC");
  ok("德国 L/C 最低手续费 19（EUR19×1）", val("bX10")===19, val("bX10"));
  await setSel("bExCountry","美国");
  ok("美国 L/C 最低手续费 25（EUR19 折 USD）", val("bX10")===25, val("bX10"));
  await setSel("bExCountry","德国");

  /* ---------- 4. 其他费用自动汇总 ---------- */
  c.docs_clause=[]; bridgeToLetters(true); await sleep(400);
  w.computeOtherEx();
  ok("只有产地证：其他费用 3（EUR3×1）", val("bX7")===3, val("bX7"));

  c.docs_clause=["品质证书","健康证书"]; bridgeToLetters(true); await sleep(400);
  w.computeOtherEx();
  ok("品质 10 + 健康 4：其他费用 3+14=17", val("bX7")===17, val("bX7"));
  ok("其他费用明细写清项目", /商检证书/.test(d.getElementById("x7Tip").textContent),
     d.getElementById("x7Tip").textContent.slice(0,120));

  /* 同一种证书不重复计（数量证书 / 重量证书是同一张） */
  c.docs_clause=["数量证书","重量证书"]; bridgeToLetters(true); await sleep(400);
  w.computeOtherEx();
  ok("数量/重量证书算一份（3+4=7）", val("bX7")===7, val("bX7"));

  /* T/T 加 DHL 寄单费（德国 EUR2） */
  c.docs_clause=[]; bridgeToLetters(true); await sleep(300);
  await setSel("bPay","TT");
  w.computeOtherEx();
  ok("T/T 加寄单费（3+2=5）", val("bX7")===5, val("bX7"));
  ok("寄单费写进明细", /DHL 寄单费/.test(d.getElementById("x7Tip").textContent),
     d.getElementById("x7Tip").textContent.slice(0,120));
  await setSel("bPay","LC");

  /* 运输条件鉴定：只有 21001/40001/40002/06002 要 */
  const gBak=c.goods_no;
  c.goods_no="40002"; c.hs=c.hs; bridgeToLetters(true); await sleep(400);
  w.X7_MANUAL=false; w.computeOtherEx();
  ok("锂电池 40002 加鉴定费（3+130=133）", val("bX7")===133, val("bX7"));
  c.goods_no="01007"; bridgeToLetters(true); await sleep(400);
  w.X7_MANUAL=false; w.computeOtherEx();
  ok("普通商品不加鉴定费（3）", val("bX7")===3, val("bX7"));
  c.goods_no=gBak;

  /* 手改冻结 / 清空恢复（isTrusted 只有真人操作才为真，这里直接置标记验证逻辑） */
  const x7=d.getElementById("bX7");
  x7.value="88"; w.X7_MANUAL=true; w.computeOtherEx();
  ok("手改后不被自动值覆盖", val("bX7")===88, val("bX7"));
  ok("手改后提示改口径", /已手改/.test(d.getElementById("x7Tip").textContent),
     d.getElementById("x7Tip").textContent.slice(0,60));
  w.X7_MANUAL=false; w.computeOtherEx();
  ok("恢复自动后回到 3", val("bX7")===3, val("bX7"));

  /* ---------- 5. DAP / DPU 加进口国内陆运费与卸货费 ---------- */
  const mSel=d.getElementById("bMode");
  mSel.value="CIP"; mSel.dispatchEvent(new Event("change",{bubbles:true}));
  w.calcBudget(); await sleep(300);
  const tCip=d.getElementById("bResult").textContent;
  ok("CIP 不出现内陆运费行", tCip.indexOf("进口国内陆运费")<0);
  mSel.value="DAP"; mSel.dispatchEvent(new Event("change",{bubbles:true}));
  w.calcBudget(); await sleep(300);
  const tDap=d.getElementById("bResult").textContent;
  ok("DAP 出口侧有内陆运费 USD300", tDap.indexOf("进口国内陆运费")>=0 && tDap.indexOf("300.00")>=0);
  ok("DAP 出口侧有卸货费 USD20", tDap.indexOf("目的地卸货费")>=0);
  mSel.value="CIP"; mSel.dispatchEvent(new Event("change",{bubbles:true}));

  window.__done();
 }catch(e){
  window.__ok("异常："+(e&&e.message), false); window.__done();
 }
})();
</script>`;

const tmp = "build/_test_charges.html";
fs.mkdirSync("build", { recursive: true });
fs.writeFileSync(tmp, html.replace("</body>", probe + "</body>"));

const exe = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const dom = execFileSync(exe, ["--headless", "--disable-gpu", "--no-sandbox",
  "--allow-file-access-from-files", "--virtual-time-budget=30000", "--dump-dom",
  "file:///" + process.cwd().replace(/\\/g, "/") + "/" + tmp],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

const m = dom.match(/%%CHG%%([\s\S]*?)%%CHE%%/);
if (!m) { console.log("没取到断言输出（页面可能没跑完）"); process.exit(1); }
const lines = m[1].trim().split("\n");
const pass = lines.filter(l => l.startsWith("PASS")).length;
const fails = lines.filter(l => l.startsWith("FAIL"));
lines.forEach(l => console.log((l.startsWith("PASS") ? "✓ " : "✗ ") + l.slice(5)));
console.log(`\n${pass}/${lines.length} 通过`);
fs.unlinkSync(tmp);
process.exit(fails.length ? 1 : 0);
