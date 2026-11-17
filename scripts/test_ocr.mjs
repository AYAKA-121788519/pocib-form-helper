/* 截图识别公司：写入目标自测
   重点：不再默认覆盖已存公司；账号认不出来也能存成新公司；更新时账号不被改写 */
import fs from "fs";
import { execFileSync } from "child_process";
import path from "path";
import os from "os";

const root = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const htmlPath = path.join(root, "app", "index.html");
const html = fs.readFileSync(htmlPath, "utf8");

const test = `
<pre id="__R"></pre>
<script>
(function(){
 try{
  const R=[];
  const ok=(n,c,extra)=>R.push((c?"PASS":"FAIL")+" "+n+(c?"":"  :: "+extra));
  window.confirm=()=>true; window.alert=()=>{};
  localStorage.removeItem("pocib.companies.v1");
  CO_LIST=[{account:"A001",name_zh:"我方出口公司",name_en:"MY EXPORT CO",country:"China",country_zh:"中国",short_zh:"我方"},
           {account:"B002",name_zh:"对方进口公司",name_en:"CP IMPORT CO",country:"Germany",country_zh:"德国",short_zh:"对方"}];
  CASES[CASE].my="A001"; CASES[CASE].cp="B002";
  const mk=o=>({kind:"company",fields:Object.keys(o).map(k=>({key:k,value:o[k],conf:0.95}))});

  // 1 认到库里没有的公司 → 默认存为新公司
  useOcrData(mk({account:"C003",name_zh:"新客户公司",name_en:"NEW CLIENT LTD",country:"Brazil",country_zh:"巴西",short_zh:"新客户"}));
  ok("新公司默认存为新公司", $("ocrTarget").value==="new", $("ocrTarget").value);
  const keepTwo=JSON.stringify(CO_LIST.slice(0,2));
  applyOcr(false);
  ok("原有两家一字未动", JSON.stringify(CO_LIST.slice(0,2))===keepTwo);
  ok("新增一家 C003", CO_LIST.length===3 && (CO_LIST[2]||{}).account==="C003", CO_LIST.length+" / "+JSON.stringify(CO_LIST.map(x=>x.account)));
  ok("我方档案仍是 A001", CASES[CASE].my==="A001" && CO_LIST.some(x=>x.account==="A001"));

  // 2 认到库里已有的公司 → 默认更新那家，不多出一份
  useOcrData(mk({account:"C003",name_zh:"新客户公司",tel:"123456"}));
  ok("已有账号默认更新该档案", $("ocrTarget").value==="co:C003", $("ocrTarget").value);
  applyOcr(false);
  ok("更新后仍是一家（无重复）", CO_LIST.length===3 && CO_LIST.filter(x=>x.account==="C003").length===1);

  // 2b 账号撞上别家（国家不同）→ 默认新公司，原档案不动
  useOcrData(mk({account:"A001",name_zh:"德国汉莎贸易",name_en:"HANSA GMBH",country:"Germany",country_zh:"德国"}));
  ok("撞号但国家不同默认存新公司", $("ocrTarget").value==="new", $("ocrTarget").value);
  ok("提示写明不覆盖原档案", /不覆盖/.test($("ocrTargetHint").textContent), $("ocrTargetHint").textContent);
  const myBefore=JSON.stringify(CO_LIST.find(x=>x.account==="A001"));
  applyOcr(false);
  ok("原档案一字未动", JSON.stringify(CO_LIST.find(x=>x.account==="A001"))===myBefore);
  ok("撞号那家另存为 A001-2", CO_LIST.filter(x=>x.account==="A001-2").length===1, JSON.stringify(CO_LIST.map(x=>x.account)));

  // 3 认到我方 → 默认更新我方，账号不丢
  useOcrData(mk({account:"A001",name_zh:"我方出口公司",tel:"010-8888"}));
  ok("认到我方账号默认选我方", $("ocrTarget").value==="my", $("ocrTarget").value);
  applyOcr(false);
  const my=CO_LIST.find(x=>x.account==="A001")||{};
  ok("我方账号未被改写", my.account==="A001", my.account);
  ok("我方电话已更新", my.tel==="010-8888", my.tel);

  // 4 认到别家账号却手选「更新我方」：账号保持 A001，不整条改名消失
  useOcrData(mk({account:"D004",name_zh:"另一家公司",tel:"999"}));
  $("ocrTarget").value="my";
  applyOcr(false);
  ok("手选我方时账号仍是 A001", CO_LIST.some(x=>x.account==="A001"), JSON.stringify(CO_LIST.map(x=>x.account)));
  ok("手选我方时不会冒出 D004", !CO_LIST.some(x=>x.account==="D004"));
  ok("公司名按确认改写", (CO_LIST.find(x=>x.account==="A001")||{}).name_zh==="另一家公司");

  // 5 账号没识别到也能存新公司
  useOcrData(mk({name_zh:"无账号公司",name_en:"NO ACC LTD"}));
  ok("缺账号默认存新公司", $("ocrTarget").value==="new", $("ocrTarget").value);
  const n0=CO_LIST.length;
  applyOcr(false);
  ok("缺账号也存得下", CO_LIST.length===n0+1, CO_LIST.length+" vs "+n0);
  const last=CO_LIST[CO_LIST.length-1]||{};
  ok("给了占位档案号", /^未填账号-/.test(last.account||""), last.account);
  ok("占位档案号唯一", CO_LIST.filter(x=>x.account===last.account).length===1);

  // 6 再存一次同名无账号公司 → 占位号自动加序号，不互相覆盖
  useOcrData(mk({name_zh:"无账号公司",name_en:"NO ACC LTD"}));
  applyOcr(false);
  const ph=CO_LIST.filter(x=>/^未填账号-/.test(x.account||""));
  ok("同名占位号自动区分", ph.length===2 && ph[0].account!==ph[1].account, JSON.stringify(ph.map(x=>x.account)));

  // 7 商品识别仍走商品档案
  useOcrData({kind:"goods",fields:[{key:"code",value:"99001",conf:0.9},{key:"name_zh",value:"测试商品",conf:0.9}]});
  ok("商品默认填商品档案", $("ocrTarget").value==="goods" && $("ocrTarget").disabled===true, $("ocrTarget").value);
  applyOcr(false);
  ok("商品已写入", GD_LIST.some(x=>x.code==="99001"));

  document.getElementById("__R").textContent = ["@@@RE","SULT@@@"].join("")+R.join("\\n")+["@@@EN","D@@@"].join("");
 }catch(e){
  document.getElementById("__R").textContent = ["@@@RE","SULT@@@"].join("")+"FAIL 脚本抛错 :: "+(e&&e.message)+" @ "+((e&&e.stack||"").split("\\n")[1]||"")+["@@@EN","D@@@"].join("");
 }

})();
</script>
`;

