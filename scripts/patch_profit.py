# -*- coding: utf-8 -*-
"""给函电预算模块加「盈亏调节」：绝对盈亏双滑块 + 相对盈亏率滑轨 + 两个平衡按钮。
所有控件都作用在成交单价（bPrice）上，从而与合同金额、单据、函电同步。
"""
import io
import os

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "_letters_src.html")
s = io.open(P, encoding="utf-8", newline=None).read()
orig = s

# ---------- 1. 面板 HTML + CSS ----------
HTML = '''<style>
  .pft{border:1px solid #CFE0F5;border-radius:10px;margin-top:12px;overflow:hidden;
       background:linear-gradient(180deg,#F5FAFF,#FFFFFF)}
  .pft-hd{display:flex;align-items:center;gap:10px;padding:9px 12px;
          background:linear-gradient(90deg,#E8F3FF,#F2FBF6);border-bottom:1px solid #D8E7F8}
  .pft-hd b{font-size:12.5px;color:#1B4FD8;letter-spacing:1px}
  .pft-hd span{font-size:11px;color:#6B7C93}
  .pft-grid{display:grid;grid-template-columns:1fr 178px 1fr;gap:10px;padding:12px}
  .pft-side{background:#fff;border:1px solid #E1EBF7;border-radius:9px;padding:10px 12px}
  .pft-side.ex{border-left:4px solid #0EA5A4}
  .pft-side.im{border-left:4px solid #F97316}
  .pft-lab{display:flex;align-items:baseline;gap:8px;font-size:11.5px;color:#4A5B72}
  .pft-lab b{font-size:12.5px;color:#16233A}
  .pft-lab em{margin-left:auto;font-style:normal;font-weight:700;font-size:15px;
              font-family:Consolas,monospace}
  .ex .pft-lab em{color:#0B8F8E}.im .pft-lab em{color:#D9600B}
  .pft-side input[type=range]{width:100%;margin:9px 0 3px;height:18px;cursor:grab}
  .pft-side.ex input[type=range]{accent-color:#0EA5A4}
  .pft-side.im input[type=range]{accent-color:#F97316}
  .pft-val{font-size:12px;font-family:Consolas,monospace;color:#33445C;text-align:right}
  .pft-val.neg{color:#C0341C}
  .pft-mid{display:flex;flex-direction:column;gap:8px;justify-content:center}
  .pft-mid button{cursor:pointer;border:0;border-radius:8px;padding:9px 6px;font-size:11.5px;
    font-weight:600;color:#fff;line-height:1.35;transition:filter .15s}
  #pftBalAbs{background:linear-gradient(135deg,#2563EB,#1D4ED8)}
  #pftBalRel{background:linear-gradient(135deg,#7C3AED,#6D28D9)}
  .pft-mid button:hover{filter:brightness(1.1)}
  .pft-rel{margin:0 12px 12px;background:#fff;border:1px solid #E1EBF7;border-radius:9px;padding:10px 14px}
  .pft-rel-hd{display:flex;align-items:center;gap:8px;font-size:11.5px;color:#4A5B72;margin-bottom:7px}
  .pft-rel-hd b{font-size:12.5px;color:#16233A}
  .pft-rel-bar{display:grid;grid-template-columns:84px 1fr 84px;align-items:center;gap:12px}
  .pft-pct{font-size:15px;font-weight:700;font-family:Consolas,monospace;text-align:center}
  .pft-pct.l{color:#0B8F8E}.pft-pct.r{color:#D9600B}
  .pft-pct small{display:block;font-size:9.5px;font-weight:400;color:#8B95A3;letter-spacing:0}
  .pft-track{position:relative;height:22px}
  .pft-track input{position:absolute;left:0;top:0;width:100%;margin:0;height:22px;
    -webkit-appearance:none;appearance:none;background:transparent;z-index:2;cursor:grab}
  .pft-track input::-webkit-slider-runnable-track{height:10px;border-radius:5px;
    background:linear-gradient(90deg,#0EA5A4 var(--p,50%),#F97316 var(--p,50%))}
  .pft-track input::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;
    border-radius:50%;background:#fff;border:3px solid #2563EB;margin-top:-5px;
    box-shadow:0 2px 6px rgba(37,99,235,.35)}
  .pft-note{padding:0 12px 10px;font-size:11px;color:#6B7C93;font-family:Consolas,monospace}
</style>

    <div class="pft">
      <div class="pft-hd"><b>盈亏调节</b>
        <span>拖动滑块直接改成交单价 —— 合同金额、单据、函电一起变</span></div>

      <div class="pft-grid">
        <div class="pft-side ex">
          <div class="pft-lab"><b>出口商</b><span>绝对盈亏</span><em id="pftExRate">—</em></div>
          <input type="range" id="pftExSlider" min="-50" max="150" step="0.5" value="19.7">
          <div class="pft-val" id="pftExAmt">—</div>
        </div>
        <div class="pft-mid">
          <button id="pftBalAbs" title="调整成交价，使出口商与进口商的盈亏额相同">⚖ 一键平衡<br>绝对盈亏</button>
          <button id="pftBalRel" title="调整成交价，使出口商与进口商的盈亏率相同">⚖ 一键平衡<br>相对盈亏</button>
        </div>
        <div class="pft-side im">
          <div class="pft-lab"><b>进口商</b><span>绝对盈亏</span><em id="pftImRate">—</em></div>
          <input type="range" id="pftImSlider" min="-50" max="150" step="0.5" value="8.2">
          <div class="pft-val" id="pftImAmt">—</div>
        </div>
      </div>

      <div class="pft-rel">
        <div class="pft-rel-hd"><b>相对盈亏率</b><span>双方盈亏额占总额的比例，拖动可调分配</span></div>
        <div class="pft-rel-bar">
          <span class="pft-pct l" id="pftRelL">50.0%<small>出口占比</small></span>
          <div class="pft-track"><input type="range" id="pftRelSlider" min="0" max="100" step="0.5" value="50"></div>
          <span class="pft-pct r" id="pftRelR">50.0%<small>进口占比</small></span>
        </div>
      </div>
      <div class="pft-note" id="pftNote">—</div>
    </div>

'''

