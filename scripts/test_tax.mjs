/* 税则近似匹配 + 函电预算税率跟随商品 自测：
   1) 粘 10 位 / 13 位完整编码、全角、带标点都能对上 8 位税则码
   2) 错一位 / 只输品目前缀时给出近似结果并标出来
   3) 函电预算里的进口税率 / 消费税 / 增值税 / 退税随商品 HS 变
   用法：node scripts/test_tax.mjs
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
  pre.textContent=["%%TX","R%%"].join("")+window.__out.join("\\n")+["%%TX","E%%"].join("");
  document.body.appendChild(pre);
};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const until=async(fn,ms=6000)=>{ const t0=Date.now(); while(Date.now()-t0<ms){ try{ const v=fn(); if(v) return v; }catch(e){} await sleep(100);} return null; };

(async()=>{
 try{
  const ok=window.__ok;

  /* ---------- 1. 编码近似匹配 ---------- */
  const M=hs=>tariffMatch(hs);
  let m=M("2005800000");
  ok("10 位报关码 → 8 位税则码", m && m.key==="20058000" && m.level==="cut", m && (m.key+"/"+m.level));
  m=M("2005800000001");
  ok("13 位附加码也对上", m && m.key==="20058000" && m.level==="cut", m && (m.key+"/"+m.level));
  m=M("２００５８０００");
  ok("全角数字先归一化", m && m.key==="20058000" && m.level==="exact", m && (m.key+"/"+m.level));
  m=M("2005.80.00.00");
  ok("带点/空格的写法也认", m && m.key==="20058000", m && (m.key+"/"+m.level));
  m=M("20058090");
  ok("错一位 → 同品目近似", m && m.key==="20058000" && m.level==="near" && m.diff===1, m && (m.key+"/"+m.level+"/"+m.diff));
  m=M("200580");
  ok("只输品目 → 取该品目第一条", m && m.key==="20058000" && m.level==="item", m && (m.key+"/"+m.level));
  m=M("9999999999");
  ok("完全对不上返回 null", m===null, JSON.stringify(m));
  m=M("8516711500");
  ok("8 位不在库但同品目有近邻", m && m.key==="85167110" && m.level==="near", m && (m.key+"/"+m.level));

  /* ---------- 2. 查询面板：粘完整编码也查得到 ---------- */
  let rows=tariffSearch("2005800000",50);
  ok("粘贴 10 位能查回 8 位条目", rows.length>=1 && rows[0][0]==="20058000", rows.length+" 条");
  rows=tariffSearch("2005800000001",50);
  ok("粘贴 13 位也查得到", rows.length>=1 && rows[0][0]==="20058000", rows.length+" 条");

  /* ---------- 3. 输入框下的提示行 ---------- */
  CASE="A"; const c=CASES[CASE];
  const hsBak=c.hs, zhBak=c.hs_zh;
  $("hs").value="2005800000001"; c.hs="2005800000001"; compute();
  let hint=$("hsMatch").textContent;
  ok("提示行写明对齐结果", /20058000/.test(hint) && /对齐/.test(hint), hint.slice(0,80));
  ok("提示行列出税率", /进口优惠 5%/.test(hint), hint.slice(0,120));
  $("hs").value="20058090"; c.hs="20058090"; compute();
  hint=$("hsMatch").textContent;
  ok("近似匹配会被标出来", /差 1 位/.test(hint), hint.slice(0,120));
  $("hs").value="甜玉米"; c.hs="甜玉米"; compute();
  hint=$("hsMatch").textContent;
  ok("填品名时给出可用编码", /20058/.test(hint), hint.slice(0,120));

  /* ---------- 4. 函电预算的税率跟着商品变 ---------- */
  c.hs="2005800000"; c.hs_zh="非用醋制作的未冷冻甜玉米";
  $("hs").value=c.hs; $("hs_zh").value=c.hs_zh;
  compute();
  document.querySelector('.mode[data-mode="letter"]').click();
  const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("bY1") ? x : null; }, 8000);
  if(!f){ ok("函电模块加载", false); window.__done(); return; }
  await sleep(700);
  const d=f.contentDocument;
  const val=id=>parseFloat(d.getElementById(id).value);
  bridgeToLetters(true);
  await sleep(500);
  ok("进口税率 = 甜玉米的 5%", val("bY1")===5, val("bY1"));
  ok("增值税率 = 13%", val("bY3")===13, val("bY3"));
  ok("消费税 = 0", val("bY2")===0, val("bY2"));
  ok("提示行写明取自哪条税则", /20058000/.test(d.getElementById("taxTip").textContent), d.getElementById("taxTip").textContent.slice(0,90));

  /* 换成葡萄酒：14% 关税 + 10% 消费税 */
  c.hs="2204210000"; c.hs_zh="小包装的鲜葡萄酿造的酒";
  $("hs").value=c.hs; $("hs_zh").value=c.hs_zh;
  compute(); bridgeToLetters(true);
  await sleep(500);
  ok("换商品后进口税率变 14%", val("bY1")===14, val("bY1"));
  ok("消费税率跟着变 10%", val("bY2")===10, val("bY2"));
  ok("出口栏消费税同步 10%", val("bX2")===10, val("bX2"));

  /* 换成小麦：增值税 9% —— 证明不只是关税在动 */
  c.hs="1001990000"; c.hs_zh="其他小麦及混合麦";
  $("hs").value=c.hs; $("hs_zh").value=c.hs_zh;
  compute(); bridgeToLetters(true);
  await sleep(500);
  ok("增值税率跟着变 9%", val("bY3")===9, val("bY3"));
  ok("出口栏增值税同步 9%", val("bX3")===9, val("bX3"));

  /* 退税：POCIB 各国海关都给本商品的出口退税率，不只有中国退（南非 13%、德国 9% 都有案例） */
  c.hs="2005800000"; $("hs").value=c.hs; compute(); bridgeToLetters(true);
  await sleep(400);
  const exSel=d.getElementById("bExCountry");
  exSel.value="澳大利亚"; exSel.dispatchEvent(new Event("change",{bubbles:true}));
  await sleep(250);
  ok("出口国非中国也按税则退税（9%）", val("bX4")===9, val("bX4"));
  exSel.value="中国"; exSel.dispatchEvent(new Event("change",{bubbles:true}));
  await sleep(250);
  ok("出口国是中国 → 退税率 9%", val("bX4")===9, val("bX4"));

  /* 算一遍预算，别出现 NaN */
  d.querySelector('button.btn-main[onclick="calcBudget()"]').click();
  await sleep(200);
  const txt=d.getElementById("bResult").textContent;
  ok("预算表算得出来且无 NaN", txt.length>50 && txt.indexOf("NaN")<0, txt.indexOf("NaN")<0? "ok":"含 NaN");
  /* 退税金额要按税则的 9% 算：收购价×9%/(1+13%) */
  const fac=parseFloat(d.getElementById("bFactory").value)||0;
  const qn =parseFloat(d.getElementById("bQty").value)||0;
  const want=((fac*qn*0.09)/1.13).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
  ok("预算表按 9% 退税算（"+want+"）", txt.indexOf(want)>=0, txt.indexOf(want)>=0? undefined : "没找到 "+want);

  c.hs=hsBak; c.hs_zh=zhBak;
  window.__done();
 }catch(e){
  document.body.insertAdjacentHTML("beforeend","<pre id=\\"OUT\\">"+["%%TX","R%%"].join("")+"FAIL 脚本抛错 :: "+(e&&e.message)+" @ "+((e&&e.stack||"").split("\\n")[1]||"")+["%%TX","E%%"].join("")+"</pre>");
 }
})();
</script>`;

let syntaxBad = 0;
[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m, i) => {
  try { new Function(m[1]); } catch (e) { syntaxBad++; console.log(`✗ 第 ${i + 1} 个脚本块语法错误：${e.message}`); }
});
if (!syntaxBad) console.log("✓ 脚本块语法检查通过");

const tmp = "build/_tax_test.html";
fs.mkdirSync("build", { recursive: true });
fs.writeFileSync(tmp, html.replace(/<\/body>(?![\s\S]*<\/body>)/, probe + "</body>"), "utf8");

const exe = process.env.CHROME || ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium"].find(p => { try { return fs.existsSync(p); } catch (e) { return false; } });
if (!exe) { console.log("✗ 找不到 Chrome，跳过"); process.exit(syntaxBad ? 1 : 0); }

const dom = execFileSync(exe, ["--headless=new", "--disable-gpu", "--no-sandbox",
  "--allow-file-access-from-files", "--virtual-time-budget=20000", "--dump-dom",
  "file:///" + process.cwd().replace(/\\/g, "/") + "/" + tmp], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

const m = dom.match(/%%TXR%%([\s\S]*?)%%TXE%%/);
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
