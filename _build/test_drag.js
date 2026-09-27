/* 长按拖拽选择 · 真机模拟功能测试（不只是看截图，验证真能选中） */
const { chromium } = require('playwright-core');
const path = require('path'), fs = require('fs');

const ROOT = 'C:/Users/Administrator/WorkBuddy/狂飙game';
const FILE = path.join(ROOT, '02-安卓版PWA（写实电影感）', 'index.html');
const HARNESS = path.join(ROOT, '_build', 'harness');
const OUT = path.join(ROOT, '_shots_new');

const INJ = "window.__goto('c1_2');setTimeout(function(){var _n=0,_t=setInterval(function(){" +
  "var c=document.getElementById('choices');if((c&&c.children.length)||_n++>14){clearInterval(_t);return;}" +
  "document.getElementById('dlg').click();},180);},250);";

function harness() {
  fs.mkdirSync(HARNESS, { recursive: true });
  let html = fs.readFileSync(FILE, 'utf8');
  html = html.replace('</body>',
    "<script>window.addEventListener('load',function(){" + INJ + "});</script>\n</body>", 1);
  html = html.replace(/"img\//g, '"' + path.dirname(FILE).replace(/\\/g, '/') + '/img/');
  const hp = path.join(HARNESS, '_drag_test.html');
  fs.writeFileSync(hp, html, 'utf8');
  return 'file:///' + hp.replace(/\\/g, '/');
}

async function fresh(ctx, url) {
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  await page.goto(url);
  await page.waitForSelector('#choices .choice', { timeout: 10000 });
  await page.waitForTimeout(500);
  return { page, errs };
}
const centers = p => p.$$eval('#choices .choice', els => els.map(e => {
  const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
}));

(async () => {
  const url = harness();
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, hasTouch: true, isMobile: true,
  });
  const pass = [], fail = [];

  /* ---------- 用例 1：长按进入拖拽态并拖到第 3 项松手 ---------- */
  {
    const { page, errs } = await fresh(ctx, url);
    const labels = await page.$$eval('#choices .choice', e => e.map(x => x.textContent.trim().slice(0, 16)));
    console.log('选项数:', labels.length, labels);
    const c = await centers(page);
    const beforeNode = await page.evaluate(() => window.__st() && window.__st().node);
    await page.mouse.move(c[0].x, c[0].y);
    await page.mouse.down();
    await page.waitForTimeout(320);
    const mid = await page.evaluate(() => ({
      dragging: document.body.classList.contains('dragging'),
      dragged: !!document.querySelector('.choice.dragging'),
      over: document.querySelectorAll('.choice.dragOver').length,
      hint: !!document.querySelector('.dragHint'),
    }));
    console.log('① 长按 320ms 后 ->', JSON.stringify(mid));
    (mid.dragging && mid.dragged && mid.over === 1) ? pass.push('长按进入拖拽态')
      : fail.push('长按进入拖拽态 -> ' + JSON.stringify(mid));
    await page.screenshot({ path: path.join(OUT, 'pwa-10-drag-iphone.png') });

    await page.mouse.move(c[2].x, c[2].y, { steps: 10 });
    await page.waitForTimeout(160);
    const overIdx = await page.evaluate(() => [].indexOf.call(
      document.querySelectorAll('#choices .choice'), document.querySelector('.choice.dragOver')));
    console.log('② 拖到第 3 项 -> 高亮索引', overIdx, '(期望 2)');
    overIdx === 2 ? pass.push('拖动时高亮跟随') : fail.push('拖动时高亮跟随 -> ' + overIdx);

    await page.mouse.up();
    await page.waitForTimeout(700);
    const after = await page.evaluate(() => ({
      dragging: document.body.classList.contains('dragging'),
      chosen: [].indexOf.call(document.querySelectorAll('#choices .choice'), document.querySelector('.choice.chosen')),
      txt: document.getElementById('txt').textContent.slice(0, 20),
      node: window.__st() && window.__st().node,
    }));
    console.log('③ 松手后 ->', JSON.stringify(after));
    (!after.dragging && after.node && after.node !== beforeNode) ? pass.push(`松手即选中并推进剧情 (${beforeNode} -> ${after.node})`)
      : fail.push('松手选中未生效 -> ' + JSON.stringify(after) + ' beforeNode=' + beforeNode);
    errs.length ? fail.push('页面报错: ' + errs.join(' | ')) : pass.push('无页面报错');
    await page.close();
  }

  /* ---------- 用例 2：普通快速点按仍能正常选择 ---------- */
  {
    const { page, errs } = await fresh(ctx, url);
    const before = await page.textContent('#txt');
    const c = await centers(page);
    await page.mouse.click(c[0].x, c[0].y);
    await page.waitForTimeout(800);
    const afterTxt = await page.textContent('#txt');
    const changed = before !== afterTxt;
    console.log('④ 普通点按 -> 文本是否推进:', changed);
    changed ? pass.push('普通点按不被拖拽逻辑吞掉') : fail.push('普通点按未被响应');
    errs.length ? fail.push('页面报错: ' + errs.join(' | ')) : pass.push('无页面报错(点按)');
    await page.close();
  }

  /* ---------- 用例 3：短按后上下滑动（模拟滚动）不应误触发拖拽 ---------- */
  {
    const { page } = await fresh(ctx, url);
    const c = await centers(page);
    await page.mouse.move(c[0].x, c[0].y);
    await page.mouse.down();
    await page.waitForTimeout(60);
    await page.mouse.move(c[0].x, c[0].y - 60, { steps: 4 });
    await page.waitForTimeout(120);
    const st = await page.evaluate(() => document.body.classList.contains('dragging'));
    await page.mouse.up();
    console.log('⑤ 短按后上滑 60px -> 是否进入拖拽:', st, '(期望 false)');
    !st ? pass.push('短按上滑不误触发拖拽') : fail.push('短按上滑误触发拖拽');
    await page.close();
  }

  await browser.close();
  console.log('\n================ 测试结果 ================');
  pass.forEach(p => console.log('  [PASS] ' + p));
  fail.forEach(f => console.log('  [FAIL] ' + f));
  console.log(`合计 ${pass.length} 通过 / ${fail.length} 失败`);
  process.exit(fail.length ? 1 : 0);
})().catch(e => { console.error('运行异常:', e); process.exit(1); });
