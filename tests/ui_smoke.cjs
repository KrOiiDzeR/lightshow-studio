const fs = require('fs'), vm=require('vm'), assert=require('assert');
const js=fs.readFileSync(__dirname+'/../custom_components/lightshow_studio/static/lightshow-studio.js','utf8');
const data=JSON.parse(fs.readFileSync(__dirname+'/defaults-fixture.json','utf8'));
const classes=new Map();
const context={
  HTMLElement:class {attachShadow(){this.shadowRoot={innerHTML:'',querySelector:()=>null};return this.shadowRoot;}},
  customElements:{get:name=>classes.get(name),define:(name,cls)=>classes.set(name,cls)},
  window:{customCards:[],setInterval:()=>1,clearInterval:()=>{},prompt:()=>"Test",confirm:()=>true},
};
vm.runInNewContext(js,context);
const card=new (classes.get('lightshow-studio'))();card._settings=data;card._pack='halloween';card._scene='castle';card._data={settings:data,devices:[],suggestions:{},migrated:false,status:{running:false,pack_id:'',scene_id:'',previewing:[],warnings:[]}};
card._hass={states:Object.fromEntries(data.fixtures.map(x=>[x.entity_id,{attributes:{friendly_name:x.entity_id},state:'on'}]))};
Object.defineProperty(card,'isConnected',{get:()=>true});
for(const tab of ['shows','schedule']){
  card._tab=tab;card._render();assert(card.shadowRoot.innerHTML.includes('LIGHTSHOW STUDIO'),`missing title ${tab}`);
  assert(!card.shadowRoot.innerHTML.includes('undefined'), `unexpected undefined ${tab}`);
}
card._pack='christmas';card._ensureSelected();card._tab='shows';card._render();
assert(card.shadowRoot.innerHTML.includes('Wintermärchen'));
assert(card.shadowRoot.innerHTML.includes('Ablauf starten'));
assert(!card.shadowRoot.innerHTML.includes('data-action="add-fixture"'));
assert(!card.shadowRoot.innerHTML.includes('data-action="show-import"'));
card._tab='editor';card.setConfig({mode:'configuration'});assert.equal(card._tab,'shows');
const config=new (classes.get('lightshow-studio-configuration'))();
config._settings=data;config._data=card._data;config._hass=card._hass;
Object.defineProperty(config,'isConnected',{get:()=>true});
for(const tab of ['connection','lights','editor','shuffle','library']){
 config._tab=tab;config._render();assert(config.shadowRoot.innerHTML.includes('Lightshow einrichten'));
 assert(!config.shadowRoot.innerHTML.includes('data-action="start"'));
 assert(!config.shadowRoot.innerHTML.includes('undefined'));
}
(async()=>{
 const calls=[];card._ws=async(action,args)=>{calls.push({action,args});return JSON.parse(JSON.stringify(card._data));};
 card._tab='shows';card._dirty=true;
 await card._click({target:{closest:()=>({dataset:{action:'save'}})}});
 assert.equal(calls[0].action,'operate');assert.deepEqual(Object.keys(calls[0].args.changes).sort(),['options','schedules','weekly']);
 assert(!calls[0].args.settings);
 config._ws=async(action,args)=>{calls.push({action,args});return JSON.parse(JSON.stringify(config._data));};
 config._dirty=true;await config._click({target:{closest:()=>({dataset:{action:'save'}})}});
 assert.equal(calls[1].action,'save');assert(calls[1].args.settings.packs);
 config._settings=JSON.parse(JSON.stringify(data));config._pack='halloween';config._scene='castle';
 config._settings.shuffle_scenes=[{pack_id:'halloween',scene_id:'castle'}];
 await config._click({target:{closest:()=>({dataset:{action:'remove-scene'}})}});
 assert.equal(config._settings.shuffle_scenes.length,0,'deleted scenes must leave the shuffle pool');
 console.log('PASS: operation/configuration separation, tab guards and separate save payloads');
})().catch(e=>{console.error(e);process.exit(1)});