anchor = '    <!-- 隐藏的原控件（供联动逻辑读写，不在界面显示） -->'
assert anchor in s, "找不到面板插入锚点"
s = s.replace(anchor, HTML + anchor, 1)

# ---------- 2. 原「出口商预期盈亏率」输入框改为随滑块显示 ----------
old_rate = '<div class="fld"><label>出口商预期盈亏率（%）</label><input id="bExpRate" value="19.67"></div>'
new_rate = ('<div class="fld"><label>出口商盈亏率（%）· 随滑块</label>'
            '<input id="bExpRate" readonly style="background:#f7f8fa; color:#0B8F8E; font-weight:700"></div>')
assert old_rate in s, "找不到 bExpRate 输入框"
s = s.replace(old_rate, new_rate, 1)

# ---------- 3. calcBudget 支持静默试算 + 暴露结果 ----------
old_sig = "function calcBudget(){"
new_sig = "function calcBudget(silent){"
assert old_sig in s
s = s.replace(old_sig, new_sig, 1)

old_tail = '''  document.getElementById("bResult").innerHTML = html;
  document.getElementById("bResult").style.display = "block";
  refQuote(mode,N,UP,xr);
}'''
new_tail = '''  /* 把本轮的数值结果留给盈亏调节用（静默试算也走这里） */
  window.__BUDGET={N:N,UP:UP,xr:xr,ir:ir,exG26:exG26,exPftG:exPftG,exPftRG:exPftRG,
                   costG:costG,imK26:imK26,imCostG:imK25,imPftG:imK27,imPftRG:imK28,
                   imCur:imCur,exCur:exCur};
  const _br=document.getElementById("bExpRate");
  if(_br) _br.value=(exPftRG*100).toFixed(2);
  if(silent) return;
  document.getElementById("bResult").innerHTML = html;
  document.getElementById("bResult").style.display = "block";
  refQuote(mode,N,UP,xr);
  if(typeof pftSync==="function") pftSync();
}'''
assert old_tail in s, "找不到 calcBudget 收尾"
s = s.replace(old_tail, new_tail, 1)

