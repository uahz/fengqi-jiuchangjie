import re
s = open('_art/out/wx.js', encoding='utf-8').read()
i = s.index('const S={')
ids = re.findall(r'\n([a-z0-9_]+):\{', s[i:])
print('节点数', len(ids))
for nid in ids:
    j = s.index(nid + ':{', i)
    seg = s[j:j + 700]
    bg = re.search(r'bg:"([\w-]+)"', seg)
    tags = []
    if 'choices' in seg: tags.append('choices')
    if 'ending:' in seg: tags.append('ending')
    if 'wave:' in seg: tags.append('wave')
    if 'era:' in seg: tags.append('era')
    if 'cardOpts' in seg: tags.append('card')
    print(f'{nid:12s} {bg.group(1) if bg else "-":12s} {",".join(tags)}')
