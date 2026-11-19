/* 函电运费实时联动自测：
   1) 函电里换港口 → 单价按新航线自动换、柜数/运费即时重算（不点按钮）
   2) 运费算完自动写进预算对应方向（FOB → 进口运费，CIF → 出口运费）
   3) 主程序「实时同步」开关关掉后，主面板改动不再推给函电
   用法：node scripts/test_live_freight.mjs
*/
import fs from "fs";
import { execFileSync } from "child_process";

const html = fs.readFileSync("app/index.html", "utf8");

/* 注入脚本里所有标记都拆开写，免得住 dom 里被自己的正则命中 */
const probe = `
<script>
window.__out=[];
window.__ok=(n,cond,extra)=>window.__out.push((cond?"PASS ":"FAIL ")+n+(extra!==undefined?" :: "+extra:""));
window.__done=()=>{
  if(document.getElementById("OUT")) return;
  const pre=document.createElement("pre"); pre.id="OUT";
  pre.textContent=["%%LS","R%%"].join("")+window.__out.join("\\n")+["%%LS","E%%"].join("");
  document.body.appendChild(pre);
};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const until=async(fn,ms=4000)=>{ const t0=Date.now(); while(Date.now()-t0<ms){ try{ const v=fn(); if(v) return v; }catch(e){} await sleep(100);} return null; };

(async()=>{
  try{
    const ok=window.__ok;
    document.querySelector('.mode[data-mode="letter"]').click();
    const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("foFinal") ? x : null; }, 8000);
    if(!f){ ok("函电模块加载", false); window.__done(); return; }
    await sleep(900);                                  // 等首次同步落地
    const d=f.contentDocument;
    const v=id=>{ const e=d.getElementById(id); return e? String(e.value).trim() : "(无)"; };
    const val=id=>parseFloat(v(id))||0;
    const finalTxt=()=>d.getElementById("foFinal").textContent;
    const money=s=>{ const m=String(s).match(/USD\\s*([\\d,]+\\.?\\d*)/); return m? parseFloat(m[1].replace(/,/g,"")) : NaN; };

    ok("函电结果区一开始就可见", d.getElementById("fResult").style.display!=="none", d.getElementById("fResult").style.display||"(空)");
    ok("没有「计算商品运费」按钮", !/计算商品运费/.test(d.body.innerHTML));
    ok("没有「一键填入运费」按钮", !/onclick="autoFreight\(\)"/.test(d.body.innerHTML));

    const r20a=val("r20"), fA=money(finalTxt());
    const buyerPay=["FOB","FCA","FAS"].includes(d.getElementById("bMode").value);
    const frtId=buyerPay?"bImFreight":"bExFreight";
    ok("初始单价有值（20普）", r20a>0, v("r20"));
    ok("初始运费已算好（不用点按钮）", fA>0, finalTxt());
    ok("初始运费自动写进预算（"+d.getElementById("bMode").value+" → "+frtId+"）", Math.abs(val(frtId)-fA)<0.02, v(frtId)+" vs "+fA);

    /* 换卸货港 → 运价与运费必须跟着变 */
    const pd=d.getElementById("portDisc");
    const loadName=d.getElementById("portLoad").value;
    ok("装运港已由主程序带入", !!loadName, loadName);
    /* 港口按公司所在国定：案例 A 是德国出口商 → 美国进口商，装运港汉堡、目的港纽约 */
    ok("装运港=出口公司所在国（德国 Hamburg）", /汉堡|Hamburg/.test(loadName), loadName);
    ok("目的港=进口公司所在国（美国 New York）", /纽约|New York/.test(pd.value), pd.value);
    pd.value="南非 Cape Town"; pd.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(300);
    const r20b=val("r20"), fB=money(finalTxt());
    ok("换卸货港后单价跟着换", r20b>0 && r20b!==r20a, v("r20")+" ← 原 "+r20a);
    ok("换卸货港后运费即时重算", fB>0, finalTxt());
    ok("预算运费跟着变", Math.abs(val(frtId)-fB)<0.02, v(frtId)+" vs "+fB);
    const rh=d.getElementById("rateHint").textContent;
    ok("航线提示写清新航线", /Hamburg/.test(rh) && /Capetown/i.test(rh), rh);

    /* 换装运港 → 也应该变 */
    const pl=d.getElementById("portLoad");
    const before=val("r20");
    pl.value="中国 Shanghai"; pl.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(250);
    const after=val("r20");
    ok("换装运港后单价跟着换", after>0 && after!==before, v("r20")+" ← 原 "+before);
    ok("单价提示说明已自动填入", /运价表/.test(d.getElementById("rateHint").textContent), d.getElementById("rateHint").textContent);

    /* 起止港相同 → 没有航线，给提示 */
    pl.value="美国 New York"; pl.dispatchEvent(new Event("change",{bubbles:true}));
    pd.value="美国 New York"; pd.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(250);
    ok("同港提示没有航线", /相同/.test(d.getElementById("rateHint").textContent), d.getElementById("rateHint").textContent);

    /* 切空运：分组切换、空运费率带出、运费重算、交易条件同步 */
    pl.value="中国 Shanghai"; pl.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(200);
    const sm=d.getElementById("fShipMode");
    sm.value="air"; sm.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(300);
    ok("切空运后交易条件同步为空运", d.getElementById("ship").value==="空运", d.getElementById("ship").value);
    ok("切空运后空运费率有值", val("ra300p")>0, v("ra300p"));
    ok("切空运后运费重算", money(finalTxt())>0, finalTxt());

    /* 改毛重 → 即时重算 */
    const f1=money(finalTxt());
    const wt=d.getElementById("fWt"); wt.value="60"; wt.dispatchEvent(new Event("input",{bubbles:true}));
    await sleep(350);
    ok("改单件毛重后运费即时变", money(finalTxt())!==f1, finalTxt()+" ← 原 "+f1);

    /* 海运 + 冻柜 */
    sm.value="sea"; sm.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(300);
    const bk=d.getElementById("fBoxType"); bk.value="rf"; bk.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(250);
    ok("切冻柜后重算", money(finalTxt())>0, finalTxt());
    ok("冻柜分组显示", d.getElementById("grpRF").style.display!=="none", d.getElementById("grpRF").style.display);

    /* 运费按术语方向：FOB → 进口运费 */
    const bm=d.getElementById("bMode"); bm.value="FOB"; bm.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(350);
    const ff=money(finalTxt());
    ok("FOB 时运费写进进口运费", Math.abs(val("bImFreight")-ff)<0.02, v("bImFreight")+" vs "+ff);

    /* 主程序：实时同步开关 */
    const chk=document.getElementById("liveSyncChk");
    ok("默认开着实时同步", chk.checked===true);
    ok("开着时不显示「同步一次」", document.getElementById("bridgeBtn").style.display==="none", document.getElementById("bridgeBtn").style.display);

    chk.checked=false; chk.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(120);
    ok("关掉后出现「同步一次」", document.getElementById("bridgeBtn").style.display!=="none");
    const oldQty=v("qty");
    CASES[CASE].qty=12345;
    document.getElementById("qty").value="12345";
    compute();
    await sleep(800);
    ok("关掉后主面板改动不推给函电", v("qty")===oldQty, v("qty"));

    chk.checked=true; chk.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(1000);
    ok("打开后立刻把当前数据推进函电", v("qty")==="12345", v("qty"));

    /* 函电改港口 → 回传主程序（实时同步开着） */
    const pd2=d.getElementById("portDisc");
    pd2.value="美国 New York"; pd2.dispatchEvent(new Event("change",{bubbles:true}));
    await sleep(1200);
    ok("函电换卸货港回传主程序", String(CASES[CASE].port_dest).includes("NEW YORK"), CASES[CASE].port_dest);
    ok("主程序运费跟着重算", +document.getElementById("freight").value>0, document.getElementById("freight").value);
  }catch(e){
    window.__ok("脚本异常", false, e && e.message);
  }
  window.__done();
})();
</script>`;

fs.writeFileSync("build/_live.html", html.replace(/<\/body>(?![\s\S]*<\/body>)/, probe + "</body>"), "utf8");
const dom = execFileSync("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
   "--virtual-time-budget=20000", "--dump-dom", "file:///D:/pocib-helper/build/_live.html"],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
const m = dom.match(/%%LSR%%([\s\S]*?)%%LSE%%/);
if (!m) { console.log("没抓到结果（脚本可能抛错）"); process.exit(1); }
const lines = m[1].split("\n").filter(Boolean);
lines.forEach(l => console.log(l));
const bad = lines.filter(l => l.startsWith("FAIL"));
console.log(`\n${lines.length - bad.length}/${lines.length} 项通过`);
process.exit(bad.length ? 1 : 0);
