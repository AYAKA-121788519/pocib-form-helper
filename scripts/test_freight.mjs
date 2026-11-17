/* 预计运费自测：运价表是否与 POCIB 一致 + 海运整箱/拼箱、空运重量档与最低运费
   数据来自 scripts/crawl_freight.py 抓的 90 条海运 + 90 条空运航线 */
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
  const near=(a,b)=>Math.abs(a-b)<0.01;
  const put=(id,v)=>{ document.getElementById(id).value=v; };
  const cargo=(qty,gw,nw,vol,unit,pack)=>{
    put("qty",qty); put("gw",gw); put("nw",nw); put("vol",vol); put("pack_qty",1);
    CASES.A.unit=unit||"CARTON"; CASES.A.pack_unit=pack||"CARTON";
  };
  const setCase=(load,dest,air,reefer)=>{
    CASE="A";
    CASES.A.port_load=load; CASES.A.port_dest=dest;
    CASES.A.transport=air?"空运":"海运"; CASES.A.reefer=!!reefer;
  };

  // 1 运价表规模与抽查（对照 POCIB 百科《如何计算运费》例题）
  ok("海运 90 条航线", Object.keys(FREIGHT.sea).length===90, Object.keys(FREIGHT.sea).length);
  ok("空运 90 条航线", Object.keys(FREIGHT.air).length===90, Object.keys(FREIGHT.air).length);
  const sh=FREIGHT.sea["shanghai-hamburg"], ny=FREIGHT.sea["shanghai-new york"],
        ml=FREIGHT.sea["shanghai-melbourne"], lv=FREIGHT.air["shanghai-liverpool"],
        ng=FREIGHT.air["shanghai-nagoya"];
  ok("上海→汉堡 20'=2140", sh && sh.dry[0]===2140, sh&&sh.dry[0]);
  ok("上海→纽约 20'/40'=5600/7071", ny && ny.dry[0]===5600 && ny.dry[1]===7071, ny&&ny.dry);
  ok("上海→墨尔本 拼箱 139/153", ml && ml.dry[3]===139 && ml.dry[4]===153, ml&&ml.dry);
  ok("上海→利物浦 空运 100KG=37.3", lv && lv.t[3]===37.3, lv&&lv.t[3]);
  ok("上海→名古屋 Normal/Min=33.3/459.3", ng && ng.t[1]===33.3 && ng.t[0]===459.3, ng&&ng.t);

  // 2 海运整箱：按柜型组合 × 单价
  setCase("SHANGHAI, CHINA","HAMBURG, GERMANY",false,false);
  cargo(1000,22,20,0.02);                       // 20 CBM / 22 t → 1×20'普柜
  let q=quoteFreight();
  ok("上海→汉堡 1×20GP = 2140", near(q.usd,2140), q.usd+" / "+(q.hint||q.err));

  setCase("SHANGHAI, CHINA","NEW YORK, AMERICA",false,false);
  cargo(1000,22,20,0.06);                       // 60 CBM / 22 t → 1×40'普柜
  q=quoteFreight();
  ok("上海→纽约 1×40GP = 7071", near(q.usd,7071), q.usd+" / "+(q.hint||q.err));

  // 3 海运拼箱：体积与重量取大
  setCase("SHANGHAI, CHINA","HAMBURG, GERMANY",false,false);
  cargo(250,7,6.5,0.02);                        // 5 CBM / 1.75 t → 拼箱
  q=quoteFreight();
  ok("拼箱按体积大者 = 137×5", near(q.usd,685), q.usd+" / "+(q.hint||q.err));

  // 4 冷柜走 rf 价
  setCase("SHANGHAI, CHINA","HAMBURG, GERMANY",false,true);
  cargo(1000,18,17,0.02);                       // 20 CBM / 18 t → 1×20'冻柜（限重 21 t）
  q=quoteFreight();
  ok("冻柜 20'=2311", near(q.usd,2311), q.usd+" / "+(q.hint||q.err));
  cargo(1000,22,20,0.02);                       // 22 t 超 20'冻柜限重 → 40'冻柜
  q=quoteFreight();
  ok("冻柜超 21t 换 40'=4421", near(q.usd,4421), q.usd+" / "+(q.hint||q.err));

  // 5 空运：计费重量取 MAX(毛重, 体积×167)，按档计价并守住最低运费
  setCase("SHANGHAI, CHINA","LIVERPOOL, UK",true,false);
  cargo(100,1.5,1.4,0.0038);                    // 150 KG / 0.38 CBM → 100-300 档 37.3
  q=quoteFreight();
  ok("空运 150KG = 37.3×150 = 5595", near(q.usd,5595), q.usd+" / "+(q.hint||q.err));

  setCase("SHANGHAI, CHINA","NAGOYA, JAPAN",true,false);
  cargo(100,0.3,0.28,0.00144);                  // 30 KG → Normal 33.3
  q=quoteFreight();
  ok("空运 30KG 按 Normal = 999", near(q.usd,999), q.usd+" / "+(q.hint||q.err));

  cargo(10,0.5,0.45,0.001);                     // 5 KG → 166.5，低于最低 459.3
  q=quoteFreight();
  ok("低于最低运费按 Minimum 收", near(q.usd,459.3), q.usd+" / "+(q.hint||q.err));

  // 6 体积重反超毛重时按体积重计
  setCase("SHANGHAI, CHINA","NAGOYA, JAPAN",true,false);
  cargo(100,0.3,0.28,0.01);                     // 30 KG vs 1.0×167=167 KG → 按 167 落 100-300 档
  q=quoteFreight();
  ok("泡货按体积重 167KG 计", near(q.usd,167*14.9), q.usd+" / "+(q.hint||q.err));

  // 7 未知航线给提示，不硬算
  setCase("OSAKA, JAPAN","HAMBURG, GERMANY",false,false);
  cargo(100,22,20,0.02);
  q=quoteFreight();
  ok("自定义港提示查不到运价", !!q.err, JSON.stringify(q));

  // 8 推进函电运费卡：档位映射要对得上
  setCase("SHANGHAI, CHINA","LIVERPOOL, UK",true,false);
  const got={}; const set=(id,v)=>{ got[id]=v; };
  pushFreightRates(set, CASES.A);
  ok("函电：空运档位映射", got.fShipMode==="air" && got.ra45===70.1 && got.ra100===46.6
     && got.ra300===37.3 && got.ra300p===37.3 && got.rMin===745.4, JSON.stringify(got));

  setCase("SHANGHAI, CHINA","HAMBURG, GERMANY",false,true);
  const g2={}; pushFreightRates((id,v)=>{g2[id]=v;}, CASES.A);
  ok("函电：海运费率 20'/40'/40'高 + 拼箱", g2.r20===2140 && g2.r40===4093 && g2.r40h===4280
     && g2.rLCLv===137 && g2.rLCLw===172, JSON.stringify(g2));
  ok("函电：冻柜价一起推进", g2.rr20===2311 && g2.rr40===4421 && g2.rr40h===4622, JSON.stringify(g2));
  ok("函电：跟着冷藏勾选切冻柜", g2.fBoxType==="rf", g2.fBoxType);

  document.getElementById("__R").textContent =
    ["@@@RE","SULT@@@"].join("")+R.join("\\n")+["@@@EN","D@@@"].join("");
 }catch(e){
  document.getElementById("__R").textContent =
    ["@@@RE","SULT@@@"].join("")+"FAIL 脚本抛错 :: "+(e&&e.message)+" @ "+((e&&e.stack||"").split("\\n")[1]||"")+["@@@EN","D@@@"].join("");
 }
})();
</script>`;

let syntaxBad = 0;
[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m, i) => {
  try { new Function(m[1]); } catch (e) { syntaxBad++; console.log(`✗ 第 ${i + 1} 个脚本块语法错误：${e.message}`); }
});
if (!syntaxBad) console.log("✓ 脚本块语法检查通过");

const tmp = path.join(root, "build", "_freight_test.html");
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
