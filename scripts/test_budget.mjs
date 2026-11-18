/* 进出口预算的费用口径自测（对照 POCIB 百科「出口报价 / 进口核算 / 三个报价实例」）：
   1) 商检费按监管条件自动判定：出口含 B（或合同选了商检证书）、进口含 A 才收 0.25%
   2) 银行手续费低于银行最低手续费时按最低收（T/T 定金+尾款两次分别判）
   3) 触发最低手续费时，参考报价换成不含 m 的公式，报价会抬高
   4) 进口「其他」只有 DAP 计入
   用法：node scripts/test_budget.mjs
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
  pre.textContent=["%%BG","R%%"].join("")+window.__out.join("\\n")+["%%BG","E%%"].join("");
  document.body.appendChild(pre);
};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const until=async(fn,ms=6000)=>{ const t0=Date.now(); while(Date.now()-t0<ms){ try{ const v=fn(); if(v) return v; }catch(e){} await sleep(100);} return null; };

(async()=>{
 try{
  const ok=window.__ok;
  CASE="A"; const c=CASES[CASE];
  const hsBak=c.hs, zhBak=c.hs_zh;

  /* ---------- 1. 商检费按监管条件判定 ---------- */
  c.hs="2005800000"; $("hs").value=c.hs; compute();
  document.querySelector('.mode[data-mode="letter"]').click();
  const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("bY1") ? x : null; }, 8000);
  if(!f){ ok("函电模块加载", false); window.__done(); return; }
  await sleep(700);
  const d=f.contentDocument, w=f.contentWindow;
  const val=id=>parseFloat(d.getElementById(id).value);
  const txt=()=>d.getElementById("bResult").textContent;
  const setHs=async(hs)=>{ c.hs=hs; $("hs").value=hs; compute(); bridgeToLetters(true); await sleep(450); };

  /* 案例 A 的合同 DOCUMENTS 选了「品质证书、健康证书」→ 按规则即使没有 B 也要报检，
     先清空单据，单独验证监管条件本身 */
  const docsBak=(c.docs_clause||[]).slice();
  c.docs_clause=[];
  bridgeToLetters(true); await sleep(500);
  ok("AB 商品：出口商检 0.25%", val("bX5")===0.25, val("bX5"));
  ok("AB 商品：进口商检 0.25%", val("bY4")===0.25, val("bY4"));
  ok("提示写明监管条件与是否报检", /监管条件/.test(d.getElementById("taxTip").textContent)
     && /出口商检 按报价 0\\.25%/.test(d.getElementById("taxTip").textContent),
     d.getElementById("taxTip").textContent.slice(0,120));

  /* 05010000 监管条件 9B：出口要报检、进口不用 */
  await setHs("0501000000");
  ok("只有 B：出口商检 0.25%", val("bX5")===0.25, val("bX5"));
  ok("只有 B：进口商检 0（无 A）", val("bY4")===0, val("bY4"));

  /* 05100030 监管条件 8AF：进口要报检、出口不用 */
  await setHs("0510003000");
  ok("只有 A：出口商检 0（无 B）", val("bX5")===0, val("bX5"));
  ok("只有 A：进口商检 0.25%", val("bY4")===0.25, val("bY4"));

  /* 15220000 监管条件 9：两边都不报检 */
  await setHs("1522000000");
  ok("没有 A/B：出口商检 0", val("bX5")===0, val("bX5"));
  ok("没有 A/B：进口商检 0", val("bY4")===0, val("bY4"));

  /* ---------- 2. 银行最低手续费 ---------- */
  await setHs("2005800000");
  const exSel=d.getElementById("bExCountry");
  exSel.value="澳大利亚"; exSel.dispatchEvent(new Event("change",{bubbles:true}));
  const paySel=d.getElementById("bPay");
  paySel.value="LC"; paySel.dispatchEvent(new Event("change",{bubbles:true}));
  await sleep(300);
  ok("未配置最低手续费时为空 0", val("bX10")===0, val("bX10"));

  w.MINFEE["澳大利亚"].LC=777.77;
  w.syncBudget(); await sleep(150);
  ok("最低手续费带到界面", Math.abs(val("bX10")-777.77)<1e-6, val("bX10"));
  w.calcBudget(); await sleep(250);
  ok("银行费用按最低手续费计（本币 777.77）", txt().indexOf("777.77")>=0,
     txt().slice(0,0)||"没找到");

  /* T/T：定金 30% + 尾款 70%，两笔都低于最低 → 收两次最低 */
  paySel.value="TT"; paySel.dispatchEvent(new Event("change",{bubbles:true}));
  w.MINFEE["澳大利亚"].TT=500.11;
  d.getElementById("bX11").value="30";
  w.syncBudget(); await sleep(150);
  w.calcBudget(); await sleep(250);
  ok("T/T 定金+尾款各取最低，合计两次", txt().indexOf("1,000.22")>=0,
     "没找到 1,000.22");

  /* ---------- 3. 报价公式在最低手续费档切换 ---------- */
  paySel.value="LC"; paySel.dispatchEvent(new Event("change",{bubbles:true}));
  w.MINFEE["澳大利亚"].LC=0; w.syncBudget(); await sleep(120);
  w.calcBudget(); await sleep(200);
  const qNoMin=parseFloat(String(d.getElementById("bQuoteT").value).replace(/[^0-9.]/g,""))||0;
  w.MINFEE["澳大利亚"].LC=100000; w.syncBudget(); await sleep(120);
  w.calcBudget(); await sleep(200);
  const qMin=parseFloat(String(d.getElementById("bQuoteT").value).replace(/[^0-9.]/g,""))||0;
  ok("触发最低手续费后参考报价抬高", qNoMin>0 && qMin>qNoMin, qNoMin+" → "+qMin);
  w.MINFEE["澳大利亚"].LC=0; w.syncBudget(); await sleep(120);

  /* ---------- 4. 进口「其他」只有 DAP 计入 ---------- */
  const modeSel=d.getElementById("bMode");
  d.getElementById("bY6").value="1234.56";
  modeSel.value="CIF"; modeSel.dispatchEvent(new Event("change",{bubbles:true}));
  w.calcBudget(); await sleep(200);
  ok("CIF 时进口其他不计入", txt().indexOf("1,234.56")<0);
  modeSel.value="DAP"; modeSel.dispatchEvent(new Event("change",{bubbles:true}));
  w.calcBudget(); await sleep(200);
  ok("DAP 时进口其他计入（1234.56）", txt().indexOf("1,234.56")>=0);
  d.getElementById("bY6").value="0";
  modeSel.value="CIF"; modeSel.dispatchEvent(new Event("change",{bubbles:true}));

  /* ---------- 5. 用百科实例 3（L/C + CFR + 海运，南非→巴西）复算一遍 ----------
     收购价 147×10000=ZAR1,470,000；退税 13%/增值税 13% → 退税 169,115.04、实际采购成本 1,300,884.96
     报关费 92、其他 40、商检 0.25%、L/C 0.13%、运费 USD1850、报价 USD202,000
     期望：商检 3,902.63、银行 2,029.37、国内费用 6,063.99、FOB 成本 1,306,948.95、CFR 成本 1,321,245.70 */
  c.docs_clause=docsBak;
  const bModeSel=d.getElementById("bMode");
  bModeSel.value="CFR"; bModeSel.dispatchEvent(new Event("change",{bubbles:true}));
  paySel.value="LC"; paySel.dispatchEvent(new Event("change",{bubbles:true}));
  /* 税率手改锁住，避免被当前商品的税则覆盖 */
  w.TAX_MANUAL.bX3=w.TAX_MANUAL.bX4=w.TAX_MANUAL.bY1=w.TAX_MANUAL.bY2=w.TAX_MANUAL.bY3=true;
  w.TAX_MANUAL.bX5=true;
  const setV=(id,v)=>{ const el=d.getElementById(id); el.value=v; el.dispatchEvent(new Event("input",{bubbles:true})); };
  setV("bQty","10000"); setV("bPrice","20.2"); setV("bFactory","147");
  setV("bX7","40"); setV("bX5","0.25"); setV("bX3","13"); setV("bX4","13");
  setV("bExFreight","1850");
  /* 国家放在最后设：设完不要再触发其它 input，否则会被主程序回灌的案例值覆盖 */
  await sleep(200);
  d.getElementById("bExCountry").value="南非";
  d.getElementById("bExCountry").dispatchEvent(new Event("change",{bubbles:true}));
  d.getElementById("bImCountry").value="巴西";
  d.getElementById("bImCountry").dispatchEvent(new Event("change",{bubbles:true}));
  await sleep(300);
  w.calcBudget(); await sleep(300);
  const t3=txt();
  ok("实例3 收购价 1,470,000", t3.indexOf("1,470,000.00")>=0);
  ok("实例3 出口退税 169,115.04", t3.indexOf("169,115.04")>=0);
  ok("实例3 实际采购成本 1,300,884.96", t3.indexOf("1,300,884.96")>=0);
  ok("实例3 商检费 3,902.63", t3.indexOf("3,902.63")>=0);
  ok("实例3 银行费用 2,029.37", t3.indexOf("2,029.37")>=0);
  ok("实例3 国内费用 6,063.99", t3.indexOf("6,063.99")>=0);
  ok("实例3 FOB 成本 1,306,948.95", t3.indexOf("1,306,948.95")>=0);
  ok("实例3 CFR 成本 1,321,245.70", t3.indexOf("1,321,245.70")>=0);

  /* ---------- 6. 用百科实例 2（T/T + FCA + 空运，古巴→俄罗斯，雪茄）复算进口税费 ----------
     合同 USD103,600；运费 USD58,880.48；加成110%；空运一切险+战争罢工 4.3‰
     进口税 25%、消费税 36%、增值税 13%、商检 0.25%、报关 RUB340、T/T 0.1%
     期望：CIF 4,787,468.33 / 关税 1,196,867.08 / 完税 5,984,335.41 / 消费税 3,366,188.67
          增值税 1,215,568.13 / 国内费用 4,589,692.11 / 总成本 10,577,065.64 */
  w.TAX_MANUAL.bY4=true;
  bModeSel.value="FCA"; bModeSel.dispatchEvent(new Event("change",{bubbles:true}));
  paySel.value="TT"; paySel.dispatchEvent(new Event("change",{bubbles:true}));
  setV("bQty","800"); setV("bPrice","129.5");
  setV("bImFreight","58880.48"); setV("bExFreight","0");
  setV("bY1","25"); setV("bY2","36"); setV("bY3","13"); setV("bY4","0.25");
  setV("bZ1","1.1");
  await sleep(200);
  d.getElementById("bShip").value="air";
  d.getElementById("bShip").dispatchEvent(new Event("change",{bubbles:true}));
  d.getElementById("bExCountry").value="古巴";
  d.getElementById("bExCountry").dispatchEvent(new Event("change",{bubbles:true}));
  d.getElementById("bImCountry").value="俄罗斯";
  d.getElementById("bImCountry").dispatchEvent(new Event("change",{bubbles:true}));
  await sleep(300);
  w.calcBudget(); await sleep(300);
  const t2=txt();
  ok("实例2 空运费率 4.3‰", d.getElementById("bZ2").value.indexOf("4.3")>=0, d.getElementById("bZ2").value);
  /* 百科原例中间步骤各自四舍五入，末位有几分钱差，按 ±0.5 元比对 */
  const nums=[...t2.matchAll(/[\\d,]+\\.\\d\\d/g)].map(x=>parseFloat(x[0].replace(/,/g,"")));
  const near=(want)=>nums.some(n=>Math.abs(n-want)<=0.5);
  ok("实例2 CIF 成交价 4,787,468.33", near(4787468.33), near(4787468.33));
  ok("实例2 进口关税 1,196,867.08", near(1196867.08), near(1196867.08));
  ok("实例2 完税成本 5,984,335.41", near(5984335.41), near(5984335.41));
  ok("实例2 消费税 3,366,188.67", near(3366188.67), near(3366188.67));
  ok("实例2 增值税 1,215,568.13", near(1215568.13), near(1215568.13));
  ok("实例2 国内费用 4,589,692.11", near(4589692.11), near(4589692.11));
  ok("实例2 总成本 10,577,065.64", near(10577065.64), near(10577065.64));

  c.hs=hsBak; c.hs_zh=zhBak;
  window.__done();
 }catch(e){
  document.body.insertAdjacentHTML("beforeend","<pre id=\\"OUT\\">"+["%%BG","R%%"].join("")+"FAIL 脚本抛错 :: "+(e&&e.message)+" @ "+((e&&e.stack||"").split("\\n")[1]||"")+["%%BG","E%%"].join("")+"</pre>");
 }
})();
</script>`;

let syntaxBad = 0;
[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m, i) => {
  try { new Function(m[1]); } catch (e) { syntaxBad++; console.log(`✗ 第 ${i + 1} 个脚本块语法错误：${e.message}`); }
});
if (!syntaxBad) console.log("✓ 脚本块语法检查通过");

const tmp = "build/_budget_test.html";
fs.mkdirSync("build", { recursive: true });
fs.writeFileSync(tmp, html.replace(/<\/body>(?![\s\S]*<\/body>)/, probe + "</body>"), "utf8");

const exe = process.env.CHROME || ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium"].find(p => { try { return fs.existsSync(p); } catch (e) { return false; } });
if (!exe) { console.log("✗ 找不到 Chrome，跳过"); process.exit(syntaxBad ? 1 : 0); }

const dom = execFileSync(exe, ["--headless=new", "--disable-gpu", "--no-sandbox",
  "--allow-file-access-from-files", "--virtual-time-budget=25000", "--dump-dom",
  "file:///" + process.cwd().replace(/\\/g, "/") + "/" + tmp], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

const m = dom.match(/%%BGR%%([\s\S]*?)%%BGE%%/);
if (!m) { console.log("✗ 测试脚本没跑起来"); process.exit(1); }
const lines = m[1].trim().split(/\r?\n/).filter(Boolean);
let bad = 0;
lines.forEach(l => {
  const t = l.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
  if (t.startsWith("FAIL")) bad++;
  console.log(t.startsWith("FAIL") ? "✗ " + t.slice(5) : "✓ " + t.slice(5));
});
console.log(`\n${lines.length - bad}/${lines.length} 通过`);
fs.unlinkSync(tmp);
process.exit(bad || syntaxBad ? 1 : 0);
