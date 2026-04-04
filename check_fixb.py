# -*- coding: utf-8 -*-
html = open(r'D:\辩论\templates\debate.html', encoding='utf-8', errors='replace').read()
js_start = html.find('<script>')
js_end = html.rfind('</script>')
js = html[js_start+8:js_end]

# Check complete handler
idx = js.find("'complete'")
if idx >= 0:
    snippet = js[idx:idx+250]
    print('COMPLETE HANDLER:')
    print(repr(snippet))

# Check if handleGroupStart was added
print('\nhandleGroupStart:', 'function handleGroupStart' in js)
print('group_start in handleEvent:', "t === 'group_start'" in js)

# Check round marker
print('\nROUND marker:', '// ==================== ROUND' in js)
idx2 = js.find('// ==================== ROUND')
if idx2 >= 0:
    print('ROUND marker context:')
    print(repr(js[idx2:idx2+30]))
