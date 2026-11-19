/* 公司 ↔ 港口联动自测：
   1) 选公司 → 按该公司所在国重选装运港（出口方）/ 目的港（进口方）
   2) 打开函电 → 港口按交易与公司国别落地，不再是模板里写死的南非
   3) 函电预算的进出口国跟着港口走（汇率、工厂价、报关费都按这个国别取）
   4) 在函电里手改港口 → 回传主程序，且后续同步不把它拉回去
   用法：node scripts/test_co_ports.mjs
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
  pre.textContent=["%%CP","R%%"].join("")+window.__out.join("\\n")+["%%CP","E%%"].join("");
  document.body.appendChild(pre);
};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const until=async(fn,ms=6000)=>{ const t0=Date.now(); while(Date.now()-t0<ms){ try{ const v=fn(); if(v) return v; }catch(e){} await sleep(100);} return null; };

(async()=>{
  try{
    const ok=window.__ok;
    ok("默认案例出口方在德国（港口汉堡）", CASES.A.port_load.indexOf("HAMBURG")===0, CASES.A.port_load);

    /* 塞一个南非公司，模拟导入的数据 */
    CO_LIST.push({account:"TEST-ZA", short_zh:"南非测试", name_zh:"南非测试", name_en:"ZA CO",
      country:"South Africa", country_zh:"南非", acct:{USD:"1"}});
    renderCoUI();
    const my=document.getElementById("myCo");
    my.value="TEST-ZA"; my.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(500);
    ok("换我方（南非公司）→ 装运港改开普敦", CASES.A.port_load.indexOf("CAPETOWN")===0, CASES.A.port_load);
    ok("目的港跟着进口方（美国）", CASES.A.port_dest.indexOf("NEW YORK")===0, CASES.A.port_dest);
    ok("港口下拉显示的也是开普敦", /开普敦/.test(document.getElementById("port_load").selectedOptions[0].textContent),
       document.getElementById("port_load").selectedOptions[0].textContent);

    /* 换对方公司（也换成南非）→ 目的港应变开普敦 */
    const cp=document.getElementById("cpCo");
    cp.value="TEST-ZA"; cp.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(400);
    ok("换对方公司 → 目的港跟着改", CASES.A.port_dest.indexOf("CAPETOWN")===0, CASES.A.port_dest);
    /* 对方还原成美国公司（我方仍是南非） */
    cp.value="202405110145"; cp.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(300);

    /* 打开函电：港口与预算国别 */
    document.querySelector('.mode[data-mode="letter"]').click();
    const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("foFinal") ? x : null; }, 9000);
    if(!f){ ok("函电模块加载", false); window.__done(); return; }
    await sleep(1200);
    const d=f.contentDocument;
    const v=id=>{ const e=d.getElementById(id); return e? String(e.value).trim() : "(无)"; };

    ok("函电装运港 = 出口公司所在国（南非）", /南非|Capetown/i.test(v("portLoad")), v("portLoad"));
    ok("函电卸货港 = 进口公司所在国（美国）", /美国|New York/i.test(v("portDisc")), v("portDisc"));
    ok("函电预算出口国 = 南非", v("bExCountry")==="南非", v("bExCountry"));
    ok("函电预算进口国 = 美国", v("bImCountry")==="美国", v("bImCountry"));
    ok("运价按开普敦航线带出", +v("r20")>0, v("r20"));
    ok("港口提示说明按公司国别", /公司所在国/.test(d.getElementById("portHint").textContent), d.getElementById("portHint").textContent.slice(0,60));

    /* 手改卸货港 → 回传主程序；后续同步不能拉回 */
    const pd=d.getElementById("portDisc");
    pd.value="日本 Nagoya"; pd.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(900);
    ok("手改卸货港回传主程序", CASES.A.port_dest.indexOf("NAGOYA")===0, CASES.A.port_dest);
    const chk=document.getElementById("liveSyncChk");
    const wasOn=!!(chk && chk.checked);
    if(chk){ chk.checked=true; chk.dispatchEvent(new Event("change",{bubbles:true})); }
    await sleep(1600);
    ok("实时同步后不把手改的港口拉回去", /日本|Nagoya/i.test(v("portDisc")), v("portDisc"));

    /* 再换我方公司（回德国）→ 港口仍按公司走 */
    const my2=document.getElementById("myCo");
    my2.value="202405110116"; my2.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(1200);
    ok("再换公司 → 主面板装运港回汉堡", CASES.A.port_load.indexOf("HAMBURG")===0, CASES.A.port_load);
    ok("再换公司 → 函电装运港跟着回汉堡", /德国|Hamburg/i.test(v("portLoad")), v("portLoad"));
    if(chk && !wasOn){ chk.checked=false; chk.dispatchEvent(new Event("change",{bubbles:true})); }
  }catch(e){
    window.__ok("脚本异常", false, e && e.message);
  }
  window.__done();
})();
</script>`;

fs.writeFileSync("build/_co_ports.html", html.replace(/<\/body>(?![\s\S]*<\/body>)/, probe + "</body>"), "utf8");
const dom = execFileSync("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
   "--virtual-time-budget=30000", "--dump-dom", "file:///D:/pocib-helper/build/_co_ports.html"],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
const m = dom.match(/%%CPR%%([\s\S]*?)%%CPE%%/);
if (!m) { console.log("没抓到结果（脚本可能抛错）"); process.exit(1); }
const lines = m[1].split("\n").filter(Boolean);
lines.forEach(l => console.log(l));
const bad = lines.filter(l => l.startsWith("FAIL"));
console.log(`\n${lines.length - bad.length}/${lines.length} 项通过`);
process.exit(bad.length ? 1 : 0);
