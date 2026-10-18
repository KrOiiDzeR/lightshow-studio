/* Lightshow Studio 2.0 beta — self contained Home Assistant Lovelace card.
 * Event packs are ordinary JSON objects; no JS changes required to add packs.
 */
const LS_ROLES = [['upper','⬆️ Oben'],['lower','⬇️ Unten'],['entrance','🚪 Haustür'],['other','💡 Andere']];
const LS_MODES = [
 ['candle','🕯️ Kerzenflackern'],['fireplace','🔥 Kaminfeuer'],['sparkle','✨ Funkeln'],
 ['breathe','🌫️ Atmen'],['blink','⚡ Blinken'],['colorloop','🌈 Farbwechsel'],
 ['sunset','🌇 Sonnenuntergang'],['sunrise','🌅 Sonnenaufgang'],['opal','💎 Opal'],
 ['glisten','💫 Glitzern'],['underwater','🌊 Unterwasser'],['cosmos','🌌 Kosmos'],
 ['sunbeam','☀️ Sonnenstrahl'],['enchant','🪄 Verzaubern'],
 ['red','🔴 Rot'],['purple','🟣 Violett'],['green','🟢 Grün'],
 ['warm','🟠 Warmweiß'],['gold','🟡 Gold'],['blue','🔵 Blau'],['ice','🧊 Eisblau'],
 ['white','⚪ Weiß'],['custom_color','🎨 Eigene Farbe'],['off','🌑 Aus']
];
const LS_ESC = v => String(v ?? '').replace(/[&<>"']/g, x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const LS_COPY = data => JSON.parse(JSON.stringify(data));
const LS_CUE = () => ({mode:'candle',brightness:65,speed:55,color:'#FF8730'});
const LS_COLORS = {halloween:'#f69e42',christmas:'#5bc49c',party:'#b596ff',ambience:'#8cd4db'};
const LS_DEF = (role) => role==='upper'?'top':role==='lower'?'bottom':'auto';

class LightshowStudio extends HTMLElement {
 constructor(){
   super(); this.attachShadow({mode:'open'}); this._data=null; this._settings=null;
   this._tab='shows'; this._pack='halloween'; this._scene='castle'; this._dirty=false;
   this._busy=false;this._loading=false;this._error='';this._info='';this._importOpen=false;this._exportOpen=false;
   this._migratedShown=false;this._importText='';
 }
 setConfig(config){
   if(config?.background && !['transparent','theme'].includes(config.background))throw Error('background: transparent oder theme verwenden');
   this._config=config||{};this._render();
 }
 getCardSize(){return this._tab==='editor'?15:9;}
 set hass(h){this._hass=h;if(this.isConnected&&!this._data&&!this._busy)this._load();}
 connectedCallback(){this._render();if(this._hass&&!this._data)this._load();this._timer=window.setInterval(()=>{if(!this._busy&&this._hass)this._load(true);},8500);
   this.shadowRoot.addEventListener('click',e=>this._click(e));
   this.shadowRoot.addEventListener('change',e=>this._change(e));
   this.shadowRoot.addEventListener('input',e=>this._input(e));
 }
 disconnectedCallback(){if(this._timer)window.clearInterval(this._timer);}
 async _ws(action, extra={}){if(!this._hass)throw Error('Keine Home Assistant-Verbindung');return this._hass.callWS({type:`lightshow_studio/${action}`,...extra});}
 async _load(statusOnly=false){
   if(this._busy||this._loading)return;this._loading=true;
   try{const data=await this._ws('get');this._data=data;
     if(this._dirty&&statusOnly)return;
     if(!this._dirty){this._settings=LS_COPY(data.settings);this._ensureSelected();}
     this._error='';this._render();
   }catch(err){this._error=err?.message||String(err);this._render();}finally{this._loading=false;}
 }
 _ensureSelected(){
   if(!this._settings?.packs?.length)return;
   if(!this._settings.packs.some(p=>p.id===this._pack))this._pack=this._settings.packs[0].id;
   if(!this._packObj()?.scenes.some(s=>s.id===this._scene))this._scene=this._packObj().scenes[0].id;
 }
 _packObj(){return this._settings?.packs.find(p=>p.id===this._pack);}
 _sceneObj(){return this._packObj()?.scenes.find(s=>s.id===this._scene);}
 _entities(){const ls=Object.entries(this._hass?.states||{}).filter(([id])=>id.startsWith('light.')).map(([id,s])=>({id,name:s.attributes.friendly_name||id}));
   for(const f of this._settings?.fixtures||[])if(!ls.some(x=>x.id===f.entity_id))ls.push({id:f.entity_id,name:`${f.entity_id} (offline)`});
   return ls.sort((a,b)=>a.name.localeCompare(b.name,'de'));
 }
 _options(arr,value,placeholder=''){return (placeholder?`<option value="">${LS_ESC(placeholder)}</option>`:'')+arr.map(([v,label])=>`<option value="${LS_ESC(v)}" ${String(v)===String(value)?'selected':''}>${LS_ESC(label)}</option>`).join('');}
 _entitiesOptions(id){return this._options(this._entities().map(x=>[x.id,x.name+' · '+x.id]),id,'Lampe auswählen');}
 _devicesOptions(name){return this._options((this._data?.devices||[]).map(d=>[d.friendly_name,d.friendly_name]),name,'Automatisch erkennen');}
 _cueControls(cue,kind,index){const opts=this._options(LS_MODES,cue.mode);return `<div class="cuegrid">
   <label>Effekt <select data-field="cue-mode" data-kind="${kind}" data-index="${index}">${opts}</select></label>
   <label>Helligkeit <div class="value">${cue.brightness}%</div><input data-field="brightness" data-kind="${kind}" data-index="${index}" type="range" min="0" max="100" step="5" value="${cue.brightness}"></label>
   <label>Tempo <div class="value">${cue.speed}%</div><input data-field="speed" data-kind="${kind}" data-index="${index}" type="range" min="0" max="100" step="5" value="${cue.speed}"></label>
   ${cue.mode==='custom_color'?`<label>Farbe <input data-field="cue-color" data-kind="${kind}" data-index="${index}" type="color" value="${LS_ESC(cue.color)}"></label>`:''}
  </div>`;}
 _tabs(){return [['shows','🎬 Shows'],['lights','💡 Lampen'],['editor','🎛️ Editor'],['schedule','🕓 Zeitplan'],['library','📦 Pakete']].map(([id,label])=>`<button class="navbtn ${this._tab===id?'selected':''}" data-action="tab" data-id="${id}">${label}</button>`).join('');}
 _packSelector(){return `<div class="packselect">${this._settings.packs.map(p=>`<button class="packpill ${p.id===this._pack?'sel':''}" data-action="pack" data-id="${LS_ESC(p.id)}">${LS_ESC(p.icon)} ${LS_ESC(p.name)}</button>`).join('')}</div>`;}
 _renderShows(){const pack=this._packObj(), st=this._data.status;return `<div class="titleline"><div><h3>${LS_ESC(pack.icon)} ${LS_ESC(pack.name)}</h3><p>${LS_ESC(pack.description)}</p></div></div>
 <div class="scenes">${pack.scenes.map(s=>`<button class="scene ${s.id===this._scene?'active':''}" data-action="scene" data-id="${LS_ESC(s.id)}"><span class="bigemoji">${LS_ESC(s.icon)}</span><strong>${LS_ESC(s.name)}</strong><small>${LS_ESC(s.description||'Lichtszene')}</small></button>`).join('')}</div>
 <div class="controlbox"><div><strong>${st.running?'● Show läuft':'○ Bereit zum Start'}</strong><p>${st.running?LS_ESC(this._settings.packs.find(p=>p.id===st.pack_id)?.name||st.pack_id)+' / '+LS_ESC(st.scene_id):'Starte die ausgewählte Szene – alte Lichtzustände werden soweit möglich gemerkt.'}</p></div>
 <div class="actions"><button class="primary" data-action="start" ${this._busy||this._dirty?'disabled':''}>▶ ${st.running?'Szene wechseln':'Show starten'}</button><button class="stop" data-action="stop" ${this._busy||!st.running?'disabled':''}>■ Stopp & zurücksetzen</button></div></div>
 <h4 class="overridesTitle">🎞️ Komplette Show-Abläufe</h4>
 <p class="small muted">Mehrere Szenen laufen automatisch nacheinander und wiederholen sich, bis du Stopp drückst.</p>
 <div class="programlist">${(pack.programs||[]).map(pr=>`<div class="librow"><div><strong>${LS_ESC(pr.icon)} ${LS_ESC(pr.name)}</strong><p>${pr.steps.length} Szenen · automatisch in Schleife</p></div><button class="outline" data-action="start-program" data-id="${LS_ESC(pr.id)}" ${this._busy||this._dirty?'disabled':''}>▶ Ablauf starten</button></div>`).join('')}${!(pack.programs||[]).length?`<p class="small muted">Noch keine Abläufe. Im Editor kannst du einen erstellen.</p>`:''}</div>
 <p class="small muted spaced">Tipp: Unter <b>Editor</b> stellst du die Effekte ein. Unter <b>Lampen</b> richtest du jede Lampe nur einmal ein.</p>`;}
 _renderLights(){const suggestions=this._data.suggestions||{};return `<div class="titleline"><div><h3>💡 Zentrale Lampenliste</h3><p>Einmal einrichten – anschließend funktionieren alle Show-Pakete mit denselben Lampen.</p></div><button class="outline" data-action="automap">↻ Erkennen</button></div>
 ${this._settings.fixtures.map((f,i)=>`<div class="fixture"><div class="fixturehead"><strong>Leuchte ${i+1}</strong><div class="right"><label class="inline"><input data-field="fixture-enabled" data-index="${i}" type="checkbox" ${f.enabled?'checked':''}> Aktiv</label><button class="minibtn danger" data-action="remove-fixture" data-index="${i}">− Entfernen</button></div></div><div class="fields">
 <label class="wide">Home-Assistant-Lampe<select data-field="fixture-entity" data-index="${i}">${this._entitiesOptions(f.entity_id)}</select></label>
 <label>Gruppe<select data-field="fixture-role" data-index="${i}">${this._options(LS_ROLES,f.role)}</select></label>
 <label>Zigbee2MQTT-Gerät<select data-field="fixture-friend" data-index="${i}">${this._devicesOptions(f.friendly_name||suggestions[f.entity_id]||'')}</select></label>
 <label>Dymera-Lichtbereich<select data-field="fixture-endpoint" data-index="${i}">${this._options([['auto','Automatisch'],['top','⬆️ Oben'],['bottom','⬇️ Unten']],f.endpoint)}</select></label>
 </div></div>`).join('')}
 <button class="dashed" data-action="add-fixture">＋ Lampe hinzufügen</button>
 <p class="small muted">Für Dymera: oben und unten als <b>zwei Entitäten</b> anlegen, beide auf denselben Zigbee2MQTT-Gerätenamen beziehen. Standard-Lampen funktionieren über Home Assistant (abhängig von unterstützten Effekten).</p>`;}
 _renderEditor(){const s=this._sceneObj();return `<div class="titleline"><div><h3>🎛️ Szenen-Editor</h3><p>Vier Gruppen festlegen – einzelne Lampen bei Bedarf anders steuern.</p></div></div>
 <div class="sceneSelect">${this._packObj().scenes.map(x=>`<button class="scenechip ${x.id===this._scene?'active':''}" data-action="scene" data-id="${LS_ESC(x.id)}">${LS_ESC(x.icon)} ${LS_ESC(x.name)}</button>`).join('')}</div>
 <div class="actions spaced"><button class="outline" data-action="clone-scene">⧉ Szene kopieren</button><button class="outline" data-action="new-scene">＋ Szene erstellen</button><button class="outline danger" data-action="remove-scene" ${this._packObj().scenes.length<=1?'disabled':''}>− Szene löschen</button></div>
 <div class="fields topGap"><label>Szene <input data-field="scene-name" value="${LS_ESC(s.name)}" maxlength="70"></label><label>Symbol <input data-field="scene-icon" value="${LS_ESC(s.icon)}" maxlength="12"></label></div>
 <div class="trackgrid">${LS_ROLES.map(([role,name])=>`<section class="track"><h4>${name}</h4>${this._cueControls(s.tracks[role],'track',role)}</section>`).join('')}</div>
 <h4 class="overridesTitle">Einzelne Lampen anders steuern</h4><p class="small muted">Die Gruppen gelten für alle Lampen. Ausnahmen überschreiben die Gruppeneinstellung nur in dieser Szene.</p>
 ${s.overrides.map((o,i)=>`<div class="override"><div class="fixturehead"><strong>🎯 Ausnahme ${i+1}</strong><div class="right"><button class="minibtn" data-action="preview" data-eid="${LS_ESC(o.entity_id)}" ${this._busy||this._dirty||this._data.status.running?'disabled':''}>▶ 10 s testen</button><button class="minibtn danger" data-action="remove-override" data-index="${i}">−</button></div></div>
 <label>Leuchte<select data-field="override-entity" data-index="${i}">${this._options(this._settings.fixtures.map(f=>[f.entity_id,f.entity_id]),o.entity_id)}</select></label>${this._cueControls(o,'override',i)}</div>`).join('')}
 <button class="dashed" data-action="add-override">＋ Ausnahme für eine Lampe</button>
 <h4 class="overridesTitle">🎞️ Show-Abläufe für dieses Paket</h4><p class="small muted">Lege die Reihenfolge und Spieldauer der Szenen fest. Am Ende beginnt der Ablauf erneut.</p>
 ${(this._packObj().programs||[]).map((pr,pi)=>`<div class="fixture"><div class="fixturehead"><strong>${LS_ESC(pr.icon)} ${LS_ESC(pr.name)}</strong><button class="minibtn danger" data-action="remove-program" data-index="${pi}">− Ablauf</button></div>
 <div class="fields"><label>Name <input data-field="program-name" data-program="${pi}" value="${LS_ESC(pr.name)}" maxlength="70"></label><label>Symbol <input data-field="program-icon" data-program="${pi}" value="${LS_ESC(pr.icon)}" maxlength="12"></label></div>
 ${pr.steps.map((step,si)=>`<div class="fields topGap"><label>Schritt ${si+1}: Szene<select data-field="step-scene" data-program="${pi}" data-index="${si}">${this._options(this._packObj().scenes.map(sc=>[sc.id,sc.icon+' '+sc.name]),step.scene_id)}</select></label><label>Dauer (Sekunden)<input type="number" min="10" max="3600" data-field="step-duration" data-program="${pi}" data-index="${si}" value="${step.duration}"></label><button class="minibtn danger" data-action="remove-step" data-program="${pi}" data-index="${si}" ${pr.steps.length===1?'disabled':''}>− Schritt entfernen</button></div>`).join('')}
 <button class="dashed" data-action="add-step" data-program="${pi}" ${pr.steps.length>=50?'disabled':''}>＋ Nächste Szene</button></div>`).join('')}
 <button class="dashed" data-action="new-program">＋ Neuen Show-Ablauf erstellen</button>
 <div class="actions spaced"><button class="outline" data-action="preview-group" ${this._busy||this._dirty||this._data.status.running?'disabled':''}>▶ Erste aktive Lampe 10 s testen</button></div>`;}
 _renderSchedule(){const p=this._packObj(),sch=p.schedule,opts=this._settings.options;return `<h3>🕓 Automatischer Show-Start</h3><p class="small muted">Jedes Event hat seinen eigenen jährlichen Zeitplan. Aktivierung ist freiwillig. Ein Zeitfenster darf nicht über Mitternacht gehen.</p>
 <div class="schedule"><label class="checkbig"><input type="checkbox" data-field="schedule-enabled" ${sch.enabled?'checked':''}> ${LS_ESC(p.icon)} ${LS_ESC(p.name)} automatisch starten</label><div class="fields">
 <label>Monat<input type="number" min="1" max="12" data-field="schedule-month" value="${sch.month}"></label><label>Tag<input type="number" min="1" max="31" data-field="schedule-day" value="${sch.day}"></label>
 <label>Beginn<input type="time" data-field="schedule-start" value="${sch.start}"></label><label>Ende<input type="time" data-field="schedule-end" value="${sch.end}"></label>
 <label class="wide">Automatisch starten<select data-field="schedule-target">${this._options([...p.scenes.map(s=>['scene:'+s.id,'💡 Szene: '+s.name]),...(p.programs||[]).map(pr=>['program:'+pr.id,'🎞️ Ablauf: '+pr.name])],sch.program_id?'program:'+sch.program_id:'scene:'+sch.scene_id)}</select></label>
 </div></div>
 <h4 class="overridesTitle">Zusätzliche Showeffekte</h4><div class="schedule"><label class="checkbig"><input type="checkbox" data-field="shuffle" ${opts.shuffle?'checked':''}> 🔀 Zufälliger Szenenwechsel (nur im laufenden Paket)</label>
 <label>Wechsel alle Sekunden<input type="number" min="60" max="3600" step="30" data-field="shuffle-interval" value="${opts.shuffle_interval}"></label>
 <label class="checkbig spaced"><input type="checkbox" data-field="wind" ${opts.wind?'checked':''}> 🌬️ Kleine Windböen beim Kerzen-/Kamin-Effekt</label></div>
 <p class="small muted">Manuell gestartete Shows werden nicht vom Zeitplan beendet. Nach einem manuellen Stopp startet am gleichen Tag kein Zeitplan erneut.</p>`;}
 _renderLibrary(){return `<h3>📦 Show-Paket-Bibliothek</h3><p class="small muted">Neue Events werden als JSON-Paket importiert. Deine zentrale Lampenliste bleibt unverändert.</p>
 <div class="library">${this._settings.packs.map(p=>`<div class="librow"><div><strong>${LS_ESC(p.icon)} ${LS_ESC(p.name)}</strong><p>${LS_ESC(p.description)}</p><span class="small">${p.scenes.length} Szenen</span></div><button class="minibtn" data-action="pack" data-id="${LS_ESC(p.id)}">Auswählen</button></div>`).join('')}</div>
 <div class="fixture"><h4>Gewähltes Paket bearbeiten</h4><div class="fields"><label>Name<input data-field="pack-name" value="${LS_ESC(this._packObj().name)}" maxlength="70"></label><label>Symbol<input data-field="pack-icon" value="${LS_ESC(this._packObj().icon)}" maxlength="12"></label><label class="wide">Beschreibung<input data-field="pack-description" value="${LS_ESC(this._packObj().description)}" maxlength="250"></label></div></div>
 <div class="actions spaced"><button class="outline" data-action="clone-pack">⧉ Aktuelles Paket kopieren</button><button class="outline" data-action="show-import">＋ Paket importieren</button><button class="outline" data-action="show-export">⇧ Paket exportieren</button><button class="outline danger" data-action="delete-pack" ${this._settings.packs.length<=1?'disabled':''}>− Paket löschen</button></div>
 ${this._importOpen?`<div class="import"><label>Show-Paket (JSON)<textarea id="pack-json" data-field="import-json" rows="8" placeholder="Hier den JSON-Inhalt des neuen Show-Pakets einfügen">${LS_ESC(this._importText)}</textarea></label><button class="primary" data-action="import-pack">Paket prüfen & hinzufügen</button></div>`:''}
 ${this._exportOpen?`<div class="import"><label>Zum Sichern oder Weitergeben kopieren<textarea rows="12" readonly>${LS_ESC(JSON.stringify(this._packObj(),null,2))}</textarea></label></div>`:''}
 <div class="help"><strong>Das Prinzip:</strong> Ein Show-Paket enthält Szenen mit vier Rollen: Oben, Unten, Haustür, Andere. Eine Szene kann zusätzlich beliebig viele Einzel-Ausnahmen definieren. So funktioniert ein neues Paket sofort mit deinen bereits eingerichteten Lampen.</div>`;}
 _css(accent){return `<style>
 :host{display:block;--ls-accent:${accent};--ls-bg:${this._config?.background==='theme'?'var(--ha-card-background, var(--card-background-color, var(--ls-text)))':'transparent'};--ls-panel:var(--ha-card-background, var(--card-background-color, var(--ls-text)));--ls-line:var(--divider-color, #8885);--ls-muted:var(--secondary-text-color, #666);--ls-text:var(--primary-text-color, #222);font:inherit;line-height:1.4}
 *{box-sizing:border-box} .studio{color:var(--ls-text);background:var(--ls-bg);border:1px solid var(--ls-line);border-radius:var(--ha-card-border-radius,12px);overflow:hidden;box-shadow:none}
 .hero{background:transparent;padding:21px 20px;border-bottom:1px solid var(--ls-line)}.eyebrow{color:var(--ls-accent);font-size:11px;font-weight:800;letter-spacing:2px}.hero h2{font-size:26px;margin:7px 0 1px;color:var(--ls-text)}.hero p{font-size:12px;color:var(--ls-muted);margin:0}
 .status{display:inline-flex;gap:6px;font-size:11px;border:1px solid var(--ls-line);border-radius:20px;padding:5px 9px;color:var(--ls-text);margin-top:11px}.status.on{border-color:var(--success-color, #2e7d32);color:var(--success-color, #2e7d32)}
 .nav{display:flex;gap:2px;overflow-x:auto;background:transparent;padding:6px;scrollbar-width:thin}.navbtn{white-space:nowrap;background:transparent;border:0;color:var(--ls-muted);border-radius:8px;padding:10px 11px;font-size:12px;font-weight:700}.navbtn.selected{background:var(--ls-panel);color:var(--ls-text)}
 .content{padding:17px 18px 20px}.packselect{display:flex;overflow-x:auto;gap:7px;margin-bottom:18px;padding-bottom:4px}.packpill{white-space:nowrap;background:var(--ls-panel);color:var(--ls-text);border:1px solid var(--ls-line);border-radius:16px;padding:9px 12px;font-size:12px}.packpill.sel{border-color:var(--ls-accent);box-shadow:0 0 0 1px var(--ls-accent) inset;color:var(--ls-text)}
 h3{font-size:18px;margin:0 0 7px;color:var(--ls-text)}h4{font-size:14px;margin:0 0 10px;color:var(--ls-text)}p{margin:0}.titleline{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;margin:0 0 14px}.titleline p{font-size:12px;color:var(--ls-muted)}.muted{color:var(--ls-muted)}.small{font-size:12px;line-height:1.55}.spaced{margin-top:15px}.topGap{margin-top:15px}
 .scenes{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}.scene{display:flex;flex-direction:column;text-align:left;min-height:105px;padding:12px;border:1px solid var(--ls-line);border-radius:12px;background:var(--ls-panel);color:var(--ls-text);gap:4px}.scene.active{border-color:var(--ls-accent);box-shadow:inset 0 0 0 1px var(--ls-accent)}.bigemoji{font-size:27px}.scene strong{font-size:13px}.scene small{color:var(--ls-muted);font-size:11px}
 .controlbox,.schedule,.fixture,.override,.track,.help,.import{background:var(--ls-panel);border:1px solid var(--ls-line);border-radius:12px;padding:14px;margin-top:14px}.controlbox strong{font-size:14px}.controlbox p{font-size:12px;color:var(--ls-muted);margin-top:5px}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:15px}button{cursor:pointer;font-family:inherit}button:disabled{opacity:.42;cursor:not-allowed}.primary,.stop,.outline,.dashed,.minibtn{border-radius:9px;padding:11px 13px;font-weight:700;font-size:12px}.primary{border:0;background:var(--ls-accent);color:#151421}.stop{border:1px solid var(--error-color, #c62828);background:transparent;color:var(--error-color, #c62828)}.outline{border:1px solid var(--ls-line);background:var(--ls-panel);color:var(--ls-text)}.outline.danger,.minibtn.danger{color:var(--error-color, #c62828)}.dashed{display:block;margin-top:12px;width:100%;border:1px dashed var(--ls-accent);background:transparent;color:var(--ls-accent);padding:12px}
 .fixturehead{display:flex;align-items:center;justify-content:space-between;gap:7px;flex-wrap:wrap;margin-bottom:10px}.fixturehead strong{font-size:13px}.right{display:flex;align-items:center;gap:9px}.minibtn{padding:7px 9px;border:1px solid var(--ls-line);background:var(--ls-panel);color:var(--ls-text)}.fields,.cuegrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.fields .wide{grid-column:1/-1}
 label{display:block;font-size:12px;color:var(--ls-text);font-weight:650;min-width:0}input:not([type=checkbox]):not([type=range]),select,textarea{display:block;margin-top:6px;background:var(--ls-panel);color:var(--ls-text);border:1px solid var(--ls-line);border-radius:8px;padding:10px;width:100%;font-size:12px;min-height:39px;color-scheme:var(--ls-color-scheme,normal);min-width:0}input[type=color]{min-height:48px!important;padding:4px!important}input[type=range]{width:100%;margin-top:16px;accent-color:var(--ls-accent)}input[type=checkbox]{accent-color:var(--ls-accent);width:17px;height:17px;vertical-align:middle}.inline{display:flex;align-items:center;gap:4px}.checkbig{font-size:13px;margin:0 0 15px}.value{float:right;color:var(--ls-accent)}.cuegrid{grid-template-columns:repeat(3,minmax(0,1fr));align-items:start}.cuegrid label:first-child{grid-column:1/-1}
 .sceneSelect{display:flex;gap:7px;overflow-x:auto}.scenechip{border:1px solid var(--ls-line);background:var(--ls-panel);color:var(--ls-text);white-space:nowrap;border-radius:9px;padding:9px;font-size:12px}.scenechip.active{border-color:var(--ls-accent)}.trackgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:14px}.track{margin:0}.overridesTitle{margin-top:22px;margin-bottom:4px}.override label{margin-bottom:9px}
 .librow{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 0;border-bottom:1px solid var(--ls-line)}.librow:last-child{border:0}.librow strong{font-size:14px}.librow p{font-size:11px;color:var(--ls-muted);margin:4px 0}.import textarea{font-family:monospace;resize:vertical}.help{font-size:12px;color:var(--ls-muted);line-height:1.5}
 .alerts{border:1px solid var(--error-color, #c62828);border-radius:9px;padding:10px;color:var(--error-color, #c62828);font-size:12px;margin-top:12px}.info{color:var(--success-color, #2e7d32);font-size:12px;margin:12px 0 0}.footer{display:flex;align-items:center;flex-wrap:wrap;gap:10px;justify-content:space-between;background:transparent;border-top:1px solid var(--ls-line);padding:13px 17px}.footer small{color:var(--ls-muted)}.footerbtn{display:flex;gap:8px}.loading{padding:28px}.notice{padding:9px 12px;color:var(--ls-muted);font-size:12px}
 @media(max-width:550px){.hero{padding:17px 14px}.hero h2{font-size:23px}.content{padding:14px 11px}.navbtn{font-size:11px;padding:9px 10px}.fields{grid-template-columns:1fr}.trackgrid{grid-template-columns:1fr}.cuegrid{grid-template-columns:repeat(2,minmax(0,1fr))}.scenes{grid-template-columns:repeat(2,minmax(0,1fr))}}
 button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--ls-accent);outline-offset:3px}
 </style>`;}
 _render(){if(!this.isConnected)return;const accent=LS_COLORS[this._pack]||'#96b2ff';if(!this._settings||!this._data){this.shadowRoot.innerHTML=this._css(accent)+`<div class="studio"><header class="hero"><div class="eyebrow">✦ LIGHTSHOW STUDIO ✦</div><h2>✨ Alle Events. Eine Steuerung.</h2></header><div class="loading">${LS_ESC(this._error||'Lade Home-Assistant-Daten ...')}</div></div>`;return;}
   this._ensureSelected();const st=this._data.status;
   const content=this._tab==='shows'?this._renderShows():this._tab==='lights'?this._renderLights():this._tab==='editor'?this._renderEditor():this._tab==='schedule'?this._renderSchedule():this._renderLibrary();
   this.shadowRoot.innerHTML=this._css(accent)+`<div class="studio"><header class="hero"><div class="eyebrow">✦ LIGHTSHOW STUDIO 2.0 ✦</div><h2>✨ Deine Lichtshow-Zentrale</h2><p>Halloween · Weihnachten · Party · Ambiente · deine Events</p><div class="status ${st.running?'on':''}">${st.running?'● SHOW AKTIV':'○ BEREIT'}</div></header><nav class="nav">${this._tabs()}</nav><div class="content">${this._packSelector()}${content}${st.warnings?.length?`<div class="alerts"><strong>Hinweise:</strong><ul>${st.warnings.map(x=>`<li>${LS_ESC(x)}</li>`).join('')}</ul></div>`:''}${this._error?`<div class="alerts">${LS_ESC(this._error)}</div>`:''}${this._info?`<p class="info">${LS_ESC(this._info)}</p>`:''}${this._data.migrated&&!this._migratedShown?`<p class="notice">Die alten Halloween-Szenen wurden importiert. Bitte Lampen prüfen und alte Automationen deaktivieren.</p>`:''}</div>
 <footer class="footer"><small>${this._dirty?'● Noch nicht gespeichert':'✓ Konfiguration gespeichert'}</small><div class="footerbtn"><button class="outline" data-action="discard" ${!this._dirty?'disabled':''}>Verwerfen</button><button class="primary" data-action="save" ${!this._dirty||this._busy?'disabled':''}>✓ Speichern</button></div></footer></div>`;}
 _dirtyMark(rebuild=true){this._dirty=true;this._error='';this._info='';if(rebuild)this._render();else{const b=this.shadowRoot.querySelector('[data-action=save]');if(b)b.disabled=false;const t=this.shadowRoot.querySelector('.footer small');if(t)t.textContent='● Noch nicht gespeichert';}}
 _cueFor(kind,index){return kind==='track'?this._sceneObj().tracks[index]:this._sceneObj().overrides[Number(index)];}
 _input(e){const f=e.target.dataset.field,i=e.target.dataset.index; if(!f)return;
   if(f==='import-json'){this._importText=e.target.value;return;}
   if(f==='program-name'){this._packObj().programs[Number(e.target.dataset.program)].name=e.target.value;this._dirtyMark(false);return;}
   if(f==='program-icon'){this._packObj().programs[Number(e.target.dataset.program)].icon=e.target.value;this._dirtyMark(false);return;}
   if(f==='pack-name'){this._packObj().name=e.target.value;this._dirtyMark(false);return;}
   if(f==='pack-icon'){this._packObj().icon=e.target.value;this._dirtyMark(false);return;}
   if(f==='pack-description'){this._packObj().description=e.target.value;this._dirtyMark(false);return;}
   if(f==='scene-name'){this._sceneObj().name=e.target.value;this._dirtyMark(false);return;}
   if(f==='scene-icon'){this._sceneObj().icon=e.target.value;this._dirtyMark(false);return;}
   if(['brightness','speed'].includes(f)){const cue=this._cueFor(e.target.dataset.kind,i);cue[f]=Number(e.target.value);const label=e.target.closest('label');if(label)label.querySelector('.value').textContent=e.target.value+'%';this._dirtyMark(false);return;}
 }
 _change(e){const t=e.target,f=t.dataset.field,i=Number(t.dataset.index),p=this._packObj();if(!f||['brightness','speed','scene-name','scene-icon','program-name','program-icon','pack-name','pack-icon','pack-description','import-json'].includes(f))return;
   if(f.startsWith('fixture-')){const x=this._settings.fixtures[i];if(f==='fixture-entity'){x.entity_id=t.value;x.endpoint=t.value.endsWith('_top')?'top':t.value.endsWith('_bottom')?'bottom':'auto';x.role=t.value.endsWith('_top')?'upper':t.value.endsWith('_bottom')?'lower':x.role;x.friendly_name='';}else if(f==='fixture-role')x.role=t.value;else if(f==='fixture-friend')x.friendly_name=t.value;else if(f==='fixture-endpoint')x.endpoint=t.value;else if(f==='fixture-enabled')x.enabled=t.checked;}
   else if(f==='cue-mode')this._cueFor(t.dataset.kind,t.dataset.index).mode=t.value;
   else if(f==='cue-color')this._cueFor(t.dataset.kind,t.dataset.index).color=t.value;
   else if(f==='override-entity')this._sceneObj().overrides[i].entity_id=t.value;
   else if(f==='step-scene')p.programs[Number(t.dataset.program)].steps[i].scene_id=t.value;
   else if(f==='step-duration')p.programs[Number(t.dataset.program)].steps[i].duration=Number(t.value);
   else if(f==='schedule-target'){const [typ,id]=t.value.split(':');if(typ==='program')p.schedule.program_id=id;else{p.schedule.program_id='';p.schedule.scene_id=id;}}
   else if(f.startsWith('schedule-')){const field=f.substring('schedule-'.length);p.schedule[field==='scene'?'scene_id':field]=field==='enabled'?t.checked:['month','day'].includes(field)?Number(t.value):t.value;}
   else if(f==='shuffle')this._settings.options.shuffle=t.checked;
   else if(f==='wind')this._settings.options.wind=t.checked;
   else if(f==='shuffle-interval')this._settings.options.shuffle_interval=Number(t.value);
   this._dirtyMark();}
 _uniqId(prefix, existing){let id=prefix+'_'+Date.now().toString(36);let n=0;while(existing.includes(id))id=prefix+'_'+Date.now().toString(36)+'_'+(++n);return id;}
 async _click(e){const t=e.target.closest('button[data-action]');if(!t||t.disabled)return;const a=t.dataset.action,i=Number(t.dataset.index);
   if(a==='tab'){this._tab=t.dataset.id;this._render();return;}
   if(a==='pack'){this._pack=t.dataset.id;this._ensureSelected();this._render();return;}
   if(a==='scene'){this._scene=t.dataset.id;this._render();return;}
   const p=this._packObj(),s=this._sceneObj();
   if(a==='add-fixture'){const next=this._entities().find(x=>!this._settings.fixtures.some(f=>f.entity_id===x.id));if(!next){this._error='Keine weitere freie light.* Entität gefunden.';this._render();return;}const role=next.id.endsWith('_top')?'upper':next.id.endsWith('_bottom')?'lower':'other';this._settings.fixtures.push({entity_id:next.id,role,endpoint:LS_DEF(role),friendly_name:'',enabled:true});this._dirtyMark();return;}
   if(a==='remove-fixture'){const eid=this._settings.fixtures[i].entity_id;this._settings.fixtures.splice(i,1);for(const pack of this._settings.packs)for(const sc of pack.scenes)sc.overrides=sc.overrides.filter(o=>o.entity_id!==eid);this._dirtyMark();return;}
   if(a==='automap'){let n=0;for(const f of this._settings.fixtures){const sug=this._data.suggestions[f.entity_id];if(sug){f.friendly_name=sug;n++;}}this._dirtyMark();this._info=n+' Lampen automatisch zugeordnet. Bitte kontrollieren und speichern.';this._render();return;}
   if(a==='add-override'){const next=this._settings.fixtures.find(f=>!s.overrides.some(o=>o.entity_id===f.entity_id));if(!next){this._error='Alle eingerichteten Lampen haben bereits eine Ausnahme.';this._render();return;}s.overrides.push({entity_id:next.entity_id,...LS_COPY(s.tracks[next.role])});this._dirtyMark();return;}
   if(a==='remove-override'){s.overrides.splice(i,1);this._dirtyMark();return;}
   if(a==='new-scene'||a==='clone-scene'){if(p.scenes.length>=35){this._error='Maximal 35 Szenen pro Paket';this._render();return;}const name=window.prompt('Name deiner neuen Szene:',a==='clone-scene'?s.name+' (Kopie)':'Meine Lichtszene');if(!name)return;const copy=a==='clone-scene'?LS_COPY(s):{id:'',name:'',icon:'✨',description:'',tracks:Object.fromEntries(LS_ROLES.map(([id])=>[id,LS_CUE()])),overrides:[]};copy.id=this._uniqId('scene',p.scenes.map(x=>x.id));copy.name=name.trim().slice(0,70);if(!copy.name)return;p.scenes.push(copy);this._scene=copy.id;this._dirtyMark();return;}
   if(a==='remove-scene'){if(!window.confirm('Szene wirklich entfernen?'))return;p.scenes=p.scenes.filter(x=>x.id!==s.id);if(p.schedule.scene_id===s.id)p.schedule.scene_id=p.scenes[0].id;for(const pr of (p.programs||[]))for(const step of pr.steps)if(step.scene_id===s.id)step.scene_id=p.scenes[0].id;this._scene=p.scenes[0].id;this._dirtyMark();return;}
   if(a==='new-program'){
     p.programs=p.programs||[];if(p.programs.length>=20){this._error='Maximal 20 Show-Abläufe';this._render();return;}
     const name=window.prompt('Name des Show-Ablaufs:','Meine Lightshow');if(!name)return;
     p.programs.push({id:this._uniqId('tour',p.programs.map(x=>x.id)),name:name.trim().slice(0,70),icon:'🎬',steps:p.scenes.slice(0,3).map(x=>({scene_id:x.id,duration:60}))});this._dirtyMark();return;
   }
   if(a==='remove-program'){
     const prog=p.programs[i];if(!window.confirm('Show-Ablauf wirklich löschen?'))return;
     if(p.schedule.program_id===prog.id)p.schedule.program_id='';p.programs.splice(i,1);this._dirtyMark();return;
   }
   if(a==='add-step'){const program=p.programs[Number(t.dataset.program)];if(program.steps.length<50)program.steps.push({scene_id:p.scenes[0].id,duration:60});this._dirtyMark();return;}
   if(a==='remove-step'){const program=p.programs[Number(t.dataset.program)];if(program.steps.length>1)program.steps.splice(i,1);this._dirtyMark();return;}
   if(a==='clone-pack'){if(this._settings.packs.length>=30){this._error='Maximal 30 Pakete';this._render();return;}const name=window.prompt('Neuer Event-/Paketname:',p.name+' (eigene Version)');if(!name)return;const copy=LS_COPY(p);copy.id=this._uniqId('pack',this._settings.packs.map(x=>x.id));copy.name=name.trim().slice(0,70);copy.schedule.enabled=false;this._settings.packs.push(copy);this._pack=copy.id;this._scene=copy.scenes[0].id;this._dirtyMark();return;}
   if(a==='delete-pack'){if(this._settings.packs.length<=1)return;if(!window.confirm('Das Paket '+p.name+' mit allen Szenen und Abläufen wirklich löschen?'))return;this._settings.packs=this._settings.packs.filter(x=>x.id!==p.id);this._pack=this._settings.packs[0].id;this._scene=this._settings.packs[0].scenes[0].id;this._dirtyMark();return;}
   if(a==='show-import'){this._importOpen=!this._importOpen;this._importText='';this._exportOpen=false;this._render();return;}
   if(a==='show-export'){this._exportOpen=!this._exportOpen;this._importOpen=false;this._render();return;}
   if(a==='import-pack'){
     try{const raw=this.shadowRoot.querySelector('#pack-json')?.value||'';const obj=JSON.parse(raw);
       if(!obj||typeof obj!=='object'||Array.isArray(obj)||!obj.id||!obj.scenes?.length)throw Error('Kein gültiges Paket-Objekt');
       if(this._settings.packs.some(x=>x.id===obj.id))throw Error('Paket-ID existiert schon. Bitte das Paket zuerst umbenennen.');
       if(this._settings.packs.length>=30)throw Error('Maximal 30 Pakete');
       this._settings.packs.push(obj);this._pack=obj.id;this._scene=obj.scenes[0].id;this._importOpen=false;this._importText='';this._dirtyMark();this._info='Paket hinzugefügt. Bitte speichern – HA prüft alle Felder.';this._render();
     }catch(err){this._error=err.message||String(err);this._render();}return;
   }
   if(a==='discard'){if(!window.confirm('Ungespeicherte Änderungen verwerfen?'))return;this._dirty=false;this._info='Änderungen verworfen';await this._load();return;}
   if(a==='save'){this._busy=true;this._render();try{const fresh=await this._ws('save',{settings:this._settings});this._data=fresh;this._settings=LS_COPY(fresh.settings);this._dirty=false;this._info='Konfiguration dauerhaft in Home Assistant gespeichert.';this._error='';}catch(err){this._error=err.message||String(err);}finally{this._busy=false;this._render();}return;}
   if(['start','start-program','preview','preview-group'].includes(a)&&this._dirty){this._error='Bitte erst speichern, bevor du einen Effekt startest oder testest.';this._render();return;}
   if(['start','start-program','stop','preview','preview-group'].includes(a)){
     let eid=t.dataset.eid;if(a==='preview-group'){const first=this._settings.fixtures.find(f=>f.enabled&&this._hass.states[f.entity_id]&&this._hass.states[f.entity_id].state!=='unavailable');eid=first?.entity_id;if(!eid){this._error='Keine aktive Lampe verfügbar';this._render();return;}}
     this._busy=true;this._render();try{let resp;
       if(a==='start')resp=await this._ws('start',{pack_id:p.id,scene_id:s.id});
       else if(a==='start-program')resp=await this._ws('start_program',{pack_id:p.id,program_id:t.dataset.id});
       else if(a==='stop')resp=await this._ws('stop');
       else resp=await this._ws('preview',{pack_id:p.id,scene_id:s.id,entity_id:eid});
       this._data=resp;this._info=a==='start-program'?'Show-Ablauf gestartet. Szenen wechseln automatisch.':a==='start'?'Szene an die konfigurierten Lampen gesendet.':a==='stop'?'Show gestoppt. Rücksetzen wurde versucht.':'10-Sekunden-Vorschau gestartet.';this._error='';
     }catch(err){this._error=err.message||String(err);}finally{this._busy=false;this._render();}return;
   }
 }
}
if(!customElements.get('lightshow-studio'))customElements.define('lightshow-studio',LightshowStudio);
window.customCards=window.customCards||[];
window.customCards.push({type:'lightshow-studio',name:'Lightshow Studio',description:'Modulare Event-Lichtshows für Home Assistant und Zigbee2MQTT',preview:false});
