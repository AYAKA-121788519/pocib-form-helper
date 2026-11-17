/* 检验检疫申请单上的港口显示自测
   规格：出境「启运地 / 到达口岸」填中文港名（如 汉堡 / 墨尔本），入境单的启运口岸、入境口岸同理 */
import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";

const root = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const html = fs.readFileSync(path.join(root, "app", "index.html"), "utf8");

const test = `
<pre id="__R"></pre>
<script>
(function(){
 const R=[];
 try{
  const ok=(n,c,extra)=>R.push((c?"PASS":"FAIL")+" "+n+(c?"":"  :: "+extra));
  const rowOf=(rows,label)=>rows.find(x=>x[0]===label)||[];
  const docs=(doc,id)=>{
    CASE=id; const c=CASES[id];
    return genericRows(doc,c,derived(),CO(c.my),CO(c.cp));
  };
  const setPorts=(id,load,dest)=>{ CASES[id].port_load=load; CASES[id].port_dest=dest; };

  setPorts("A","HAMBURG, GERMANY","NEW YORK, AMERICA");
  let r=docs("出境货物检验检疫申请","A");
  ok("出境·启运地写中文港名", rowOf(r,"启运地")[1]==="汉堡", rowOf(r,"启运地")[1]);
  ok("出境·到达口岸写中文港名", rowOf(r,"到达口岸")[1]==="纽约", rowOf(r,"到达口岸")[1]);
  ok("认得出的港标「自动」", rowOf(r,"启运地")[2]==="自动", rowOf(r,"启运地")[2]);

  setPorts("B","NEW YORK, AMERICA","MELBOURNE, AUSTRALIA");
  r=docs("出境货物检验检疫申请","B");
  const two=rowOf(r,"启运地")[1]+"/"+rowOf(r,"到达口岸")[1];
  ok("反向也换中文（纽约→墨尔本）", two==="纽约/墨尔本", two);
  ok("墨尔本命中码表", rowOf(r,"到达口岸")[1]==="墨尔本", rowOf(r,"到达口岸")[1]);

  setPorts("A","SHANGHAI, CHINA","MELBOURNE, AUSTRALIA");
  r=docs("出境货物检验检疫申请","A");
  ok("上海出口·到达墨尔本", [rowOf(r,"启运地")[1],rowOf(r,"到达口岸")[1]].join(",")==="上海,墨尔本",
     rowOf(r,"启运地")[1]+","+rowOf(r,"到达口岸")[1]);

  // 自定义港：不认识的港原样给出并标「待确认」，提醒手动换成中文
  setPorts("A","OSAKA, JAPAN","MELBOURNE, AUSTRALIA");
  r=docs("出境货物检验检疫申请","A");
  ok("自定义港原样保留", rowOf(r,"启运地")[1]==="OSAKA, JAPAN", rowOf(r,"启运地")[1]);
  ok("自定义港标「待确认」", rowOf(r,"启运地")[2]==="待确认", rowOf(r,"启运地")[2]);

  // 入境单同样用中文港名
  setPorts("B","SHANGHAI, CHINA","HAMBURG, GERMANY");
  r=docs("入境货物检验检疫申请","B");
  ok("入境·启运口岸中文", rowOf(r,"启运口岸")[1]==="上海", rowOf(r,"启运口岸")[1]);
  ok("入境·入境口岸中文", rowOf(r,"入境口岸")[1]==="汉堡", rowOf(r,"入境口岸")[1]);
  ok("入境·目的地中文", rowOf(r,"目的地")[1]==="汉堡", rowOf(r,"目的地")[1]);

  document.getElementById("__R").textContent = ["@@@RE","SULT@@@"].join("")+R.join("\\n")+["@@@EN","D@@@"].join("");
 }catch(e){
  document.getElementById("__R").textContent = ["@@@RE","SULT@@@"].join("")+"FAIL 脚本抛错 :: "+(e&&e.message)+["@@@EN","D@@@"].join("");
 }
})();
</script>`;

// 语法自检
let syntaxBad = 0;
[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m, i) => {
  try { new Function(m[1]); } catch (e) { syntaxBad++; console.log(`✗ 第 ${i + 1} 个脚本块语法错误：${e.message}`); }
});
if (!syntaxBad) console.log("✓ 脚本块语法检查通过");

const tmp = path.join(root, "build", "_docs_test.html");
fs.mkdirSync(path.dirname(tmp), { recursive: true });
fs.writeFileSync(tmp, html.replace(/<\/body>(?![\s\S]*<\/body>)/, test + "</body>"), "utf8");

const exe = process.env.CHROME || ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium"].find(p => { try { return fs.existsSync(p); } catch (e) { return false; } });
if (!exe) { console.log("✗ 找不到 Chrome，跳过"); process.exit(syntaxBad ? 1 : 0); }

const dom = execFileSync(exe, ["--headless=new", "--disable-gpu", "--no-sandbox",
  "--allow-file-access-from-files", "--virtual-time-budget=4000", "--dump-dom",
  "file:///" + tmp.replace(/\\/g, "/")], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

const m = dom.match(/@@@RESULT@@@([\s\S]*?)@@@END@@@/);
if (!m) { console.log("✗ 测试脚本没跑起来"); process.exit(1); }
const lines = m[1].trim().split(/\r?\n/).filter(Boolean);
let bad = 0;
lines.forEach(l => { if (l.startsWith("FAIL")) bad++; console.log(l.startsWith("FAIL") ? "✗ " + l.slice(5) : "✓ " + l.slice(5)); });
console.log(`\n${lines.length - bad}/${lines.length} 通过`);
fs.unlinkSync(tmp);
process.exit(bad || syntaxBad ? 1 : 0);
