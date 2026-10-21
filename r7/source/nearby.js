/* Prototype question: can explicit activity links make Nearby easy to locate?
   Keep the supplied two-column layout; use inline disclosures below 801px. */
const nearbyKey=(date,id)=>JSON.stringify([date,id]);
const nearbyId=(kind,key)=>'nearby-'+kind+'-'+encodeURIComponent(key);
const nearbyPlaceCount=n=>`${n} ${n===1?'place':'places'}`;
function nearbyGroups(t){
 const anchors=[];
 for(const [dayIndex,d] of array(t.days).entries())for(const a of array(d.activities))
  if(!isFree(a))anchors.push({key:nearbyKey(d.date,a.activity_id),date:d.date,dayIndex,activity:a,items:[]});
 const other=[];
 nearbyEntries(t).forEach((reference,index)=>{
  const candidates=reference.anchor_activity_id?anchors.filter(g=>g.activity.activity_id===reference.anchor_activity_id&&(!reference.associated_day||g.date===reference.associated_day)):[];
  const item={reference,index};
  if(candidates.length===1)candidates[0].items.push(item);else other.push(item);
 });
 return {groups:anchors.filter(g=>g.items.length),other};
}
function nearbyGroup(t,g){
 const open=!ui.nearbyCollapsed.has(g.key),selected=ui.nearbySelected===g.key;
 return `<section class="nearby-group ${selected?'nearby-linked-selected':''}" id="${nearbyId('group',g.key)}" aria-label="Nearby for ${esc(activityName(g.activity))}"><div class="nearby-group-heading"><button type="button" class="nearby-anchor-link" data-action="nearby-back" data-key="${esc(g.key)}" aria-label="Find ${esc(activityName(g.activity))} in Day ${g.dayIndex+1} itinerary">${ic('pin',16)}<span><strong>${esc(activityName(g.activity))}</strong><small>Around this stop · ${nearbyPlaceCount(g.items.length)}</small></span></button>${button(ic('down',16),'nearby-toggle',`nearby-group-toggle ${open?'open':''}`,`data-key="${esc(g.key)}" id="${nearbyId('toggle',g.key)}" aria-label="${open?'Collapse':'Expand'} nearby for ${esc(activityName(g.activity))}" aria-expanded="${open}" aria-controls="${nearbyId('items',g.key)}"`)}</div><div class="nearby-group-items" id="${nearbyId('items',g.key)}" ${open?'':'hidden'}>${g.items.map(({reference,index})=>nearbyRow(t,reference,index)).join('')}</div></section>`;
}
function nearbyPanel(t){
 const {groups,other}=nearbyGroups(t),visible=groups.filter(g=>ui.dayFilter==='all'||g.date===ui.dayFilter),unassigned=other.filter(({reference:n})=>ui.dayFilter==='all'||!n.associated_day||n.associated_day===ui.dayFilter);
 return `<section class="content-card nearby-panel ${unassigned.length?'has-other':''}" id="nearby"><div class="nearby-sidebar-groups"><div class="content-heading"><span class="section-icon nearby-icon">${ic('pin',21)}</span><h2>Nearby · A little discovery</h2></div><p class="aside-intro">Ideas near your planned stops. These are not scheduled visits.</p>${array(t.days).map((d,i)=>{const matches=visible.filter(g=>g.date===d.date);return matches.length?`<section class="nearby-day"><h3>DAY ${i+1} <span>· ${dt(d.date).toUpperCase()}</span></h3>${matches.map(g=>nearbyGroup(t,g)).join('')}</section>`:'';}).join('')}${!visible.length&&!unassigned.length?'<p class="nearby-empty">No nearby ideas for '+(ui.dayFilter==='all'?'these stops.':'this day.')+'</p>':''}</div>${unassigned.length?`<section class="nearby-other" id="nearby-other"><h3>Other nearby references</h3><p class="aside-intro">Optional places without a linked scheduled stop.</p>${unassigned.map(({reference,index})=>nearbyRow(t,reference,index,true)).join('')}</section>`:''}${visible.length||unassigned.length?'<p class="footnote caution-text">'+ic('info',14)+' Straight-line distances are not walking routes.</p>':''}</section>`;
}
function nearbyInline(t,g){
 const open=ui.nearbyInlineOpen.has(g.key);
 return `<section class="nearby-inline" id="${nearbyId('inline',g.key)}">${button(`${ic('pin',14)}<span>Nearby · ${nearbyPlaceCount(g.items.length)}</span>${ic('down',15)}`,'nearby-inline-toggle',`nearby-inline-trigger ${open?'open':''}`,`id="${nearbyId('inline-trigger',g.key)}" data-key="${esc(g.key)}" aria-label="${open?'Hide':'Show'} nearby for ${esc(activityName(g.activity))}" aria-expanded="${open}" aria-controls="${nearbyId('inline-items',g.key)}"`)}<div class="nearby-inline-items" id="${nearbyId('inline-items',g.key)}" ${open?'':'hidden'}><p class="nearby-inline-note">Optional places · not scheduled visits</p>${g.items.map(({reference,index})=>nearbyRow(t,reference,index)).join('')}</div></section>`;
}
let nearbyPulse=0;
function nearbyNavigate(key,destination){
 const t=findTrip(ui.detailTrip),g=t&&nearbyGroups(t).groups.find(g=>g.key===key);if(!g)return;
 ui.dayOpen.add(g.date);ui.nearbyCollapsed.delete(key);
 if(ui.dayFilter!=='all'&&ui.dayFilter!==g.date)ui.dayFilter=g.date;
 const mobile=matchMedia('(max-width:800px)').matches;
 if(mobile)ui.nearbyInlineOpen.add(key);
 ui.nearbySelected=key;const pulse=++nearbyPulse;render();
 requestAnimationFrame(()=>{
  const target=document.getElementById(nearbyId(destination==='stop'?'stop':mobile?'inline':'group',key));
  const focus=destination==='stop'?target:target?.querySelector('button');
  focus?.focus({preventScroll:true});target?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'center'});
 });
 setTimeout(()=>{if(pulse!==nearbyPulse)return;ui.nearbySelected=null;document.querySelectorAll('.nearby-linked-selected').forEach(el=>el.classList.remove('nearby-linked-selected'));},2600);
}
function nearbyToggle(key,inline){
 const set=inline?ui.nearbyInlineOpen:ui.nearbyCollapsed;
 set.has(key)?set.delete(key):set.add(key);render();
 requestAnimationFrame(()=>document.getElementById(nearbyId(inline?'inline-trigger':'toggle',key))?.focus({preventScroll:true}));
}
function scrollDetailSection(value){
 let target=document.getElementById(value);
 if(value==='nearby'&&matchMedia('(max-width:800px)').matches){
  const t=findTrip(ui.detailTrip),g=t&&nearbyGroups(t).groups.find(g=>ui.dayFilter==='all'||g.date===ui.dayFilter);
  if(g){nearbyNavigate(g.key,'group');return;}
  target=document.getElementById('nearby-other');
  if(!target){showToast('No nearby ideas for this day.');return;}
 }
 target?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'start'});
}
