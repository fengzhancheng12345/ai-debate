# -*- coding: utf-8 -*-
html = open(r'D:\辩论\templates\debate.html', encoding='utf-8', errors='replace').read()
js_start = html.find('<script>')
js_end = html.rfind('</script>')
js = html[js_start+8:js_end]
orig_len = len(js)
changes = []

# FIX A: handleGroupVoteResult add updateTrackerGroup
old_a = "  const statusEl = document.getElementById('tracker-status-' + d.group_id);\n  if (statusEl) { const icon = d.group_vote === '支持' ? '✅' : d.group_vote === '反对' ? '❌' : '⚖️'; statusEl.textContent = icon + ' ' + d.group_vote; statusEl.style.color = d.group_vote === '支持' ? 'var(--green)' : d.group_vote === '反对' ? 'var(--red)' : 'var(--yellow)'; }\n}"
new_a = "  const statusEl = document.getElementById('tracker-status-' + d.group_id);\n  if (statusEl) { const icon = d.group_vote === '支持' ? '✅' : d.group_vote === '反对' ? '❌' : '⚖️'; statusEl.textContent = icon + ' ' + d.group_vote; statusEl.style.color = d.group_vote === '支持' ? 'var(--green)' : d.group_vote === '反对' ? 'var(--red)' : 'var(--yellow)'; }\n  if (d.votes) { updateTrackerGroup(d.group_id, d.votes); }\n}"
if old_a in js:
    js = js.replace(old_a, new_a, 1)
    changes.append('A: handleGroupVoteResult updateTrackerGroup')
    print('FIX A OK')

# FIX B: complete - set evtSource = null
old_b = "if (evtSource) evtSource.close();\n      addStatus('全部完成', 'done');"
new_b = "if (evtSource) { evtSource.close(); evtSource = null; }\n      addStatus('全部完成', 'done');"
if old_b in js:
    js = js.replace(old_b, new_b, 1)
    changes.append('B: complete evtSource = null')
    print('FIX B OK')

# FIX C: remove markGroupDone
old_c = "function markGroupDone(groupId) { const badge = document.getElementById('badge-' + groupId); if (badge) badge.className = 'group-badge'; }\n"
if old_c in js:
    js = js.replace(old_c, '', 1)
    changes.append('C: removed dead markGroupDone')
    print('FIX C OK')

# FIX D: add handleGroupStart function + mapping
grpst_func = "function handleGroupStart(d) {\n  const badge = document.getElementById('badge-' + d.group_id);\n  if (badge) badge.className = 'group-badge active';\n}\n"
if 'function handleGroupStart' not in js:
    marker = "// ==================== ROUND ===================="
    if marker in js:
        js = js.replace(marker, grpst_func + marker, 1)
        changes.append('D1: added handleGroupStart function')
        print('FIX D1 OK')

# FIX D2: add to handleEvent mapping
grpst_map = "  else if (t === 'group_start') { handleGroupStart(d); }\n"
if "t === 'group_start'" not in js:
    insert_after = "  else if (t === 'groups_created')"
    if insert_after in js:
        js = js.replace(insert_after, grpst_map + insert_after, 1)
        changes.append('D2: added group_start to handleEvent')
        print('FIX D2 OK')

print()
print('Changes:', changes)
print('JS delta: %+d' % (len(js) - orig_len))

html = html[:js_start+8] + js + html[js_end:]
with open(r'D:\辩论\templates\debate.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Written: %d chars' % len(html))
