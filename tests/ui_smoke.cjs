const fs = require('fs'), vm=require('vm'), assert=require('assert');
const js=fs.readFileSync(__dirname+'/../custom_components/lightshow_studio/static/lightshow-studio.js','utf8');
const data=JSON.parse(fs.readFileSync(__dirname+'/defaults-fixture.json','utf8'));
let klass;
const context={
  HTMLElement:class {attachShadow(){this.shadowRoot={innerHTML:'',querySelector:()=>null};return this.shadowRoot;}},
  customElements:{get:()=>null,define:(name,cls)=>{klass=cls;}},
  window:{customCards:[],setInterval:()=>1,clearInterval:()=>{},prompt:()=>"Test",confirm:()=>true},
};
vm.runInNewContext(js,context);
const card=new klass();card._settings=data;card._pack='halloween';card._scene='castle';card._data={settings:data,devices:[],suggestions:{},migrated:false,status:{running:false,pack_id:'',scene_id:'',previewing:[],warnings:[]}};
card._hass={states:Object.fromEntries(data.fixtures.map(x=>[x.entity_id,{attributes:{friendly_name:x.entity_id},state:'on'}]))};
Object.defineProperty(card,'isConnected',{get:()=>true});
for(const tab of ['shows','lights','editor','schedule','library']){
  card._tab=tab;card._render();assert(card.shadowRoot.innerHTML.includes('LIGHTSHOW STUDIO'),`missing title ${tab}`);
  assert(!card.shadowRoot.innerHTML.includes('undefined'), `unexpected undefined ${tab}`);
}
card._pack='christmas';card._ensureSelected();card._tab='shows';card._render();
assert(card.shadowRoot.innerHTML.includes('Wintermärchen'));
assert(card.shadowRoot.innerHTML.includes('Ablauf starten'));
console.log('PASS: card renders five tabs, programs and second pack');
