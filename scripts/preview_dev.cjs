const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'docs');
const js=fs.readFileSync(path.join(root,'custom_components/lightshow_studio/static/lightshow-studio.js'),'utf8');
const data=JSON.parse(fs.readFileSync(path.join(root,'tests/defaults-fixture.json'),'utf8'));
data.fixtures=data.fixtures.slice(0,2);data.fixtures.forEach((f,i)=>{f.entity_id='light.demo_'+i;f.friendly_name='Demo-Wandleuchte';f.role=i?'lower':'upper';f.endpoint=i?'bottom':'top';f.transport='zigbee2mqtt';});
const html=`<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lightshow Studio · lokale Entwicklungsvorschau</title>
<style>body{margin:24px;background:#1c1c1c;color:#eee;font:14px Arial;--primary-text-color:#eee;--secondary-text-color:#aaa;--ha-card-background:#252525;--divider-color:#454545;--error-color:#d93b4c;--success-color:#3d9866;--ls-color-scheme:dark}main{max-width:1012px;margin:auto}.demo{font-size:13px;margin:0 auto 18px;max-width:1012px;line-height:1.6}.demo button{padding:9px 15px;background:#333;color:#eee;border:1px solid #777;border-radius:7px;cursor:pointer}</style>
<div class="demo"><strong>Lokale Entwicklungsvorschau · 2.2 · gemischte Lampen</strong><br>Beispieldaten. Keine Verbindung zu Home Assistant oder echten Lampen.<br><button id="operation">Bedienung / Dashboard</button> <button id="configuration">Integration einrichten</button></div><main></main>
<script>${js}</script><script>
const clone=x=>JSON.parse(JSON.stringify(x));window.requests=[];
const original=${JSON.stringify(data)};
let configuration={schema:3,areas:[['wall','Außenwand','🏠',0],['garden','Garten','🌿',2],['bath','Badewanne','🛁',3],['pool','Pool','🏊',4]].map(([id,name,icon,n])=>{const settings=clone(original);settings.fixtures=id==='wall'?settings.fixtures:[{...settings.fixtures[0],entity_id:'light.demo_'+n,role:'other',endpoint:'auto',friendly_name:'',transport:'homeassistant'}];return {id,name,icon,settings};})};
let demoAreaSerial=0;
let connection={mqtt_mode:'auto',mqtt_base_topic:''};
const idle=()=>({running:false,pack_id:'',scene_id:'',program_id:'',source:'manual',previewing:[],warnings:[]});
let states=Object.fromEntries(configuration.areas.map(a=>[a.id,idle()]));
const getData=(key)=>{const a=configuration.areas.find(a=>a.id===key)||configuration.areas[0];return {area_id:a.id,settings:clone(a.settings),configuration:clone(configuration),connection:clone(connection),devices:[{friendly_name:'Demo-Wandleuchte',model:'046677585235'},{friendly_name:'Demo-Zigbee',model:'Demo'}],suggestions:{'light.demo_0':'Demo-Wandleuchte','light.demo_1':'Demo-Wandleuchte','light.zigbee_demo':'Demo-Zigbee'},status:clone(states[a.id]),areas:configuration.areas.map(a=>{const st=states[a.id],pack=a.settings.packs.find(p=>p.id===st.pack_id),scene=pack?.scenes.find(s=>s.id===st.scene_id),program=pack?.programs.find(p=>p.id===st.program_id);return {id:a.id,name:a.name,icon:a.icon,running:st.running,previewing:false,warnings:[],source:st.source,lights:a.settings.fixtures.filter(f=>f.enabled).length,pack:pack?.name||'',scene:scene?.name||'',program:program?.name||''};})};};
const hass={states:Object.fromEntries([...configuration.areas.flatMap(a=>a.settings.fixtures.map(f=>[f.entity_id,{state:'off',attributes:{friendly_name:a.name+' · '+f.entity_id}}])),['light.free_demo',{state:'off',attributes:{friendly_name:'Neue Demolampe'}}]]),async callWS(msg){requests.push(clone(msg));const action=msg.type.split('/')[1];let key=msg.area_id||configuration.areas[0].id;let a=configuration.areas.find(a=>a.id===key);
 if(action==='areas'){
  if(msg.action==='add'){do{key='area_demo_'+(++demoAreaSerial);}while(configuration.areas.some(a=>a.id===key));const settings=clone(original);settings.fixtures=[];configuration.areas.push({id:key,name:msg.name,icon:msg.icon||'💡',settings});states[key]=idle();}
  if(msg.action==='copy'){do{key='area_demo_'+(++demoAreaSerial);}while(configuration.areas.some(a=>a.id===key));const settings=clone(a.settings);settings.fixtures=[];for(const p of settings.packs){p.schedule.enabled=false;for(const sc of p.scenes)sc.overrides=[];}for(const w of settings.weekly||[])w.enabled=false;configuration.areas.push({id:key,name:msg.name,icon:msg.icon||'💡',settings});states[key]=idle();}
  if(msg.action==='rename'){a.name=msg.name;a.icon=msg.icon;}
  if(msg.action==='remove'){configuration.areas=configuration.areas.filter(a=>a.id!==key);delete states[key];key=configuration.areas[0].id;}
  if(msg.action==='restore'){configuration=clone(msg.configuration);states=Object.fromEntries(configuration.areas.map(a=>[a.id,idle()]));key=configuration.areas[0].id;}
 }
 if(action==='save')a.settings=clone(msg.settings);
 if(action==='operate'){a.settings.options=clone(msg.changes.options);a.settings.weekly=clone(msg.changes.weekly);for(const p of a.settings.packs)p.schedule=clone(msg.changes.schedules[p.id]);}
 if(action==='connection'){connection=clone(msg.connection);return {saved:true,connection:clone(connection)};}
 if(action==='start'||action==='start_program'){states[key].running=true;states[key].pack_id=msg.pack_id;states[key].scene_id=msg.scene_id||a.settings.packs.find(p=>p.id===msg.pack_id).programs.find(p=>p.id===msg.program_id).steps[0].scene_id;states[key].program_id=msg.program_id||'';}
 if(action==='stop'){states[key]=idle();}
 if(action==='control'){
  if(msg.action==='favorite'){const pair={pack_id:msg.pack_id,scene_id:msg.scene_id};a.settings.favorites=a.settings.favorites||[];const idx=a.settings.favorites.findIndex(f=>f.pack_id===pair.pack_id&&f.scene_id===pair.scene_id);if(idx<0)a.settings.favorites.push(pair);else a.settings.favorites.splice(idx,1);}
  if(msg.action==='timer'){if(msg.minutes&&!states[key].running)throw Error('Bitte zuerst die Show starten');states[key].stop_at=msg.minutes?Date.now()/1000+msg.minutes*60:null;}
  if(msg.action==='start_selected'){for(const id of msg.area_ids){const target=configuration.areas.find(a=>a.id===id);if(!target?.settings.packs.some(p=>p.id===msg.pack_id&&p.scenes.some(sc=>sc.id===msg.scene_id)))throw Error('Szene fehlt in einem gewählten Bereich');}for(const id of msg.area_ids)Object.assign(states[id],{running:true,pack_id:msg.pack_id,scene_id:msg.scene_id,program_id:''});}
  if(msg.action==='stop_selected')for(const id of msg.area_ids)states[id]=idle();
 }
 return getData(key);
}};
Object.assign(hass.states,{
 'light.free_demo':{state:'off',attributes:{friendly_name:'Neue Demolampe',supported_color_modes:['rgb']}},
 'light.shelly_rgbw':{state:'on',attributes:{friendly_name:'Shelly · RGBW-Streifen',supported_color_modes:['rgbw']}},
 'light.wifi_rgbww':{state:'on',attributes:{friendly_name:'WLAN · RGBWW-Poollicht',supported_color_modes:['rgbww']}},
 'light.zigbee_demo':{state:'off',attributes:{friendly_name:'Zigbee · Gartenleuchte',supported_color_modes:['xy']}}
});
for(const [id,s] of Object.entries(hass.states))if(!s.attributes.supported_color_modes)s.attributes.supported_color_modes=[id==='light.demo_2'?'rgbw':id==='light.demo_3'?'color_temp':id==='light.demo_4'?'rgbww':'rgb'];
window.demoData=getData;
window.setInterval(()=>{for(const [key,s] of Object.entries(states))if(s.running&&s.stop_at&&Date.now()/1000>=s.stop_at)states[key]=idle();},1000);

window.show=function(mode){document.querySelector('main').replaceChildren();const card=document.createElement(mode==='configuration'?'lightshow-studio-configuration':'lightshow-studio');card.hass=hass;card.setConfig({background:'transparent'});document.querySelector('main').append(card);window.card=card;};
document.querySelector('#operation').onclick=()=>show('operation');document.querySelector('#configuration').onclick=()=>show('configuration');show('operation');
</script></html>`;
fs.writeFileSync(path.join(out,'dev-preview.html'),html);
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||undefined});
 const page=await browser.newPage({viewport:{width:1060,height:1080}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+path.join(out,'dev-preview.html').replace(/\\/g,'/'));
 await page.getByRole('tab',{name:'🎬 Shows',exact:true}).waitFor();
 assert.equal(await page.getByRole('tab',{name:'💡 Lampen',exact:true}).count(),0);
 await page.getByRole('switch',{name:/Zufälliger Szenenwechsel/}).check();
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.equal(await page.evaluate(()=>requests.at(-1).type),'lightshow_studio/operate');
 // Exercise the new controls and folder behavior with ordinary browser input.
 await page.getByRole('button',{name:'5 Min.',exact:true}).click();
 assert.equal(await page.getByRole('slider',{name:'Szenenwechsel-Intervall',exact:true}).inputValue(),'300');
 await page.getByRole('slider',{name:'Szenenwechsel-Intervall',exact:true}).press('ArrowRight');
 await page.getByRole('switch',{name:'Sanfte Windböen',exact:true}).check();
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.equal(await page.evaluate(()=>requests.at(-1).changes.options.shuffle_interval),330);
 assert.equal(await page.evaluate(()=>requests.at(-1).changes.options.wind),true);
 await page.locator('details[data-folder="show-programs"] > summary').click();
 await page.getByRole('button',{name:'👻 Geisterhaus Lichtszene',exact:true}).click();
 assert.equal(await page.locator('details[data-folder="show-programs"]').getAttribute('open'),null);
 await page.locator('details[data-folder="show-programs"] > summary').click();
 await page.getByRole('tab',{name:'🎬 Shows',exact:true}).press('ArrowRight');
 assert.equal(await page.getByRole('tab',{name:'🕓 Zeitplan',exact:true}).getAttribute('aria-selected'),'true');
 await page.getByRole('tab',{name:'🕓 Zeitplan',exact:true}).press('ArrowLeft');
 assert.equal(await page.getByRole('tab',{name:'🎬 Shows',exact:true}).getAttribute('aria-selected'),'true');
 await page.screenshot({path:path.join(out,'dev-design-folders.png'),fullPage:true});
 await page.locator('details[data-folder="show-effects"]').screenshot({path:path.join(out,'dev-design-effects.png')});
 await page.getByRole('button',{name:'▶ Show starten',exact:true}).click();
 await page.getByRole('button',{name:'Bereich Garten auswählen',exact:true}).click();
 await page.getByRole('button',{name:'🌿 Ambiente & Jahreszeiten',exact:true}).click();
 await page.getByRole('button',{name:'▶ Show starten',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('garden').areas.filter(a=>a.running).length),2);
 await page.screenshot({path:path.join(out,'dev-parallel-areas.png'),fullPage:true});
 await page.getByRole('button',{name:'■ Stopp & zurücksetzen',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('garden').areas.find(a=>a.id==='wall').running),true);
 assert.equal(await page.evaluate(()=>demoData('garden').areas.find(a=>a.id==='garden').running),false);
 await page.getByRole('button',{name:'Bereich Außenwand auswählen',exact:true}).click();
 await page.getByRole('button',{name:'■ Stopp & zurücksetzen',exact:true}).click();
 await page.screenshot({path:path.join(out,'dev-dashboard-dark.png'),fullPage:true});
 await page.getByRole('tab',{name:'🕓 Zeitplan',exact:true}).click();
 await page.getByRole('button',{name:'＋ Wochenzeit hinzufügen',exact:true}).click();
 await page.getByLabel('Mo',{exact:true}).uncheck();await page.getByLabel('Sa',{exact:true}).check();
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.deepEqual(await page.evaluate(()=>requests.at(-1).changes.weekly[0].days),[1,2,3,4,5]);
 await page.screenshot({path:path.join(out,'dev-weekly-dark.png'),fullPage:true});
 await page.getByRole('button',{name:'Integration einrichten',exact:true}).click();
 await page.getByRole('tab',{name:'🔀 Shuffle',exact:true}).click();
 await page.getByRole('button',{name:'Auswahl leeren',exact:true}).click();
 await page.getByRole('switch',{name:'Halloween · Gruselschloss',exact:true}).check();
 await page.getByRole('switch',{name:'Ambiente & Jahreszeiten · Sommernacht',exact:true}).check();
 await page.getByRole('switch',{name:'Halloween · Gruselschloss',exact:true}).uncheck();
 assert.equal(await page.getByRole('switch',{name:'Halloween · Gruselschloss',exact:true}).isChecked(),false);
 await page.getByRole('switch',{name:'Halloween · Gruselschloss',exact:true}).check();
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.deepEqual(await page.evaluate(()=>demoData('wall').settings.shuffle_scenes.map(r=>r.pack_id+'/'+r.scene_id).sort()),['ambience/summer','halloween/castle']);
 await page.locator('details[data-folder="shuffle-pack-christmas"] > summary').click();
 await page.locator('details[data-folder="shuffle-pack-party"] > summary').click();
 await page.getByRole('tabpanel',{name:'Shuffle',exact:true}).screenshot({path:path.join(out,'dev-shuffle-selection.png')});
 await page.setViewportSize({width:390,height:900});
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
 await page.setViewportSize({width:1060,height:1080});
 await page.getByRole('button',{name:'Bereich Garten auswählen',exact:true}).click();
 assert.equal(await page.evaluate(()=>Object.hasOwn(demoData('garden').settings,'shuffle_scenes')),false);
 await page.getByRole('button',{name:'Bereich Außenwand auswählen',exact:true}).click();
 assert.equal(await page.getByRole('switch',{name:'Ambiente & Jahreszeiten · Sommernacht',exact:true}).isChecked(),true);
 await page.getByRole('tab',{name:'🔌 Verbindung',exact:true}).click();
 await page.getByLabel('Geräteerkennung').selectOption('manual');
 await page.getByLabel('MQTT-Basisthema').fill('Home/Zigbee');
 await page.getByRole('button',{name:'Verbindung übernehmen',exact:true}).click();
 assert.equal(await page.evaluate(()=>requests.findLast(r=>r.type==='lightshow_studio/connection').connection.mqtt_base_topic),'Home/Zigbee');
 await page.screenshot({path:path.join(out,'dev-connection-dark.png'),fullPage:true});
 await page.getByRole('tab',{name:'💡 Lampen',exact:true}).click();
 await page.screenshot({path:path.join(out,'dev-configuration-dark.png'),fullPage:true});
 for(const tab of ['🎛️ Editor','📦 Pakete']){await page.getByRole('tab',{name:tab,exact:true}).click();assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));}
 await page.getByRole('button',{name:'⇧ Gesamte Konfiguration exportieren',exact:true}).click();
 assert.equal(JSON.parse(await page.getByLabel('Konfiguration (JSON)',{exact:true}).inputValue()).schema,3);
 await page.getByRole('tab',{name:'🏡 Bereiche',exact:true}).click();
 // Embedded browsers may suppress native dialogs. The area workflow must not use them.
 await page.evaluate(()=>{window.prompt=()=>{throw Error('Native prompt unavailable');};window.confirm=()=>{throw Error('Native confirm unavailable');};});
 await page.getByRole('button',{name:'＋ Bereich anlegen',exact:true}).click();
 await page.getByRole('button',{name:'✓ Bereich erstellen',exact:true}).click();
 assert.equal(await page.getByRole('alert').innerText(),'Bitte gib deinem Bereich einen Namen.');
 await page.getByLabel('Name des neuen Bereichs',{exact:true}).fill('Testbereich');
 await page.getByLabel('Symbol des neuen Bereichs',{exact:true}).fill('🌴');
 assert.equal(await page.getByRole('alert').count(),0);
 await page.screenshot({path:path.join(out,'dev-area-create-form.png'),fullPage:true});
 await page.getByLabel('Name des neuen Bereichs',{exact:true}).press('Enter');
 assert.equal(await page.getByRole('button',{name:'Bereich Testbereich auswählen',exact:true}).count(),1);
 await page.locator('details[data-folder="area-overview"]').screenshot({path:path.join(out,'dev-area-created.png')});
 await page.getByRole('button',{name:'Bedienung / Dashboard',exact:true}).click();
 await page.getByRole('button',{name:'Bereich Testbereich auswählen',exact:true}).click();
 assert.equal(await page.getByRole('button',{name:'Bereich Testbereich auswählen',exact:true}).getAttribute('aria-pressed'),'true');
 await page.getByRole('button',{name:'Integration einrichten',exact:true}).click();
 await page.getByRole('button',{name:'Bereich Testbereich auswählen',exact:true}).click();
 await page.getByRole('tab',{name:'💡 Lampen',exact:true}).click();
 await page.getByRole('button',{name:'＋ Lampe hinzufügen',exact:true}).click();
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('area_demo_1').settings.fixtures[0].entity_id),'light.free_demo');
 await page.getByRole('tab',{name:'🏡 Bereiche',exact:true}).click();
 await page.getByLabel('Bereichsname',{exact:true}).fill('Gästezimmer');
 await page.getByLabel('Bereichssymbol',{exact:true}).fill('🛏️');
 await page.getByRole('button',{name:'Bereich übernehmen',exact:true}).click();
 assert.equal(await page.getByRole('button',{name:'Bereich Gästezimmer auswählen',exact:true}).count(),1);
 await page.getByRole('button',{name:'− Bereich löschen',exact:true}).click();
 await page.getByRole('button',{name:'Behalten',exact:true}).click();
 assert.equal(await page.getByRole('button',{name:'Bereich Gästezimmer auswählen',exact:true}).count(),1);
 await page.getByRole('button',{name:'− Bereich löschen',exact:true}).click();
 await page.getByRole('button',{name:'Ja, Bereich löschen',exact:true}).click();
 await page.getByRole('button',{name:'＋ Bereich anlegen',exact:true}).click();
 await page.getByLabel('Name des neuen Bereichs',{exact:true}).fill('Abbrechen-Test');
 await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
 assert.equal(await page.getByRole('button',{name:'Bereich Abbrechen-Test auswählen',exact:true}).count(),0);
 assert.equal(await page.getByRole('button',{name:'Bereich Gästezimmer auswählen',exact:true}).count(),0);
 await page.screenshot({path:path.join(out,'dev-area-configuration.png'),fullPage:true});
 await page.getByRole('button',{name:'Bedienung / Dashboard',exact:true}).click();
 await page.setViewportSize({width:390,height:900});
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
 await page.screenshot({path:path.join(out,'dev-mobile-dark.png'),fullPage:true});
 await page.setViewportSize({width:1060,height:1080});
 await page.addStyleTag({content:'body{background:#f2f4f6;color:#222;--primary-text-color:#222;--secondary-text-color:#666;--ha-card-background:#fff;--divider-color:#ddd;--ls-color-scheme:light}'});
 await page.screenshot({path:path.join(out,'dev-dashboard-light.png'),fullPage:true});
 assert.equal(await page.evaluate(()=>getComputedStyle(card.shadowRoot.querySelector('.studio')).backgroundColor),'rgba(0, 0, 0, 0)');
 // Mixed sources: HA inventory includes every light, Z2M inventory is filtered.
 await page.getByRole('button',{name:'Integration einrichten',exact:true}).click();
 await page.getByRole('button',{name:'Bereich Garten auswählen',exact:true}).click();
 await page.getByRole('tab',{name:'💡 Lampen',exact:true}).click();
 assert.equal(await page.locator('[data-field="fixture-friend"]').count(),0);
 assert((await page.locator('[data-field="fixture-entity"]').innerText()).includes('Shelly'));
 assert((await page.locator('[data-field="fixture-entity"]').innerText()).includes('RGBWW'));
 await page.getByLabel('Lampenquelle',{exact:true}).selectOption('zigbee2mqtt');
 await page.getByRole('button',{name:'＋ Lampe hinzufügen',exact:true}).click();
 assert.equal(await page.locator('[data-field="fixture-entity"][data-index="1"]').inputValue(),'light.zigbee_demo');
 assert(!(await page.locator('[data-field="fixture-entity"][data-index="1"]').innerText()).includes('Shelly'));
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('garden').settings.fixtures[1].transport),'zigbee2mqtt');
 await page.getByLabel('Lampenquelle',{exact:true}).selectOption('homeassistant');
 await page.getByRole('button',{name:'＋ Lampe hinzufügen',exact:true}).click();
 await page.locator('[data-field="fixture-entity"][data-index="2"]').selectOption('light.shelly_rgbw');
 await page.getByRole('button',{name:'＋ Lampe hinzufügen',exact:true}).click();
 await page.locator('[data-field="fixture-entity"][data-index="3"]').selectOption('light.wifi_rgbww');
 await page.getByRole('button',{name:'↻ Erkennen',exact:true}).click();
 assert.equal(await page.locator('[data-field="fixture-friend"]').count(),1);
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.deepEqual(await page.evaluate(()=>demoData('garden').settings.fixtures.map(f=>f.transport)),['homeassistant','zigbee2mqtt','homeassistant','homeassistant']);
 await page.screenshot({path:path.join(out,'dev-mixed-lights-light.png'),fullPage:true});
 await page.addStyleTag({content:'body{background:#1c1c1c;color:#eee;--primary-text-color:#eee;--secondary-text-color:#aaa;--ha-card-background:#252525;--divider-color:#454545;--ls-color-scheme:dark}'});
 await page.screenshot({path:path.join(out,'dev-mixed-lights-dark.png'),fullPage:true});
 await page.setViewportSize({width:390,height:900});
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
 await page.screenshot({path:path.join(out,'dev-mixed-lights-mobile.png'),fullPage:true});
 // Daily controls through real DOM input and the demo websocket adapter.
 await page.setViewportSize({width:1060,height:1080});
 await page.getByRole('button',{name:'Bedienung / Dashboard',exact:true}).click();
 await page.getByRole('button',{name:'☆ Gewählte Szene merken',exact:true}).click();
 assert.equal(await page.getByRole('button',{name:'★ Aus Favoriten entfernen',exact:true}).count(),1);
 await page.locator('[data-action="favorite-start"]').click();
 assert.equal(await page.evaluate(()=>demoData('wall').status.running),true);
 await page.getByRole('button',{name:'30 Min. Timer',exact:true}).click();
 assert((await page.evaluate(()=>demoData('wall').status.stop_at))>Date.now()/1000);
 await page.getByRole('button',{name:'Timer entfernen',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('wall').status.stop_at),null);
 await page.getByRole('checkbox',{name:'Außenwand gemeinsam bedienen',exact:true}).check();
 await page.getByRole('checkbox',{name:'Garten gemeinsam bedienen',exact:true}).check();
 await page.getByRole('button',{name:'▶ Markierte Bereiche starten',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('garden').status.running),true);
 await page.getByRole('button',{name:'■ Markierte Bereiche stoppen',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('wall').status.running||demoData('garden').status.running),false);
 await page.getByRole('switch',{name:'Shuffle ohne Wiederholungen',exact:true}).uncheck();
 await page.getByLabel('Übergang in Sekunden',{exact:true}).fill('3');
 await page.getByLabel('Übergang in Sekunden',{exact:true}).press('Tab');
 await page.getByRole('button',{name:'✓ Speichern',exact:true}).click();
 assert.equal(await page.evaluate(()=>demoData('wall').settings.options.transition),3);
 assert.equal(await page.evaluate(()=>demoData('wall').settings.options.shuffle_no_repeat),false);
 await page.screenshot({path:path.join(out,'dev-daily-controls.png'),fullPage:true});
 await page.setViewportSize({width:390,height:900});
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
 await page.screenshot({path:path.join(out,'dev-daily-mobile.png'),fullPage:true});
 await page.setViewportSize({width:1060,height:1080});
 await page.getByRole('button',{name:'Integration einrichten',exact:true}).click();
 await page.getByRole('button',{name:'⧉ Bereich kopieren',exact:true}).click();
 assert.equal(await page.getByRole('button',{name:'Bereich Außenwand (Kopie) auswählen',exact:true}).count(),1);
 assert.equal(await page.evaluate(()=>demoData(card._area).settings.fixtures.length),0);
 await page.screenshot({path:path.join(out,'dev-area-copy.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 // Reproduce an old manual Lovelace resource loading before the new HA module.
 for(const version of ['v2','v2.1']){
  const legacyPage=await browser.newPage();
  const legacyErrors=[];legacyPage.on('pageerror',e=>legacyErrors.push(e.message));
  const legacy=fs.readFileSync(path.join(root,'tests','legacy-card-'+version+'.js'),'utf8');
  await legacyPage.addScriptTag({type:'module',content:legacy});
  await legacyPage.setContent(html.replace('<script>'+js+'</script>',''));
  await legacyPage.getByRole('button',{name:'▶ Show starten',exact:true}).waitFor();
  await legacyPage.addScriptTag({type:'module',content:js});
  await legacyPage.evaluate(()=>{card.hass=hass;});
  await legacyPage.getByRole('button',{name:'☆ Gewählte Szene merken',exact:true}).waitFor();
  assert.equal(await legacyPage.getByRole('tab',{name:'💡 Lampen',exact:true}).count(),0);
  await legacyPage.getByRole('button',{name:'☆ Gewählte Szene merken',exact:true}).click();
  assert.equal(await legacyPage.getByRole('button',{name:'★ Aus Favoriten entfernen',exact:true}).count(),1);
  await legacyPage.getByRole('button',{name:'Integration einrichten',exact:true}).click();
  await legacyPage.getByRole('tab',{name:'💡 Lampen',exact:true}).click();
  await legacyPage.getByLabel('Lampenquelle',{exact:true}).waitFor();
  await legacyPage.getByRole('button',{name:'Bedienung / Dashboard',exact:true}).click();
  await legacyPage.getByRole('button',{name:'★ Aus Favoriten entfernen',exact:true}).waitFor();
  assert.deepEqual(legacyErrors,[]);
  await legacyPage.close();
 }
 await browser.close();console.log('PASS: legacy v2/v2.1 frontend migration without YAML edits; mixed sources, favorites, area batches, timer, shuffle rounds, transitions, copy, existing flows, mobile and themes');
})().catch(e=>{console.error(e);process.exit(1)});
