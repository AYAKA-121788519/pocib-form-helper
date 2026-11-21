/* 函电预算「工厂价格」自测：按商品档案的出口国出厂价自动带一次
   1) 德国 + 26006（德国咖啡机）→ 40.00 EUR
   2) 带出来之后手改的数，主面板再同步也不覆盖
   3) 换商品编号 → 按新商品的出厂价重带
   4) 出口国是中国时，价目表里存成 RMB，要能对上（别名）
   5) 价目表里没有这个商品 → 不动用户的值，标题里提示手填
   6) 主程序暴露的 LETTERS_FACTORY_PRICE 直接用也能查
   用法：node scripts/test_factory.mjs
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
    document.querySelector('.mode[data-mode="letter"]').click();
    const f=await until(()=>{ const x=document.getElementById("lettersFrame"); return x && x.contentDocument && x.contentDocument.getElementById("bFactory") ? x : null; });
    if(!f){ ok("函电模块加载", false); window.__done(); return; }
    await sleep(1500);
    const d=f.contentDocument, W=f.contentWindow;
    const V=id=>String(d.getElementById(id).value);

    /* 0) 输入框不该再带写死的示例价 */
    ok("工厂价输入框没有写死的示例值", d.getElementById("bFactory").getAttribute("value")===null,
       d.getElementById("bFactory").getAttribute("value"));

    /* 6) 主程序 API：直接按出口国查 */
    CASES[CASE].goods_no="26006";
    const r1=LETTERS_FACTORY_PRICE("德国");
    ok("API 德国+26006 = 40.00 EUR", r1 && r1.price===40 && r1.cur==="EUR", JSON.stringify(r1));
    ok("API 中国走 RMB 别名", (()=>{ CASES[CASE].goods_no="01001"; const r=LETTERS_FACTORY_PRICE("中国");
        return r && r.price===44 && r.code==="01001"; })(), JSON.stringify(LETTERS_FACTORY_PRICE("中国")));
    /* 编号和品名都对不上 → null（先把品名临时清掉，免得按品名兜到别的编号上） */
    const zh0=CASES[CASE].hs_zh, gd0=CASES[CASE].goods;
    CASES[CASE].goods_no="99999"; CASES[CASE].hs_zh=""; CASES[CASE].goods="NO SUCH GOODS";
    ok("API 价目表没这个商品返回 null", LETTERS_FACTORY_PRICE("德国")===null, String(LETTERS_FACTORY_PRICE("德国")));
    /* 没编号但品名能对上（中国咖啡机 → 26006）→ 按品名兜 */
    CASES[CASE].goods_no=""; CASES[CASE].hs_zh="德国咖啡机";
    const rn=LETTERS_FACTORY_PRICE("德国");
    ok("没编号时按中文品名兜一次", rn && rn.price===40 && rn.code==="26006", JSON.stringify(rn));
    CASES[CASE].hs_zh=zh0; CASES[CASE].goods=gd0;

    /* 1) 德国 + 26006 → 自动带 40 */
    CASES[CASE].goods_no="26006";
    d.getElementById("bExCountry").value="德国";
    W.syncBudget();
    ok("换到德国 → 工厂价带出 40", +V("bFactory")===40, V("bFactory"));
    ok("标题说明来源", /自动带出/.test(d.getElementById("bFactory").title), d.getElementById("bFactory").title);

    /* 2) 手改之后不再被覆盖 */
    setv(d,"bFactory","33.3");
    W.syncBudget();
    await sleep(200);
    ok("手改 33.3 后 syncBudget 不覆盖", +V("bFactory")===33.3, V("bFactory"));
    /* 主面板连推两次也不动 */
    bridgeToLetters(true); bridgeToLetters(true);
    await sleep(400);
    ok("主面板同步两次仍保留手改值", +V("bFactory")===33.3, V("bFactory"));

    /* 3) 换商品 → 重带（德国 01005 玉米笋罐头 4.8） */
    CASES[CASE].goods_no="01005";
    W.autoFactoryPrice();
    ok("换商品 01005 → 重带 4.8", +V("bFactory")===4.8, V("bFactory"));

    /* 4) 中国（价目表存成 RMB）+ 01001 洋菇罐头 44 */
    CASES[CASE].goods_no="01001";
    d.getElementById("bExCountry").value="中国";
    W.syncBudget();
    ok("换到中国 → 44（RMB 别名生效）", +V("bFactory")===44, V("bFactory"));

    /* 5) 没这个商品 → 值不动，标题提示 */
    CASES[CASE].goods_no="99999";
    W.autoFactoryPrice();
    ok("价目表没有的商品不清空用户值", +V("bFactory")===44, V("bFactory"));
    ok("没查到时标题提示手填", /手填/.test(d.getElementById("bFactory").title), d.getElementById("bFactory").title);
  }catch(e){
    window.__ok("脚本异常", false, e && e.message);
  }
  window.__done();
})();
</script>`;

fs.writeFileSync("build/_factory.html", html.replace("</body>", probe + "</body>"), "utf8");
const dom = execFileSync("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
   "--virtual-time-budget=40000", "--dump-dom", "file:///D:/pocib-helper/build/_factory.html"],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
const m = dom.match(/%%CPR%%([\s\S]*?)%%CPE%%/);
if (!m) { console.log("没抓到结果（脚本可能抛错）"); process.exit(1); }
const lines = m[1].split("\n").filter(Boolean);
lines.forEach(l => console.log(l));
const bad = lines.filter(l => l.startsWith("FAIL"));
console.log(`\n${lines.length - bad.length}/${lines.length} 项通过`);
process.exit(bad.length ? 1 : 0);
