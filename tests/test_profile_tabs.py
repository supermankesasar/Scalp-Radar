"""UI-only profile navigation regression; no live market requests."""
import shutil,subprocess,unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.nodes={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:
            self.nodes[a['id']]=(tag,a)

class ProfileTabsTests(unittest.TestCase):
    def test_default_and_preview_are_separate(self):
        page=Page();page.feed((ROOT/'index.html').read_text(encoding='utf-8'))
        nodes=page.nodes
        self.assertEqual(nodes['profileScalping'][1]['aria-controls'],'scalpingPanel')
        self.assertEqual(nodes['profileSwing'][1]['aria-controls'],'swingPanel')
        self.assertEqual(nodes['profileScalping'][1]['aria-selected'],'true')
        self.assertNotIn('hidden',nodes['scalpingPanel'][1])
        self.assertIn('hidden',nodes['swingPanel'][1])
        self.assertEqual(nodes['profileMajors'][1]['aria-controls'],'majorsPanel')
        self.assertIn('hidden',nodes['majorsPanel'][1])
        self.assertIn('rows',nodes)
    @unittest.skipUnless(shutil.which('node'),'Node.js not installed')
    def test_profile_switch_and_keyboard(self):
        js=(ROOT/'ui.js').read_text(encoding='utf-8')
        nav=js[js.index('function selectProfile('):js.index('function updateModeUI(')]
        script="""
const assert=require('node:assert/strict');
const ids=['scalpingPanel','swingPanel','majorsPanel','refresh','profileScalping','profileSwing','profileMajors'];
const nodes=Object.fromEntries(ids.map(id=>[id,{hidden:false,attrs:{},handlers:{},
 setAttribute(k,v){this.attrs[k]=v},addEventListener(k,v){this.handlers[k]=v},focus(){this.focused=true}}]));
const $=id=>nodes[id];
"""+nav+"""
initProfiles();
assert.equal(nodes.scalpingPanel.hidden,false);
assert.equal(nodes.swingPanel.hidden,true);
nodes.profileSwing.handlers.click();
assert.equal(nodes.scalpingPanel.hidden,true);
assert.equal(nodes.swingPanel.hidden,false);
assert.equal(nodes.refresh.hidden,true);
assert.equal(nodes.profileSwing.attrs['aria-selected'],'true');
nodes.profileSwing.handlers.keydown({key:'ArrowRight',preventDefault(){}});
assert.equal(nodes.majorsPanel.hidden,false);
assert.equal(nodes.swingPanel.hidden,true);
nodes.profileMajors.handlers.keydown({key:'Home',preventDefault(){}});
assert.equal(nodes.scalpingPanel.hidden,false);
assert.equal(nodes.refresh.hidden,false);
assert.equal(nodes.profileScalping.focused,true);
"""
        subprocess.run(['node','-e',script],check=True,timeout=10)
if __name__=='__main__':unittest.main()