# ---------- 4. 盈亏调节逻辑 ----------
JS = r'''
/* ================= 盈亏调节（绝对 / 相对） =================
   所有控件都只改一个东西：成交单价 UP。改完重算预算，
   合同金额、单据、函电、参考报价随上游同步跟着变。 */
const PFT={busy:false};

/* 临时把成交单价设成 up 试算一遍，拿结果但不碰界面 */
function pftProbe(up){
  const el=document.getElementById("bPrice");
  if(!el) return null;
  const old=el.value;
  el.value=String(up);
  calcBudget(true);
  el.value=old;
  return window.__BUDGET||null;
}

function pftApply(up){
  if(!isFinite(up)||up<=0) return;
  const el=document.getElementById("bPrice");
  el.value=(Math.round(up*100)/100).toFixed(2);
  calcBudget(false);
}

function pftMoney(x){
  const s=Math.abs(x).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
  return (x<0?"−":"+")+s;
}

/* 计算完刷新控件（不回写价格，避免循环） */
function pftSync(){
  const b=window.__BUDGET; if(!b) return;
  const exR=b.exPftRG*100, imR=b.imPftRG*100;
  const se=document.getElementById("pftExSlider"), si=document.getElementById("pftImSlider");
  if(se && document.activeElement!==se) se.value=Math.max(-50,Math.min(150,exR)).toFixed(1);
  if(si && document.activeElement!==si) si.value=Math.max(-50,Math.min(150,imR)).toFixed(1);

  const e1=document.getElementById("pftExRate"), e2=document.getElementById("pftImRate");
  if(e1) e1.textContent=exR.toFixed(2)+"%";
  if(e2) e2.textContent=imR.toFixed(2)+"%";

  const a1=document.getElementById("pftExAmt"), a2=document.getElementById("pftImAmt");
  if(a1){ a1.textContent=pftMoney(b.exPftG)+" USD"; a1.className="pft-val"+(b.exPftG<0?" neg":""); }
  if(a2){ a2.textContent=pftMoney(b.imPftG)+" "+b.imCur; a2.className="pft-val"+(b.imPftG<0?" neg":""); }

  const tot=b.exPftG+b.imPftG;
  let share= tot!==0 ? (b.exPftG/tot*100) : 50;
  if(!isFinite(share)) share=50;
  share=Math.max(0,Math.min(100,share));
  const rs=document.getElementById("pftRelSlider");
  if(rs){
    if(document.activeElement!==rs) rs.value=share.toFixed(1);
    rs.style.setProperty("--p", share.toFixed(1)+"%");
  }
  const l=document.getElementById("pftRelL"), r=document.getElementById("pftRelR");
  if(l) l.firstChild.nodeValue=share.toFixed(1)+"%";
  if(r) r.firstChild.nodeValue=(100-share).toFixed(1)+"%";

  const note=document.getElementById("pftNote");
  if(note) note.textContent="成交单价 USD "+b.UP.toFixed(2)
    +"　出口盈亏 "+pftMoney(b.exPftG)+" USD"
    +"　进口盈亏 "+pftMoney(b.imPftG)+" "+b.imCur;
  PFT.busy=false;
}

/* 出口滑块：盈亏率 → 反解成交单价（出口成本与成交价无关，一步到位） */
function pftSetExRate(pct){
  const b=window.__BUDGET; if(!b||!(b.N>0)) return;
  const cost=b.exG26-b.exPftG;            /* 出口总成本（USD），与 UP 无关 */
  pftApply(cost*(1+pct/100)/b.N);
}

/* 进口滑块：先两次采样求「进口总成本 = A + B·UP」，再解目标盈亏率 */
function pftSetImRate(pct){
  const b=window.__BUDGET; if(!b) return;
  const up0=b.UP, u2=up0*1.05+0.5;
  const p1=pftProbe(up0), p2=pftProbe(u2);
  if(!p1||!p2) return;
  const B=(p2.imCostG-p1.imCostG)/(u2-up0);
  if(!isFinite(B)||Math.abs(B)<1e-9) return;
  const A=p1.imCostG-B*up0;
  pftApply((p1.imK26/(1+pct/100)-A)/B);
}

/* 相对盈亏率滑轨：让「出口盈亏额 ÷ 双方总额」等于目标占比 */
function pftSetShare(pct){
  const b=window.__BUDGET; if(!b) return;
  const p=Math.max(0,Math.min(100,pct))/100;
  const up0=b.UP, u2=up0*1.05+0.5;
  const p1=pftProbe(up0), p2=pftProbe(u2);
  if(!p1||!p2) return;
  const d1=(p2.exPftG-p1.exPftG)/(u2-up0), c1=p1.exPftG-d1*up0;
  const d2=(p2.imPftG-p1.imPftG)/(u2-up0), c2=p1.imPftG-d2*up0;
  const D=d1+d2, C=c1+c2;
  const den=d1-p*D;
  if(Math.abs(den)<1e-9) return;
  pftApply((p*C-c1)/den);
}

/* 一键平衡绝对盈亏：两边盈亏额相等（两条直线求交点） */
function pftBalanceAbs(){
  const b=window.__BUDGET; if(!b) return;
  const up0=b.UP, u2=up0*1.05+0.5;
  const p1=pftProbe(up0), p2=pftProbe(u2);
  if(!p1||!p2) return;
  const d1=(p2.exPftG-p1.exPftG)/(u2-up0), c1=p1.exPftG-d1*up0;
  const d2=(p2.imPftG-p1.imPftG)/(u2-up0), c2=p1.imPftG-d2*up0;
  if(Math.abs(d1-d2)<1e-12) return;
  pftApply((c2-c1)/(d1-d2));
}

/* 一键平衡相对盈亏：两边盈亏率相等（单调，二分） */
function pftBalanceRel(){
  const b=window.__BUDGET; if(!b) return;
  const F=(u)=>{ const r=pftProbe(u); return r? (r.exPftRG-r.imPftRG) : NaN; };
  let lo=Math.max(0.01,b.UP*0.15), hi=Math.max(b.UP*4, b.UP+30);
  let flo=F(lo), fhi=F(hi);
  if(!isFinite(flo)||!isFinite(fhi)) return;
  if(flo*fhi>0){
    const note=document.getElementById("pftNote");
    if(note) note.textContent="当前成本与市场价下，两边盈亏率无法完全相等（可调市场价再试）";
    return;
  }
  for(let i=0;i<36;i++){
    const mid=(lo+hi)/2, fm=F(mid);
    if(flo*fm<=0){ hi=mid; } else { lo=mid; flo=fm; }
  }
  pftApply((lo+hi)/2);
}

(function bindPft(){
  const se=document.getElementById("pftExSlider");
  const si=document.getElementById("pftImSlider");
  const sr=document.getElementById("pftRelSlider");
  const ba=document.getElementById("pftBalAbs");
  const br=document.getElementById("pftBalRel");
  if(se) se.addEventListener("input",e=>{ pftSetExRate(Number(e.target.value)); });
  if(si) si.addEventListener("input",e=>{ pftSetImRate(Number(e.target.value)); });
  if(sr) sr.addEventListener("input",e=>{ pftSetShare(Number(e.target.value)); });
  if(ba) ba.addEventListener("click",pftBalanceAbs);
  if(br) br.addEventListener("click",pftBalanceRel);

  /* 首屏先静默算一遍，让滑块直接显示真实值 */
  setTimeout(()=>{
    try{
      if(!window.__BUDGET) calcBudget(true);
      pftSync();
    }catch(e){}
  }, 120);
})();
'''

# 插到最后一个 </script> 之前
idx = s.rfind("</script>")
assert idx > 0
s = s[:idx] + JS + "\n" + s[idx:]

io.open(P, "w", encoding="utf-8", newline="\r\n").write(s)
print("已改 _letters_src.html：%d → %d 字节" % (len(orig), len(s)))
