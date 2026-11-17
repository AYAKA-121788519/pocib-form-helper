/* 海关税率库自测：内嵌数据完整性、编码/品名查询、进口税额计算、缴款书字段联动
   数据来源：POCIB「税率查询 - 海关 CUSTOMS」（scripts/crawl_tariff.py） */
import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";

const root = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const html = fs.readFileSync(path.join(root, "app", "index.html"), "utf8");
const src = JSON.parse(fs.readFileSync(path.join(root, "data", "tariff.json"), "utf8"));

const test = `
<pre id="__R"></pre>
<script>
(function(){
 const R=[];
 try{
  const ok=(n,c,extra)=>R.push((c?"PASS":"FAIL")+" "+n+(c?"":"  :: "+extra));
  const near=(a,b)=>Math.abs(a-b)<0.02;

  ok("税则库已内嵌（>3000 条）", TARIFF.length>3000, TARIFF.length);
  ok("数据源条数一致（"+__COUNT__+"）", TARIFF.length===__COUNT__, TARIFF.length);

  // 1 编码查询：10 位报关编码退 8 位税则编码
  let r=tariffRow(tariffOf("2005800000"));
  ok("10 位编码退到 8 位税则码", r && r.hs==="20058000", r && r.hs);
  ok("甜玉米进口优惠税率 5%", r && r.imPref===5, r && r.imPref);
  ok("甜玉米增值税 13%", r && r.vat===13, r && r.vat);
  ok("甜玉米非应税消费品", tariffExcise("2005800000")===false, tariffExcise("2005800000"));
  ok("编码不认得的返回 null", tariffOf("9999999999")===null || tariffOf("9999999999")[0].slice(0,2)==="99",
     JSON.stringify(tariffOf("9999999999")));

  // 2 品名查询
  const byName=tariffSearch("甜玉米");
  ok("品名查得到甜玉米", byName.length>0, byName.length);
  ok("品名查询结果含编码", byName[0] && /^\\d{8}$/.test(byName[0][0]), byName[0] && byName[0][0]);

  // 3 前缀查询：填 20 列出第 20 章
  const byPre=tariffSearch("20",1000);
  ok("前缀 20 命中整章（>50 条）", byPre.length>50, byPre.length);
  ok("前缀结果都以 20 开头", byPre.every(x=>x[0].indexOf("20")===0), "有越界");

  // 4 进口税额：案例 B 是进口，把商品换成甜玉米试算
  CASE="B"; const b=CASES.B;
  const hsBak=b.hs, zhBak=b.hs_zh, qBak=b.qty, uBak=b.unit, gBak=b.goods_no;
  b.hs="2005800000"; b.hs_zh="非用醋制作的未冷冻甜玉米"; b.qty=1000; b.unit="千克";
  $("hs").value=b.hs; $("qty").value=1000; $("unit").value="千克";
  $("tfFx").value="6.80";
  const D=derived(), t=importTax(b,D,6.8);
  ok("算得出进口税", !!t, "null");
  ok("完税价格 = CIF × 6.80", t && near(t.cif, D.cif*6.8), t && t.cif);
  ok("关税 = 完税价 × 5%", t && near(t.duty, t.cif*0.05), t && t.duty);
  ok("无消费税", t && near(t.excise,0), t && t.excise);
  ok("增值税 =（完税价+关税）×13%", t && near(t.vat,(t.cif+t.duty)*0.13), t && t.vat);

  // 5 应税消费品：挑一条有消费税的税则，验证三张缴款书
  const csRow=TARIFF.find(x=>x[7]>0 && x[7]<100);
  ok("税则里有从价消费税的品目", !!csRow, "没有");
  if(csRow){
    const csHs=csRow[0];
    ok("应税消费品判定为真", tariffExcise(csHs)===true, csHs);
    b.hs=csHs; b.hs_zh=csRow[1]; $("hs").value=csHs;
    const D2=derived(), t2=importTax(b,D2,6.8);
    ok("从价消费税按组成计税价格算", t2 && near(t2.excise,(t2.cif+t2.duty)*csRow[7]/100/(1-csRow[7]/100)),
       t2 && t2.excise);
    const step20=docsOf(FLOW.find(f=>f.s===20));
    ok("缴税环节多出消费税缴款书", step20.d.indexOf("海关进口消费税专用缴款书")>=0, step20.d.join("/"));
  }

  // 6 缴款书字段：点开第 20 步，看有没有算出税额
  SEL=20; renderFields(20,0);
  const txt=$("fields").textContent;
  ok("缴款书显示关税税率", /进口关税税率/.test(txt), txt.slice(0,80));
  ok("缴款书显示税额", /税额/.test(txt), "无税额行");
  ok("没有出现 NaN", txt.indexOf("NaN")<0, "含 NaN");

  // 还原案例 B 的商品
  b.hs=hsBak; b.hs_zh=zhBak; b.qty=qBak; b.unit=uBak; b.goods_no=gBak;

  document.getElementById("__R").textContent = ["@@@RE","SULT@@@"].join("")+R.join("\\n")+["@@@EN","D@@@"].join("");
 }catch(e){
  document.getElementById("__R").textContent = ["@@@RE","SULT@@@"].join("")+"FAIL 脚本抛错 :: "+(e&&e.message)+" @ "+((e&&e.stack||"").split("\\n")[1]||"")+["@@@EN","D@@@"].join("");
 }
})();
</script>`.replaceAll("__COUNT__", String(src.meta.count));

let syntaxBad = 0;
[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m, i) => {
  try { new Function(m[1]); } catch (e) { syntaxBad++; console.log(`✗ 第 ${i + 1} 个脚本块语法错误：${e.message}`); }
});
if (!syntaxBad) console.log("✓ 脚本块语法检查通过");

const tmp = path.join(root, "build", "_tariff_test.html");
fs.mkdirSync(path.dirname(tmp), { recursive: true });
fs.writeFileSync(tmp, html.replace(/<\/body>(?![\s\S]*<\/body>)/, test + "</body>"), "utf8");

const exe = process.env.CHROME || ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium"].find(p => { try { return fs.existsSync(p); } catch (e) { return false; } });
if (!exe) { console.log("✗ 找不到 Chrome，跳过"); process.exit(syntaxBad ? 1 : 0); }

const dom = execFileSync(exe, ["--headless=new", "--disable-gpu", "--no-sandbox",
  "--allow-file-access-from-files", "--virtual-time-budget=5000", "--dump-dom",
  "file:///" + tmp.replace(/\\/g, "/")], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

const m = dom.match(/@@@RESULT@@@([\s\S]*?)@@@END@@@/);
if (!m) { console.log("✗ 测试脚本没跑起来"); process.exit(1); }
const lines = m[1].trim().split(/\r?\n/).filter(Boolean);
let bad = 0;
lines.forEach(l => { if (l.startsWith("FAIL")) bad++; console.log(l.startsWith("FAIL") ? "✗ " + l.slice(5) : "✓ " + l.slice(5)); });
console.log(`\n${lines.length - bad}/${lines.length} 通过`);
fs.unlinkSync(tmp);
process.exit(bad || syntaxBad ? 1 : 0);
