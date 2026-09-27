/* 游戏本体自检：调用内置 window.__qa 做剧情图静态校验 + 随机通关模拟 */
const { chromium } = require('playwright-core');
const path = require('path');

const ROOT = 'C:/Users/Administrator/WorkBuddy/狂飙game';
const FILES = {
  '网页版': path.join(ROOT, '01-网页版（写实电影感）', 'fengqi-jiuchangjie.html'),
  'PWA/安卓': path.join(ROOT, '02-安卓版PWA（写实电影感）', 'index.html'),
  'APK资源': path.join(ROOT, '05-Android源码工程', 'assets', 'index.html'),
};

(async () => {
  const n = parseInt(process.argv[2] || '600', 10);
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  let bad = 0;
  for (const [name, file] of Object.entries(FILES)) {
    const ctx = await browser.newContext({ viewport: { width: 420, height: 900 } });
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push('pageerror: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
    await page.goto('file:///' + file.replace(/\\/g, '/'));
    await page.waitForTimeout(600);
    const raw = await page.evaluate(k => window.__qa(k), n);
    const r = JSON.parse(raw);
    const ok = r.errCount === 0 && r.endingsReached === n && errs.length === 0;
    if (!ok) bad++;
    console.log(`[${ok ? 'PASS' : 'FAIL'}] ${name.padEnd(8)} 模拟 ${r.runs} 局 -> 到达结局 ${r.endingsReached} 局, ` +
      `静态/运行期错误 ${r.errCount} 条, 页面报错 ${errs.length} 条`);
    if (r.errs && r.errs.length) r.errs.slice(0, 5).forEach(e => console.log('        · ' + e));
    if (errs.length) errs.slice(0, 5).forEach(e => console.log('        · ' + e));
    await ctx.close();
  }
  await browser.close();
  console.log(bad ? `\n*** ${bad} 个平台未通过 ***` : '\n全部平台自检通过');
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
