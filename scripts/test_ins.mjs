/* 保险费率组合自测（POCIB 保险公司「保险条款费率表」）：
   1) 基本险只能选一种：一切险 8 / 水渍险 6 / 平安险 5 / ICC A 8 / B 6 / C 5（‰）
   2) 空运：航空运输险 2 / 航空运输一切险 3.5（‰）
   3) 特殊附加险：战争险、罢工险各 0.8‰，同时投保只计一次（不累加）
   4) 默认 = 一切险 + 战争 + 罢工 = 8.8‰；空运默认 = 航空运输一切险 + 0.8 = 4.3‰
   5) 改险别后总保费率与出口预算的「总保费率」行同步
   用法：node scripts/test_ins.mjs
*/
import fs from "fs";
import { execFileSync } from "child_process";

const html = fs.readFileSync("app/index.html", "utf8");

const probe = `
<script>
window.__out=[];
window.__ok=(n,c,x)=>window.__out.push((c?"PASS ":"FAIL ")+n+(x!==undefined?" :: "+x:""));
window.__done=()=>{
  if(document.getElementById("OUT")) return;
  const pre=document.createElement("pre"); pre.id="OUT";
  pre.textContent=["%%IN","R%%"].join("")+window.__out.join("\\n")+["%%IN","E%%"].join("");
  document.body.appendChild(pre);
};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const until=async(fn,ms=9000)=>{ const t0=Date.now(); while(Date.now()-t0<ms){ try{ const v=fn(); if(v) return v; }catch(e){} await sleep(100);} return null; };

(async()=>{
 try{
  const ok=window.__ok;
  document.querySelector('.mode[data-mode="letter"]').click();
  const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("bInsBase") ? x : null; });
  if(!f){ ok("函电模块加载", false); window.__done(); return; }
  await sleep(1200);
  const d=f.contentDocument, W=f.contentWindow;
  const V=id=>String(d.getElementById(id).value);
  const pick=(id,v)=>{ const el=d.getElementById(id); el.value=v; el.dispatchEvent(new Event("change",{bubbles:true})); };
  const chk=(id,v)=>{ const el=d.getElementById(id); el.checked=v; el.dispatchEvent(new Event("change",{bubbles:true})); };
  const rate=()=>parseFloat(V("bZ2").replace("%",""));

  /* 1) 默认：海运 一切险 + 战争 + 罢工 = 8.8‰ */
  ok("默认基本险是一切险", V("bInsBase")==="all", V("bInsBase"));
  ok("默认两个附加险都勾上", d.getElementById("bInsWar").checked && d.getElementById("bInsStrike").checked,
     [d.getElementById("bInsWar").checked, d.getElementById("bInsStrike").checked].join("/"));
  ok("默认总保费率 8.8‰", rate()===8.8, V("bZ2"));

  /* 2) 战争/罢工同时投保只算一次 */
  chk("bInsStrike", false);
  ok("只留战争险仍是 8.8‰（不因少一个而变）", rate()===8.8, V("bZ2"));
  chk("bInsWar", false);
  ok("附加险全不选 = 8.0‰", rate()===8, V("bZ2"));
  chk("bInsStrike", true);
  ok("只选罢工险 = 8.8‰", rate()===8.8, V("bZ2"));
  chk("bInsWar", true);
  ok("两个都选仍 8.8‰（不是 9.6‰）", rate()===8.8, V("bZ2"));

  /* 3) 基本险切换 */
  pick("bInsBase", "wpa");
  ok("水渍险 6 + 0.8 = 6.8‰", rate()===6.8, V("bZ2"));
  pick("bInsBase", "fpa");
  chk("bInsWar", false); chk("bInsStrike", false);
  ok("平安险 5 + 无附加 = 5.0‰", rate()===5, V("bZ2"));
  pick("bInsBase", "iccb");
  ok("ICC(B) 6 + 无附加 = 6.0‰", rate()===6, V("bZ2"));
  pick("bInsBase", "icca");
  ok("ICC(A) 8 + 无附加 = 8.0‰", rate()===8, V("bZ2"));
  pick("bInsBase", "iccc");
  ok("ICC(C) 5 + 无附加 = 5.0‰", rate()===5, V("bZ2"));

  /* 4) 切空运：选项换成两项，默认航空运输一切险 */
  pick("bShip", "air");
  chk("bInsWar", true);
  await sleep(300);
  ok("空运基本险只有 2 项", d.getElementById("bInsBase").options.length===2,
     d.getElementById("bInsBase").options.length);
  ok("空运默认航空运输一切险", V("bInsBase")==="airall", V("bInsBase"));
  ok("空运默认 3.5 + 0.8 = 4.3‰", rate()===4.3, V("bZ2"));
  pick("bInsBase", "airr");
  ok("航空运输险 2 + 0.8 = 2.8‰", rate()===2.8, V("bZ2"));

  /* 5) 切回海运：选项恢复 6 项，默认一切险 */
  pick("bShip", "sea");
  await sleep(300);
  ok("海运基本险恢复 6 项", d.getElementById("bInsBase").options.length===6,
     d.getElementById("bInsBase").options.length);
  ok("切回海运默认一切险 8.8‰", V("bInsBase")==="all" && rate()===8.8, V("bInsBase")+" "+V("bZ2"));

  /* 6) 总保费率进预算表（保费行只在 CIF/CIP/DAP/DPU 出现，先切 CIF） */
  pick("bInsBase", "wpa");
  chk("bInsWar", false); chk("bInsStrike", false);
  d.getElementById("bMode").value="CIF"; W.syncBudget();
  W.calcBudget(); await sleep(250);
  ok("预算表总保费率 6.00 ‰（水渍险，无附加）",
     d.getElementById("bResult").textContent.indexOf("6.00 ‰")>=0, "没找到 6.00 ‰");
  chk("bInsStrike", true);
  W.calcBudget(); await sleep(200);
  ok("加回罢工险后 6.80 ‰", d.getElementById("bResult").textContent.indexOf("6.80 ‰")>=0,
     "没找到 6.80 ‰");

  window.__done();
 }catch(e){
  document.body.insertAdjacentHTML("beforeend","<pre id=\\"OUT\\">"+["%%IN","R%%"].join("")+"FAIL 脚本抛错 :: "+(e&&e.message)+["%%IN","E%%"].join("")+"</pre>");
 }
})();
</script>`;

let syntaxBad = 0;
[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m, i) => {
  try { new Function(m[1]); } catch (e) { syntaxBad++; console.log(`✗ 第 ${i + 1} 个脚本块语法错误：${e.message}`); }
});
if (!syntaxBad) console.log("✓ 脚本块语法检查通过");

const tmp = "build/_ins_test.html";
fs.mkdirSync("build", { recursive: true });
fs.writeFileSync(tmp, html.replace(/<\/body>(?![\s\S]*<\/body>)/, probe + "</body>"), "utf8");

const exe = process.env.CHROME || ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium"].find(p => { try { return fs.existsSync(p); } catch (e) { return false; } });
if (!exe) { console.log("✗ 找不到 Chrome，跳过"); process.exit(syntaxBad ? 1 : 0); }

const dom = execFileSync(exe, ["--headless=new", "--disable-gpu", "--no-sandbox",
  "--allow-file-access-from-files", "--virtual-time-budget=25000", "--dump-dom",
  "file:///" + process.cwd().replace(/\\/g, "/") + "/" + tmp], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

const m = dom.match(/%%INR%%([\s\S]*?)%%INE%%/);
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
