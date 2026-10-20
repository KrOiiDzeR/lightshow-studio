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
const registered=classes.get('lightshow-studio'),render=registered.prototype._render;
vm.runInNewContext(js,context);vm.runInNewContext(js,context);
assert.equal(classes.get('lightshow-studio'),registered);
assert.equal(registered.prototype._render,render,'repeated loads must not replace the current render method with a recursive delegate');
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
 config._tab=tab;config._render();assert(config.shadowRoot.innerHTML.includes('Konfiguration'));
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
 // Explicit HA fixtures must stay HA even when discovery finds a Z2M match.
 config._settings.fixtures=[{entity_id:'light.ha',role:'other',friendly_name:'',endpoint:'auto',enabled:true,transport:'homeassistant'}];
 config._hass.states={
  'light.ha':{state:'on',attributes:{friendly_name:'Shelly RGBW',supported_color_modes:['rgbw']}},
  'light.zigbee':{state:'on',attributes:{friendly_name:'Zigbee',supported_color_modes:['rgb']}},
  'light.wifi':{state:'on',attributes:{friendly_name:'WLAN RGBWW',supported_color_modes:['rgbww']}}
 };
 config._data.suggestions={'light.ha':'matched-but-HA','light.zigbee':'zigbee-device'};
 config._data.configuration={areas:[]};
 assert(config._entitiesOptions('light.zigbee','zigbee2mqtt').includes('light.zigbee'));
 assert(!config._entitiesOptions('light.zigbee','zigbee2mqtt').includes('light.wifi'));
 assert(config._entitiesOptions('light.ha','homeassistant').includes('light.wifi'));
 config._tab='lights';config._render();
 assert(config.shadowRoot.innerHTML.includes('RGBW'));
 assert(!config.shadowRoot.innerHTML.includes('data-field="fixture-friend"'));
 await config._click({target:{closest:()=>({dataset:{action:'automap'}})}});
 assert.equal(config._settings.fixtures[0].transport,'homeassistant');
 assert.equal(config._settings.fixtures[0].friendly_name,'');
 config._addTransport='zigbee2mqtt';
 await config._click({target:{closest:()=>({dataset:{action:'add-fixture'}})}});
 assert.equal(config._settings.fixtures[1].entity_id,'light.zigbee');
 assert.equal(config._settings.fixtures[1].transport,'zigbee2mqtt');
 config._addTransport='homeassistant';
 await config._click({target:{closest:()=>({dataset:{action:'add-fixture'}})}});
 assert.equal(config._settings.fixtures[2].entity_id,'light.wifi');
 assert.equal(config._settings.fixtures[2].transport,'homeassistant');
 assert.equal(config._settings.fixtures[2].role,'upper','normal lights must start on the active main track');
 config._hass.states['switch.relay_lamp']={state:'on',attributes:{friendly_name:'Relay lamp'}};
 assert(!config._entitiesOptions('light.ha','homeassistant').includes('switch.relay_lamp'));
 config._addTransport='switch';
 await config._click({target:{closest:()=>({dataset:{action:'add-fixture'}})}});
 assert.equal(config._settings.fixtures.at(-1).entity_id,'switch.relay_lamp');
 assert.equal(config._settings.fixtures.at(-1).transport,'homeassistant');
 assert.equal(config._settings.fixtures.at(-1).role,'upper');
 assert(config._entitiesOptions('switch.relay_lamp','homeassistant').includes('switch.relay_lamp'));
 assert(!config._entitiesOptions('switch.relay_lamp','homeassistant').includes('light.wifi'));
 config._settings.fixtures.forEach(f=>f.role='other');
 config._sceneObj().tracks.other.mode='off';
 assert(config._routingSummary().includes('Aus-Szene'));
 config._data.connection={mqtt_mode:'disabled',mqtt_base_topic:''};
 config._change({target:{dataset:{field:'show-sidebar'},checked:false}});
 assert.equal(config._connectionDraft.show_sidebar,false);
 const wire=[];config._area='second_area';config._hass.callWS=async msg=>{wire.push(msg);return {};};
 await classes.get('lightshow-studio').prototype._ws.call(config,'connection',{connection:config._connectionDraft});
 assert(!Object.hasOwn(wire[0],'area_id'),'global connection settings must not include a selected area');
 await classes.get('lightshow-studio').prototype._ws.call(config,'get');
 assert.equal(wire[1].area_id,'second_area','area-specific requests must retain the area');
 console.log('PASS: operation/configuration separation, tab guards and separate save payloads');
})().catch(e=>{console.error(e);process.exit(1)});
