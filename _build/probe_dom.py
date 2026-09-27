#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DOM 布局探针：把关键元素的盒模型尺寸 dump 出来（用 --dump-dom 读取）。"""
import os, re, subprocess, sys, shutil
from pathlib import Path

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ROOT = Path("C:/Users/Administrator/WorkBuddy/狂飙game")
PWA = ROOT / "02-安卓版PWA（写实电影感）" / "index.html"
WEB = ROOT / "01-网页版（写实电影感）" / "fengqi-jiuchangjie.html"

PROBE = r'''
(function(){
  try{window.__goto('c1_2');}catch(e){}
  var _n=0,_t=setInterval(function(){
    var c=document.getElementById('choices');
    if((c&&c.children.length)||_n++>14){clearInterval(_t);dump();return;}
    document.getElementById('dlg').click();},180);
  function box(id){var e=document.getElementById(id);if(!e)return id+': MISSING';
    var r=e.getBoundingClientRect();var cs=getComputedStyle(e);
    return id+' rect='+[r.x|0,r.y|0,r.width|0,r.height|0].join(',')
      +' disp='+cs.display+' wrap='+cs.flexWrap+' overflow='+cs.overflow; }
  function dump(){
    var o=[];
    o.push('VP='+innerWidth+'x'+innerHeight);
    ['hud','nav','choices','dlg','bottom','sndBtn','c_risk','titleArt','sceneEnv'].forEach(function(k){o.push(box(k));});
    var hud=document.getElementById('hud');
    if(hud){o.push('hud.scrollW='+hud.scrollWidth+' clientW='+hud.clientWidth);
      [].forEach.call(hud.children,function(c,i){
        var r=c.getBoundingClientRect();
        o.push('  child'+i+' '+c.id+' x='+(r.x|0)+' w='+(r.width|0)+' y='+(r.y|0));});}
    var ta=document.getElementById('titleArt');
    if(ta)o.push('titleArt.bg='+(ta.style.backgroundImage||'(none)').slice(0,40)+' op='+ta.style.opacity);
    var pre=document.createElement('pre');pre.id='__probe__';
    pre.textContent=('@@'+'PROBE@@')+'\n'+o.join('\n')+'\n'+('@@'+'END@@');
    document.body.appendChild(pre);
  }
})();
'''


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "pwa"
    size = sys.argv[2] if len(sys.argv) > 2 else "390,844"
    tgt = PWA if which == "pwa" else WEB
    html = tgt.read_text(encoding="utf-8")
    html = html.replace("</body>", "<script>" + PROBE + "</script>\n</body>", 1)
    hp = tgt.parent / f"_probe_{which}.html"
    hp.write_text(html, encoding="utf-8")
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--virtual-time-budget=9000",
           f"--window-size={size}", "--dump-dom", hp.as_uri()]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    dom = r.stdout.decode("utf-8", "replace")
    m = re.search(r"@@PROBE@@(.*?)@@END@@", dom, re.S)
    if m:
        print(m.group(1).strip())
    else:
        print("!! 未取到探针输出；dom 长度", len(dom))
        print(dom[-1500:])
    hp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
