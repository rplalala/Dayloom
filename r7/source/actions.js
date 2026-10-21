function dateTimeValue(value,path){
 const m=/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,9}))?)?(Z|[+-]\d{2}:\d{2})?$/.exec(value||'');
 if(!m||!validDate(m[1])||Number(m[2])>23||Number(m[3])>59||Number(m[4]||0)>59)throw Error(path+': use a valid local ISO date and time.');
 const offset=m[6];let offsetMinutes=0;
 if(offset&&offset!=='Z'){const h=Number(offset.slice(1,3)),min=Number(offset.slice(4));if(h>23||min>59)throw Error(path+': invalid UTC offset.');offsetMinutes=(h*60+min)*(offset[0]==='-'?-1:1);}
 const seconds=BigInt(Date.parse(`${m[1]}T${m[2]}:${m[3]}:${m[4]||'00'}Z`)/1000);
 return {aware:!!offset,time:seconds*1000000000n+BigInt((m[5]||'').padEnd(9,'0'))-BigInt(offsetMinutes)*60000000000n};
}
function normalizeImport(raw){
 if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('Import one itinerary JSON object.');
 const x=raw.itinerary||raw;
 if(typeof x.destination!=='string'||!x.destination.trim()||!Array.isArray(x.days))throw Error('Expected a destination and a days array.');
 if(!x.days.length||x.days.length>400)throw Error('Provide between 1 and 400 day records.');
 const seenDays=new Set(),ids=new Map();
 const days=x.days.map((d,i)=>{
  const path=`days[${i}]`;
  if(!validDate(d?.date))throw Error(path+'.date: enter a real date in YYYY-MM-DD format.');
  if(seenDays.has(d.date))throw Error(path+'.date: duplicate day.');seenDays.add(d.date);
  if(!Array.isArray(d.activities))throw Error(path+'.activities: expected an array.');
  const activities=d.activities.map((a,j)=>{
   const loc=path+`.activities[${j}]`;
   if(!a||typeof a!=='object'||Array.isArray(a))throw Error(loc+': expected an activity.');
   const id=String(a.activity_id||`import-day-${i}-activity-${j}`);
   if(ids.has(id))throw Error(loc+'.activity_id: duplicate activity identifier.');ids.set(id,d.date);
   const start=dateTimeValue(a.start_time,loc+'.start_time'),end=dateTimeValue(a.end_time,loc+'.end_time');
   if(start.aware!==end.aware)throw Error(loc+': start and end must both include UTC offsets, or both omit them.');
   if(end.time<=start.time)throw Error(loc+': the end must be after the start in actual time.');
   if(String(a.start_time).slice(0,10)!==d.date)throw Error(loc+'.start_time: the local date must match its day record.');
   if(a.estimated_cost!=null&&(!finite(a.estimated_cost.amount)||Number(a.estimated_cost.amount)<0||!a.estimated_cost.currency))throw Error(loc+'.estimated_cost: provide a non-negative amount and currency, or null.');
   return {...cloned(a),activity_id:id,estimated_cost:a.estimated_cost??null,nearby:array(a.nearby)};
  });
  return {...cloned(d),activities,weather:d.weather||{status:'unavailable',forecast:null}};
 });
 const dates=[...seenDays].sort(),start=x.start_date||dates[0],end=x.end_date||dates.at(-1);
 if(!validDate(start)||!validDate(end)||end<start)throw Error('The itinerary start/end dates are invalid or reversed.');
 if(dates.some(d=>d<start||d>end))throw Error('A day record falls outside the itinerary date range.');
 const transfers=array(x.transfers);
 for(const [i,l] of transfers.entries()){
  if(!ids.has(l.from_activity_id)||!ids.has(l.to_activity_id))throw Error(`transfers[${i}]: an endpoint activity does not exist.`);
  if(l.from_activity_id===l.to_activity_id||ids.get(l.from_activity_id)!==ids.get(l.to_activity_id))throw Error(`transfers[${i}]: use distinct endpoints on the same day.`);
 }
 for(const d of days)for(const a of d.activities)for(const n of a.nearby){if(n.anchor_activity_id&&n.anchor_activity_id!==a.activity_id)throw Error('A Nearby reference points to a different activity.');if(n.associated_day&&n.associated_day!==d.date)throw Error('A Nearby reference has a mismatched day.');}
 const req=raw.request||raw.input||raw._prototype?.input||null,known=req||raw.requirements||{},budget=known.budget||(finite(raw.activity_budget)?{amount:raw.activity_budget,currency:raw.currency}:null);
 return {id:uid('preview'),title:raw.title||raw._prototype?.title||`${x.destination} · ${days.length}-day itinerary`,destination:x.destination,start_date:start,end_date:end,days,transfers:cloned(transfers),nearby:cloned(array(x.nearby)),reference_recommendations:cloned(array(x.reference_recommendations)),status:'preview',origin:'imported',created_at:new Date().toISOString(),description:'Your imported itinerary, kept as supplied.',cover:/sydney/i.test(x.destination)?'sydney':'nature',people:known.traveler_count??raw.people??null,activity_budget:budget?.amount??null,currency:budget?.currency||null,interests:[],pace:'',transport:[],request:req?cloned(req):null,policy_completion:raw.policy_completion||'unassessed',policy_reasons:array(raw.policy_reasons),minimum_daily_coverage:array(raw.minimum_daily_coverage),preference_coverage:array(raw.preference_coverage)};
}
function toExport(t){return {title:t.title,origin:t.origin,request:t.request||null,policy_completion:t.policy_completion||'unassessed',policy_reasons:array(t.policy_reasons),minimum_daily_coverage:array(t.minimum_daily_coverage),preference_coverage:array(t.preference_coverage),itinerary:{output_version:'itinerary_3',destination:t.destination,start_date:t.start_date,end_date:t.end_date,days:cloned(t.days),transfers:cloned(t.transfers||[]),nearby:cloned(t.nearby||[]),reference_recommendations:cloned(t.reference_recommendations||[])}};}
function summaryText(t){return `${t.title}\nDestination: ${t.destination}\nDates: ${t.start_date} — ${t.end_date}\n\n${array(t.days).map((d,i)=>`Day ${i+1} · ${d.date}\n${array(d.activities).map(a=>`${clock(a.start_time)}–${clock(a.end_time)} ${activityName(a)}${isFree(a)?' (free time)':''}\n${a.location||''}\n${a.notes||''}`).join('\n\n')}`).join('\n\n')}\n\nConnections\n${array(t.transfers).map(l=>`${activityName(allActivities(t).find(a=>a.activity_id===l.from_activity_id))} → ${activityName(allActivities(t).find(a=>a.activity_id===l.to_activity_id))}: ${modeName(l.mode)} · ${minutes(l.provider_duration_seconds)} · ${distance(l.distance_meters)} · ${transferState(l).label}`).join('\n')}\n\nNearby (unscheduled)\n${nearbyEntries(t).map(n=>`${n.place_name}: ${n.reason||''}\n${n.uncertainty||''}`).join('\n')}\n\nUnknown information remains to confirm. No bookings have been made.`;}
function downloadText(content,name,type){const blob=new Blob([content],{type});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),500);}
function exportTrip(id,format){const t=findTrip(id);if(!t)return;const title=t.title.replace(/[<>:"/\\|?*\u0000-\u001f]/g,'_');downloadText(format==='json'?JSON.stringify(toExport(t),null,2):summaryText(t),title+(format==='json'?'.json':'.txt'),format==='json'?'application/json;charset=utf-8':'text/plain;charset=utf-8');showToast('Your itinerary has been exported.');}
async function copySummary(t){try{await navigator.clipboard.writeText(summaryText(t));showToast('Itinerary summary copied.');}catch{openModal({type:'sharetext',text:summaryText(t)});}}
function openModal(m){modalFocus=document.activeElement;ui.modal=m;render();}
function closeModal(){ui.modal=null;render();if(modalFocus?.isConnected)modalFocus.focus();}
function refreshPreferenceUI(){
 document.querySelectorAll('#planForm [data-action="interest"]').forEach(el=>{const on=ui.plan.interests.includes(el.dataset.value);el.classList.toggle('active',on);el.setAttribute('aria-pressed',String(on));el.innerHTML=ic(on?'check':'plus',14)+' '+esc(el.dataset.value);});
 document.querySelectorAll('#planForm [data-action="pace"]').forEach(el=>{const on=ui.plan.pace===el.dataset.value;el.classList.toggle('selected',on);el.setAttribute('aria-pressed',String(on));});
 document.querySelectorAll('#planForm [data-action="transport"]').forEach(el=>{const on=ui.plan.transport.includes(el.dataset.value);el.classList.toggle('selected',on);el.setAttribute('aria-pressed',String(on));});
 const text=document.getElementById('plan-notes');if(text&&text.value!==ui.plan.notes)text.value=ui.plan.notes;
 const polish=document.getElementById('polish-button');if(polish)polish.disabled=!ui.plan.notes.trim();
 const region=document.getElementById('polish-region');if(region)region.innerHTML=polishView();persistPlan();
}
function captureProfile(){const form=document.getElementById('profileForm');if(!form||!profileEdit)return;const fd=new FormData(form);profileEdit.name=String(fd.get('name')||'').trim();profileEdit.currency=String(fd.get('currency')||'AUD');profileEdit.notes=String(fd.get('notes')||'');}
function render(){
 tickTask();const r=route();
 if(ui.activeRoute!==location.hash){
  if(r.path!=='/account')profileEdit=null;
  if(r.path.startsWith('/trips/')){const id=decodeURIComponent(r.path.slice(7)),t=findTrip(id);if(t&&id!==ui.detailTrip){ui.detailTrip=id;ui.dayOpen=new Set(array(t.days).map(d=>d.date));ui.dayFilter='all';ui.nearbyCollapsed=new Set();ui.nearbyInlineOpen=new Set();ui.nearbySelected=null;}}
  ui.activeRoute=location.hash;ui.mobileNav=false;
 }
 let content;
 if(r.path==='/')content=home();
 else if(r.path==='/plan')content=plan();
 else if(r.path==='/trips')content=trips();
 else if(r.path==='/login')content=auth();
 else if(r.path==='/account')content=accountPage();
 else if(r.path.startsWith('/trips/')){const t=findTrip(decodeURIComponent(r.path.slice(7)));content=t?tripDetail(t):`<div class="page container missing">${pageHeader('NOT FOUND','This itinerary is not available.','It may have been removed, or belong to a different account.')}${href('/trips','Back to My trips','btn btn-primary')}</div>`;}
 else content=`<div class="page container missing">${pageHeader('NOT FOUND','A little off the beaten path.','This page could not be found.')}${href('/','Back home','btn btn-primary')}</div>`;
 document.getElementById('app').innerHTML=header()+`<main id="main">${content}</main>`+footer()+modalMarkup()+'<div id="toast" class="toast" role="status" aria-live="polite"></div>';
 document.body.style.overflow=ui.modal?'hidden':'';loadPhotos();
 document.title=({ '/':'Home','/plan':'Plan a trip','/trips':'My trips','/login':'Log in','/account':'Your account'}[r.path]||'Itinerary')+' · Dayloom';
 if(ui.modal)requestAnimationFrame(()=>{document.querySelector('[role="dialog"] input:not([type="hidden"]),[role="dialog"] textarea,[role="dialog"] button')?.focus({preventScroll:true});});
}
function viewTask(){ui.modal=null;const t=task();if(t?.status==='completed'){t.seen=true;persist();const result=findTrip(t.preview_id);if(result){go('/trips/'+result.id);return;}}go('/plan');requestAnimationFrame(()=>document.getElementById('generation-progress')?.scrollIntoView({behavior:'smooth',block:'center'}));}
function act(action,el){const id=el.dataset.id,value=el.dataset.value;
 switch(action){
  case 'mobile-menu':ui.mobileNav=!ui.mobileNav;render();break;
  case 'account':capturePlan();go('/account');break;
  case 'logout':data.session=null;data.pending=null;data.guestPlan=null;ui.plan=freshPlan();ui.draftId=null;ui.displayPreview=null;ui.planFrom=null;ui.modal=null;ui.polish=null;ui.polishUndo=null;profileEdit=null;persist();go('/');showToast('You are logged out.');break;
  case 'auth-tab':ui.authTab=value;ui.authError='';document.querySelectorAll('.auth-tabs [role="tab"]').forEach(tab=>{const active=tab.dataset.value===value;tab.classList.toggle('active',active);tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;});document.querySelectorAll('.auth-pane').forEach(p=>{const active=p.id===`auth-${value}-panel`;p.inert=!active;p.setAttribute('aria-hidden',String(!active));});break;
  case 'toggle-password':{const input=el.parentElement.querySelector('input');input.type=input.type==='password'?'text':'password';break;}
  case 'interest':capturePlan();selectInterest(ui.plan,value);ui.polish=null;ui.polishUndo=null;refreshPreferenceUI();break;
  case 'pace':capturePlan();selectPace(ui.plan,value);ui.polish=null;ui.polishUndo=null;refreshPreferenceUI();break;
  case 'transport':capturePlan();selectTransport(ui.plan,value);ui.polish=null;ui.polishUndo=null;refreshPreferenceUI();break;
  case 'polish':{capturePlan();if(!ui.plan.notes.trim())return;const suggested=ui.plan.notes.split('\n').map(s=>s.trim().replace(/[ \t]+/g,' ')).filter(Boolean).join('\n');ui.polish={original:ui.plan.notes,suggested,originalBindings:cloned(bindings(ui.plan))};ui.polishUndo=null;refreshPreferenceUI();break;}
  case 'apply-polish':{const p=ui.polish;if(!p||p.original!==ui.plan.notes)return;ui.polishUndo={before:p.original,after:p.suggested,bindings:cloned(p.originalBindings)};const newBindings=[];for(const r of p.originalBindings){const at=p.suggested.indexOf(r.text);if(at>=0)newBindings.push({...r,start:at,end:at+r.text.length});else detachControl(ui.plan,r.key);}ui.plan.notes=p.suggested;ui.plan.promptBindings=newBindings;ui.polish=null;refreshPreferenceUI();showToast('Suggestion applied. You can undo it.');break;}
  case 'dismiss-polish':ui.polish=null;refreshPreferenceUI();break;
  case 'undo-polish':{const u=ui.polishUndo;if(!u||ui.plan.notes!==u.after)return;ui.plan.notes=u.before;ui.plan.promptBindings=u.bindings;ui.polishUndo=null;refreshPreferenceUI();showToast('Your original wording has been restored.');break;}
  case 'mood':{capturePlan();const sets=[['Art & museums','History & culture'],['Nature','Free exploration'],['City walks','History & culture']];for(const v of sets[Number(value)]||[])if(!ui.plan.interests.includes(v))selectInterest(ui.plan,v);if(ui.plan.pace!=='Relaxed')selectPace(ui.plan,'Relaxed');ui.polish=null;ui.polishUndo=null;persistPlan();go('/plan');break;}
  case 'input-summary':capturePlan();openModal({type:'input'});break;
  case 'save-draft':saveDraft();break;
  case 'save-as-draft':ui.draftId=null;saveDraft();break;
  case 'busy-save':ui.modal=null;render();saveDraft();break;
  case 'view-task':capturePlan();viewTask();break;
  case 'stop-generate':{tickTask();const t=task();if(t?.status==='running'){t.status='cancelled';t.finished_at=Date.now();persist();render();showToast('Planning stopped. Your brief is still available.');}else{render();showToast('Your itinerary is already complete. The preview is available.');}break;}
  case 'restore-task':if(task()){ui.plan=cloned(task().plan);ui.formError='';persistPlan();render();}break;
  case 'save-result':saveResult(id);break;
  case 'discard-preview':openModal({type:'discard',id});break;
  case 'confirm-discard':account().previews=account().previews.filter(t=>t.id!==id);if(ui.displayPreview===id)ui.displayPreview=null;if(task()?.preview_id===id)task().seen=true;persist();ui.modal=null;render();showToast('Preview discarded.');break;
  case 'replan':replan(findTrip(id));break;
  case 'duplicate':duplicate(id);break;
  case 'card-menu':openModal({type:'menu',id});break;
  case 'rename':openModal({type:'rename',id});break;
  case 'delete':openModal({type:'delete',id});break;
  case 'confirm-delete':account().trips=ownedTrips().filter(t=>t.id!==id);if(ui.draftId===id)ui.draftId=null;persist();ui.modal=null;render();showToast('Removed from My trips.');break;
  case 'prev-page':ui.tripsPage--;render();break;
  case 'next-page':ui.tripsPage++;render();break;
  case 'page':ui.tripsPage=Number(value);render();break;
  case 'day-toggle':ui.dayOpen.has(value)?ui.dayOpen.delete(value):ui.dayOpen.add(value);render();break;
  case 'filter-day':ui.nearbySelected=null;ui.dayFilter=value;if(value!=='all')ui.dayOpen.add(value);render();break;
  case 'expand-all':for(const d of array(findTrip(ui.detailTrip)?.days))ui.dayOpen.add(d.date);render();break;
  case 'activity':openModal({type:'activity',trip:el.dataset.trip,activity:id});break;
  case 'route':openModal({type:'route',trip:el.dataset.trip,activity:id,to:el.dataset.to});break;
  case 'nearby-jump':nearbyNavigate(el.dataset.key,'group');break;
  case 'nearby-back':nearbyNavigate(el.dataset.key,'stop');break;
  case 'nearby-toggle':nearbyToggle(el.dataset.key,false);break;
  case 'nearby-inline-toggle':nearbyToggle(el.dataset.key,true);break;
  case 'nearby-detail':openModal({type:'nearby',trip:el.dataset.trip,index:Number(value)});break;
  case 'scroll':scrollDetailSection(value);break;
  case 'export':openModal({type:'export',id});break;
  case 'export-json':exportTrip(id,'json');break;
  case 'export-text':exportTrip(id,'text');break;
  case 'share':{const t=findTrip(id);if(t)copySummary(t);break;}
  case 'import':if(requireAccount('import'))openModal({type:'import',text:''});break;
  case 'open-examples':if(!account())openModal({type:'examples'});break;
  case 'view-example':ui.modal=null;go('/trips/'+id);break;
  case 'close-modal':closeModal();break;
  case 'about':capturePlan();openModal({type:'about'});break;
  case 'profile-interest':captureProfile();profileEdit.interests=profileEdit.interests.includes(value)?profileEdit.interests.filter(v=>v!==value):[...profileEdit.interests,value];render();break;
  case 'profile-pace':captureProfile();profileEdit.pace=profileEdit.pace===value?'':value;render();break;
  case 'profile-transport':captureProfile();profileEdit.transport=profileEdit.transport.includes(value)?profileEdit.transport.filter(v=>v!==value):[...profileEdit.transport,value];render();break;
  case 'reset-avatar':captureProfile();profileEdit.avatar='';render();break;
  case 'simulate-failure':case 'simulate-clarification':case 'simulate-complete':if(running()){const t=task();t.scenario=action==='simulate-failure'?'failed':action==='simulate-clarification'?'clarification':'complete';t.started_at=Date.now()-t.duration;tickTask();ui.modal=null;render();}break;
 }
}
const app=document.getElementById('app');
app.addEventListener('click',e=>{
 const anchor=e.target.closest('a[href^="#/"]');if(anchor){capturePlan();ui.modal=null;ui.mobileNav=false;if(anchor.hash==='#/plan?new=1'){e.preventDefault();ui.plan=freshPlan(account()?.profile);ui.draftId=null;ui.planFrom=null;ui.polish=null;ui.polishUndo=null;ui.formError='';persistPlan();go('/plan');return;}if(anchor.hash===location.hash){e.preventDefault();render();window.scrollTo({top:0,behavior:'smooth'});}return;}
 const el=e.target.closest('[data-action]');if(!el)return;if(el.classList.contains('modal-backdrop')&&e.target.closest('[data-modal-card]'))return;e.preventDefault();act(el.dataset.action,el);
});
app.addEventListener('input',e=>{
 if(e.target.id==='tripSearch'){ui.search=e.target.value;ui.tripsPage=1;document.getElementById('tripList').innerHTML=renderTripList();loadPhotos();}
 else if(e.target.closest('#planForm')){capturePlan();ui.formError='';refreshPreferenceUI();}
 else if(e.target.closest('#profileForm'))captureProfile();
});
app.addEventListener('change',async e=>{
 if(e.target.id==='sortTrips'){ui.tripsSort=e.target.value;ui.tripsPage=1;document.getElementById('tripList').innerHTML=renderTripList();loadPhotos();}
 if(e.target.id==='importFile'){
  const file=e.target.files[0];if(!file)return;if(file.size>5*1024*1024){showToast('Choose one itinerary file smaller than 5 MB.');return;}
  const text=await file.text();const box=document.getElementById('importText');if(box)box.value=text;if(ui.modal?.type==='import')ui.modal.text=text;
 }
 if(e.target.id==='avatarFile'){
  const file=e.target.files[0];if(!file)return;if(file.size>2*1024*1024||!['image/png','image/jpeg','image/webp'].includes(file.type)){showToast('Choose a JPG, PNG or WebP image up to 2 MB.');return;}
  captureProfile();const img=new Image(),url=URL.createObjectURL(file);img.onload=()=>{const canvas=document.createElement('canvas');canvas.width=canvas.height=200;const scale=Math.max(200/img.width,200/img.height),w=img.width*scale,h=img.height*scale;canvas.getContext('2d').drawImage(img,(200-w)/2,(200-h)/2,w,h);profileEdit.avatar=canvas.toDataURL('image/jpeg',.85);URL.revokeObjectURL(url);render();};img.onerror=()=>{URL.revokeObjectURL(url);showToast('This image could not be opened.');};img.src=url;
 }
});
app.addEventListener('submit',e=>{
 e.preventDefault();const form=e.target;
 if(form.id==='planForm'){beginGenerate();return;}
 if(form.id==='profileForm'){captureProfile();if(!profileEdit.name){showToast('Enter a display name.');return;}account().profile=cloned(profileEdit);persist();render();showToast('Your profile and travel defaults are saved.');return;}
 if(form.id==='renameForm'){const fd=new FormData(form),t=ownedTrips().find(t=>t.id===fd.get('id')),title=String(fd.get('title')||'').trim();if(t&&title){t.title=title;t.updated_at=new Date().toISOString();persist();ui.modal=null;render();showToast('Trip name updated.');}return;}
 if(form.id==='importForm'){
  const text=String(new FormData(form).get('json')||'');try{if(new Blob([text]).size>5*1024*1024)throw Error('Choose one itinerary smaller than 5 MB.');const t=normalizeImport(JSON.parse(text.replace(/^\uFEFF/,'')));account().previews.unshift(t);ui.displayPreview=t.id;persist();ui.modal=null;go('/trips/'+t.id);}catch(error){ui.modal={type:'import',text,error:error instanceof SyntaxError?'The JSON could not be read. Check brackets, quotes and commas.':error.message};render();}return;
 }
 if(form.hasAttribute('data-auth-form')){
  const fd=new FormData(form),email=String(fd.get('email')||'').trim().toLowerCase(),pw=String(fd.get('password')||''),register=form.dataset.authForm==='register';
  if(!/^\S+@\S+\.\S+$/.test(email)||pw.length<6){ui.authError='Enter a valid email and a password of at least 6 characters.';render();return;}
  if(register&&pw!==fd.get('confirm')){ui.authError='Your passwords do not match.';render();return;}
  if(register&&data.accounts[email]){ui.authError='This email already has a local account. Log in instead.';render();return;}
  const pending=data.pending,guestPlan=data.guestPlan;
  if(!data.accounts[email])data.accounts[email]={profile:{...defaultProfile(email),...(register?{name:String(fd.get('name')||'Traveler').trim()}: {})},trips:[],previews:[],task:null,workingPlan:null};
  data.session=email;data.pending=null;data.guestPlan=null;ui.authError='';ui.draftId=null;ui.planFrom=null;ui.displayPreview=null;profileEdit=null;
  ui.plan=pending&&guestPlan?cloned(guestPlan):account().workingPlan?cloned(account().workingPlan):freshPlan(account().profile);if(!pending){ui.draftId=account().workingDraftId||null;ui.planFrom=account().workingFrom||null;}persistPlan();
  if(pending?.action==='duplicate'){duplicate(pending.payload);return;}
  if(pending?.action==='import'){go('/trips');setTimeout(()=>openModal({type:'import',text:''}),0);return;}
  if(pending?.action==='save-draft'){go('/plan');setTimeout(()=>showToast('Your brief is restored. Save it when ready.'),0);return;}
  if(pending?.action==='generate'){go('/plan');setTimeout(()=>showToast('Your brief is restored. Review it and click Generate itinerary to continue.'),0);return;}
  go('/trips');
 }
});
window.addEventListener('hashchange',()=>{render();window.scrollTo({top:0,behavior:'instant'});});
window.addEventListener('keydown',e=>{
 if(e.target.matches('.auth-tabs [role="tab"]')&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const value=e.key==='Home'?'login':e.key==='End'?'register':ui.authTab==='login'?'register':'login';act('auth-tab',{dataset:{value}});document.getElementById(`auth-${value}-tab`)?.focus();}
 if(!ui.modal)return;if(e.key==='Escape'){closeModal();return;}if(e.key==='Tab'){const list=[...document.querySelector('[role="dialog"]').querySelectorAll('a[href],button:not(:disabled),input:not([type="hidden"]),textarea,select')],first=list[0],last=list.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}
});
window.addEventListener('storage',e=>{if(e.key!==STORE_KEY)return;const fresh=readStore();if(!fresh)return;const previous=data.session;data=fresh;if(previous!==data.session){ui.plan=account()?.workingPlan||freshPlan(account()?.profile);ui.draftId=null;ui.displayPreview=null;ui.modal=null;profileEdit=null;}render();});
setInterval(()=>{
 const t=task();if(!t||t.status!=='running')return;
 const finished=tickTask();
 const nav=document.getElementById('nav-task-slot');if(nav)nav.innerHTML=taskEntry();
 const progress=document.getElementById('generation-progress');if(progress)progress.outerHTML=progressSection();
 if(finished){const box=document.getElementById('result');if(box)box.innerHTML='<div class="flow-title"><span class="step-number">03</span><div><h2>Your itinerary</h2><p>Preview every day. Save it when it feels right.</p></div></div>'+resultContent();loadPhotos();showToast(t.status==='completed'?'Your itinerary preview is ready.':t.status==='clarification'?'Your travel brief needs a little clarification.':'Planning did not finish. Your brief is still available.');}
},600);
window.DayloomPrototype={version:'r7',getState:()=>cloned({session:data.session,account:account(),currentBrief:ui.plan}),buildProductInput:()=>productInput(ui.plan),importItinerary:raw=>{if(!account())throw Error('Log in before importing.');const t=normalizeImport(raw);account().previews.unshift(t);persist();go('/trips/'+t.id);return t.id;}};
if(!location.hash)location.hash='#/';render();
