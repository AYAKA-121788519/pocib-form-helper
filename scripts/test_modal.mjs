/* 弹窗防误关自测：
   1) 点遮罩不再关窗（以前手一滑就丢数据）
   2) 右上角 × 能关；没改动时直接关
   3) 有未保存修改时 × / 取消 / Esc 先确认，取消确认就留在窗口里
   4) 商品弹窗同样规则
   用法：node scripts/test_modal.mjs
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
const on=id=>document.getElementById(id).classList.contains("on");

(async()=>{
  try{
    const ok=window.__ok;
    /* --- 公司弹窗 --- */
    document.getElementById("newCo").click();
    await sleep(80);
    ok("新建公司弹窗打开", on("coMask"));
    const mask=document.getElementById("coMask");
    mask.dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));
    await sleep(60);
    ok("点遮罩不关窗", on("coMask"));

    /* 没改动 → × 直接关 */
    window.confirm=()=>{ window.__asked="co-nochange"; return true; };
    document.getElementById("coX").click();
    await sleep(60);
    ok("没改动时 × 直接关", !on("coMask"), "confirm 被调用? "+(window.__asked||"否"));

    /* 有改动 + 取消确认 → 不关 */
    document.getElementById("newCo").click();
    await sleep(80);
    const acc=document.querySelector('#coForm [data-k="account"]');
    acc.value="TEST-999"; acc.dispatchEvent(new Event("input",{bubbles:true}));
    window.confirm=()=>false;
    document.getElementById("coX").click();
    await sleep(60);
    ok("有改动时 × 先确认，拒绝则不关", on("coMask"));

    /* 有改动 + 同意 → 关 */
    window.confirm=()=>true;
    document.getElementById("coCancel").click();
    await sleep(60);
    ok("同意后才关", !on("coMask"));

    /* 有改动 + Esc + 拒绝 → 不关 */
    document.getElementById("newCo").click();
    await sleep(80);
    const acc2=document.querySelector('#coForm [data-k="account"]');
    acc2.value="TEST-888"; acc2.dispatchEvent(new Event("input",{bubbles:true}));
    window.confirm=()=>false;
    document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
    await sleep(60);
    ok("Esc 有关改动也先确认", on("coMask"));
    window.confirm=()=>true;
    document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
    await sleep(60);
    ok("Esc 同意后关闭", !on("coMask"));

    /* --- 商品弹窗 --- */
    document.getElementById("newGd").click();
    await sleep(80);
    ok("新建商品弹窗打开", on("gdMask"));
    document.getElementById("gdMask").dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));
    await sleep(60);
    ok("商品：点遮罩不关窗", on("gdMask"));
    window.confirm=()=>true;
    document.getElementById("gdX").click();
    await sleep(60);
    ok("商品：× 关闭", !on("gdMask"));

    /* 每个弹窗都有 × 且可点 */
    ok("公司/商品/识图 三个弹窗都有 × 按钮",
       ["coX","gdX","ocrX"].every(id=>!!document.getElementById(id)));
  }catch(e){
    window.__ok("脚本异常", false, e && e.message);
  }
  window.__done();
})();
</script>`;

fs.writeFileSync("build/_modal.html", html.replace(/<\/body>(?![\s\S]*<\/body>)/, probe + "</body>"), "utf8");
const dom = execFileSync("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  ["--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
   "--virtual-time-budget=20000", "--dump-dom", "file:///D:/pocib-helper/build/_modal.html"],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
const m = dom.match(/%%CPR%%([\s\S]*?)%%CPE%%/);
if (!m) { console.log("没抓到结果（脚本可能抛错）"); process.exit(1); }
const lines = m[1].split("\n").filter(Boolean);
lines.forEach(l => console.log(l));
const bad = lines.filter(l => l.startsWith("FAIL"));
console.log(`\n${lines.length - bad.length}/${lines.length} 项通过`);
process.exit(bad.length ? 1 : 0);
