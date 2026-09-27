/* 用 playwright-core 驱动本机 Edge，做真实移动端设备模拟截图 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const ROOT = 'C:/Users/Administrator/WorkBuddy/狂飙game';
const OUT = path.join(ROOT, '_shots_new');
const HARNESS = path.join(ROOT, '_build', 'harness');

const TARGETS = {
  web: path.join(ROOT, '01-网页版（写实电影感）', 'fengqi-jiuchangjie.html'),
  pwa: path.join(ROOT, '02-安卓版PWA（写实电影感）', 'index.html'),
};

const ADV = "var _n=0;var _t=setInterval(function(){var c=document.getElementById('choices');" +
  "if((c&&c.children.length)||_n++>14){clearInterval(_t);return;}document.getElementById('dlg').click();},180);";

const STATES = {
  '01-title': '',
  '02-story': "window.__goto('c1_1');setTimeout(function(){" + ADV + "},250);",
  '03-choice': "window.__goto('c1_2');setTimeout(function(){" + ADV + "},250);",
  '04-card': "window.__goto('c1_8');setTimeout(function(){" + ADV + "},250);",
  '05-rain': "window.__goto('c1_7');setTimeout(function(){" + ADV + "},250);",
  '06-wave': "window.__goto('w1');",
  '07-gallery': "window.__goto('c1_1');setTimeout(function(){showGallery('end')},120);",
  '08-panel': "window.__goto('c1_1');setTimeout(function(){openPanel('aff')},120);",
  '09-ending': "window.__goto('c4_4');setTimeout(function(){" + ADV + "},250);",
  '11-era': "window.__goto('c2_1a');",
};

// 视口：桌面 + 主流手机/平板
const VIEWS = {
  desk: { w: 1440, h: 900, dpr: 1, touch: false },
  wide: { w: 1920, h: 1080, dpr: 1, touch: false },
  iphone: { w: 390, h: 844, dpr: 3, touch: true },
  android: { w: 412, h: 915, dpr: 2.6, touch: true },
  small: { w: 360, h: 640, dpr: 3, touch: true },
};

async function main() {
  const only = process.argv[2] || 'all';
  const viewArg = process.argv[3] || '';
  fs.mkdirSync(OUT, { recursive: true });
  fs.mkdirSync(HARNESS, { recursive: true });

  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const made = [];

  for (const [tag, file] of Object.entries(TARGETS)) {
    if (only !== 'all' && tag !== only) continue;
    const base = fs.readFileSync(file, 'utf8');
    const views = viewArg ? [viewArg] :
      (tag === 'web' ? ['desk'] : ['iphone']);
    for (const vname of views) {
      const v = VIEWS[vname];
      const ctx = await browser.newContext({
        viewport: { width: v.w, height: v.h },
        deviceScaleFactor: v.dpr,
        hasTouch: v.touch,
        isMobile: v.touch,
        userAgent: v.touch
          ? 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Mobile Safari/537.36'
          : undefined,
      });
      const page = await ctx.newPage();
      for (const [sname, inject] of Object.entries(STATES)) {
        if (sname === '10-drag') continue; // 单独处理
        let html = base;
        if (inject) {
          html = html.replace('</body>',
            "<script>window.addEventListener('load',function(){setTimeout(function(){try{"
            + inject + "}catch(e){}},180)});</script>\n</body>", 1);
        }
        const hp = path.join(HARNESS, `_s_${tag}_${vname}_${sname}.html`);
        // harness 放在 _build/harness，需把相对图片路径指回原目录
        if (tag !== 'web') html = html.replace(/"img\//g, '"' + path.dirname(file).replace(/\\/g, '/') + '/img/');
        fs.writeFileSync(hp, html, 'utf8');
        made.push(hp);
        await page.goto('file:///' + hp.replace(/\\/g, '/'));
        await page.waitForTimeout(2600);
        const out = path.join(OUT, `${tag}-${sname}-${vname}.png`);
        await page.screenshot({ path: out });
        console.log('  ' + path.basename(out) + '  ' + Math.round(fs.statSync(out).size / 1024) + ' KB');
      }
      await ctx.close();
    }
  }
  await browser.close();
  console.log('done');
}
main().catch(e => { console.error(e); process.exit(1); });