// 语法自检：脚本块能否 new Function
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
let syntaxBad = 0;
blocks.forEach((b, i) => {
  try { new Function(b); } catch (e) { syntaxBad++; console.log(`✗ 第 ${i + 1} 个脚本块语法错误：${e.message}`); }
});
if (!syntaxBad) console.log("✓ 脚本块语法检查通过（" + blocks.length + " 块）");

const tmp = path.join(root, "build", "_ocr_test.html");
fs.mkdirSync(path.dirname(tmp), { recursive: true });
fs.writeFileSync(tmp, html.replace(/<\/body>(?![\s\S]*<\/body>)/, test + "</body>"), "utf8");

const exe = process.env.CHROME
  || ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
      "/usr/bin/google-chrome", "/usr/bin/chromium"].find(p => { try { return fs.existsSync(p); } catch (e) { return false; } });

if (!exe) {
  console.log("✗ 找不到 Chrome，跳过 DOM 测试（只跑了语法检查）");
  process.exit(syntaxBad ? 1 : 0);
}

const dom = execFileSync(exe, [
  "--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
  "--virtual-time-budget=4000", "--dump-dom", "file:///" + tmp.replace(/\\/g, "/"),
], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

const m = dom.match(/@@@RESULT@@@([\s\S]*?)@@@END@@@/);
if (!m) { console.log("✗ 测试脚本没跑起来（页面初始化可能报错）"); process.exit(1); }

const lines = m[1].trim().split(/\r?\n/).filter(Boolean);
let bad = 0;
lines.forEach(l => { if (l.startsWith("FAIL")) bad++; console.log(l.startsWith("FAIL") ? "✗ " + l.slice(5) : "✓ " + l.slice(5)); });
console.log(`\n${lines.length - bad}/${lines.length} 通过`);
fs.unlinkSync(tmp);
process.exit(bad || syntaxBad ? 1 : 0);
