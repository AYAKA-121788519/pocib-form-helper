/* 商品报价（成交价）/ 数量 双向同步自测：
   1) 主面板单价 → 函电「商品与价格」单价、预算「成交单价」
   2) 函电改单价/成交单价 → 回传主面板（以前只做了单向，切回去就被旧值盖掉）
   3) 函电改数量 → 回传主面板
   4) 来回切换不被旧值拉回；主面板再改仍能推下去
   5) 实时同步关着时不采纳（返回 -1），值没变时不重复计算（返回 0）
   用法：node scripts/test_deal.mjs
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
  pre.textContent=["%%CP","R%%"].join("")+window.__out.join("\\n")+["%%CP","E%%"].join("");
  document.body.appendChild(pre);
};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const until=async(fn,ms=9000)=>{ const t0=Date.now(); while(Date.now()-t0<ms){ try{ const v=fn(); if(v) return v; }catch(e){} await sleep(100);} return null; };
const setv=(doc,id,v)=>{ const el=doc.getElementById(id); if(!el) return;
  el.value=v; el.dispatchEvent(new Event("input",{bubbles:true})); el.dispatchEvent(new Event("change",{bubbles:true})); };

(async()=>{
  try{
    const ok=window.__ok;
    setv(document,"unit_price","88.50");
    document.querySelector('.mode[data-mode="letter"]').click();
    const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("price") ? x : null; });
    if(!f){ ok("函电模块加载", false); window.__done(); return; }
    await sleep(1200);
    const d=f.contentDocument;
    const V=id=>String(d.getElementById(id).value);

    ok("主面板单价 → 函电单价", +V("price")===88.5, V("price"));
    ok("主面板单价 → 预算成交单价", +V("bPrice")===88.5, V("bPrice"));

    /* 函电里改单价 → 主面板 */
    setv(d,"price","123.45");
    await sleep(700);
    ok("函电改单价 → 主面板单价", +document.getElementById("unit_price").value===123.45, document.getElementById("unit_price").value);
    ok("函电改单价 → 案例里的单价", +CASES[CASE].unit_price===123.45, CASES[CASE].unit_price);
    ok("函电改单价 → 合同金额按新价重算", +String(d.getElementById("amount").value).replace(/,/g,"")===123.45*+V("qty"),
       d.getElementById("amount").value);

    /* 预算区成交单价 → 主面板 */
    setv(d,"bPrice","150");
    await sleep(700);
    ok("预算成交单价 → 主面板单价", +document.getElementById("unit_price").value===150, document.getElementById("unit_price").value);
    ok("预算成交单价 → 商品与价格单价", +V("price")===150, V("price"));

    /* 函电改数量 → 主面板 */
    setv(d,"qty","2000");
    await sleep(700);
    ok("函电改数量 → 主面板数量", +document.getElementById("qty").value===2000, document.getElementById("qty").value);

    /* 来回切换不被旧值拉回 */
    document.querySelector('.mode[data-mode="form"]').click(); await sleep(300);
    document.querySelector('.mode[data-mode="letter"]').click(); await sleep(1400);
    ok("切回函电单价没被拉回", +V("price")===150, V("price"));
    ok("切回主面板单价没被拉回", +document.getElementById("unit_price").value===150, document.getElementById("unit_price").value);

    /* 主面板再改价 → 函电跟随 */
    document.querySelector('.mode[data-mode="form"]').click(); await sleep(200);
    setv(document,"unit_price","99.9");
    await sleep(200);
    document.querySelector('.mode[data-mode="letter"]').click(); await sleep(1400);
    ok("主面板再改价 → 函电跟随", +V("price")===99.9, V("price"));

    /* 返回值：0=没变化，-1=实时同步关着 */
    ok("值没变时返回 0", LETTERS_ADOPT_DEAL(V("qty"), V("price"))===0, LETTERS_ADOPT_DEAL(V("qty"),V("price")));
    const chk=document.getElementById("liveSyncChk");
    const wasOn=!!(chk && chk.checked);
    if(chk){ chk.checked=false; chk.dispatchEvent(new Event("change",{bubbles:true})); }
    ok("关同步时返回 -1", LETTERS_ADOPT_DEAL("999","7.77")===-1, LETTERS_ADOPT_DEAL("999","7.77"));
    setv(d,"price","11.11");
    await sleep(600);
    ok("关同步时主面板不改", +document.getElementById("unit_price").value===99.9, document.getElementById("unit_price").value);
    if(chk && wasOn){ chk.checked=true; chk.dispatchEvent(new Event("change",{bubbles:true})); }
    await sleep(300);
    /* 重新开着同步再改一次 → 依然能回传 */
    setv(d,"price","12.34");
    await sleep(700);
    ok("重新开同步后回传恢复", +document.getElementById("unit_price").value===12.34, document.getElementById("unit_price").value);
  }catch(e){
    window.__ok("脚本异常", false, e && e.message);
  }
  window.__done();
})();
</script>`;

fs.writeFileSync("build/_deal.html", html.replace(/<\/body>(?![\s\S]*<\/body>)/, probe + "</body>"), "utf8");
const dom = execFileSync("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
   "--virtual-time-budget=40000", "--dump-dom", "file:///D:/pocib-helper/build/_deal.html"],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
const m = dom.match(/%%CPR%%([\s\S]*?)%%CPE%%/);
if (!m) { console.log("没抓到结果（脚本可能抛错）"); process.exit(1); }
const lines = m[1].split("\n").filter(Boolean);
lines.forEach(l => console.log(l));
const bad = lines.filter(l => l.startsWith("FAIL"));
console.log(`\n${lines.length - bad.length}/${lines.length} 项通过`);
process.exit(bad.length ? 1 : 0);
