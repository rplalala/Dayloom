/* PROTOTYPE r6: preserve r5 layout while checking the agreed Product flows.
   Persistence and background jobs are browser-local simulations, not real services. */
const ic=(name,size=20)=>`<svg class="ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]||ICONS.info}</svg>`;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cloned=v=>JSON.parse(JSON.stringify(v));
const array=v=>Array.isArray(v)?v:[];
const uid=(prefix='dayloom')=>prefix+'-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,8);
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const fmtDate=v=>String(v||'').slice(0,10).replaceAll('-','.');
const dt=v=>{const s=String(v||'').slice(0,10);return validDate(s)?new Intl.DateTimeFormat('en',{month:'short',day:'numeric',timeZone:'UTC'}).format(new Date(s+'T12:00Z')):'Date not set';};
const dayOf=v=>new Intl.DateTimeFormat('en',{weekday:'short',timeZone:'UTC'}).format(new Date(String(v).slice(0,10)+'T12:00Z'));
const clock=v=>/T(\d{2}:\d{2})/.exec(v||'')?.[1]||'—';
const minutes=v=>finite(v)?Math.ceil(Number(v)/60)+' min':'Time to confirm';
const distance=v=>!finite(v)?'Distance to confirm':Number(v)>=1000?(Number(v)/1000).toFixed(1)+' km':Math.round(Number(v))+' m';
const money=m=>m&&finite(m.amount)?esc(m.currency||'')+' '+Number(m.amount).toLocaleString('en',{maximumFractionDigits:2}):'To confirm';
function localToday(){const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');}
function addDays(s,n){const d=new Date(s+'T12:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);}
function validDate(s){return /^\d{4}-\d{2}-\d{2}$/.test(s||'')&&!Number.isNaN(Date.parse(s+'T12:00Z'))&&new Date(s+'T12:00Z').toISOString().slice(0,10)===s;}
const inclusiveDays=(a,b)=>validDate(a)&&validDate(b)?Math.round((Date.parse(b+'T12:00Z')-Date.parse(a+'T12:00Z'))/86400000)+1:0;
function safeURL(s){try{const u=new URL(s);return ['https:','http:'].includes(u.protocol)?u.href:'';}catch{return '';}}
const isFree=a=>a.time_use==='free_window'||a.activity_kind==='free_window';
const activityName=a=>a?.display_name||a?.place_name||a?.title||'Untitled activity';
const modeName=m=>({WALK:'Walking',TRANSIT:'Public transit',DRIVE:'Driving'}[m]||'Transport to confirm');
const modeIcon=m=>m==='WALK'?'walk':m==='DRIVE'?'car':m==='TRANSIT'?'bus':'info';
ICONS.car='<path d="m5 6-2 7v6h3v-3h12v3h3v-6l-2-7H5ZM3 13h18M7 10h10"/><circle cx="7" cy="14" r=".6"/><circle cx="17" cy="14" r=".6"/>';
ICONS.bus='<rect x="5" y="3" width="14" height="16" rx="3"/><path d="M5 11h14M8 19v2m8-2v2M8 15h.01M16 15h.01"/>';
ICONS.eye='<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>';
const href=(url,label,cls='',aria='')=>`<a class="${cls}" href="#${url}" ${aria?`aria-label="${esc(aria)}"`:''}>${label}</a>`;
const button=(label,action,cls='btn',extra='')=>`<button type="button" class="${cls}" data-action="${action}" ${extra}>${label}</button>`;
const navLink=(url,label,active)=>href(url,label,'nav-link '+(active?'selected':''));
const CURRENCIES=['AUD','CNY','USD','EUR','GBP','JPY','NZD','CAD','SGD','HKD','KRW','THB','CHF'];
const STORE_KEY='dayloom_prototype_r7';
function readStore(){try{const v=JSON.parse(localStorage.getItem(STORE_KEY));return v?.version===7&&v.accounts?v:null;}catch{return null;}}
let data=readStore()||{version:7,accounts:{},session:null,guestPlan:null,pending:null};
const defaultProfile=email=>({name:email.split('@')[0]||'Traveler',avatar:'',currency:'AUD',interests:[],pace:'Balanced',transport:[],notes:''});
const account=()=>data.session?data.accounts[data.session]||null:null;
if(data.session&&!account())data.session=null;
let ui={mobileNav:false,authTab:'login',tripsPage:1,tripsSort:'new',search:'',modal:null,activeRoute:'',plan:data.guestPlan||freshPlan(account()?.profile),draftId:null,planFrom:null,displayPreview:null,formError:'',polish:null,polishUndo:null,dayOpen:new Set(),detailTrip:null,dayFilter:'all',nearbyCollapsed:new Set(),nearbyInlineOpen:new Set(),nearbySelected:null,authError:'',storageWarning:false,taskNotice:''};
let toastTimer=0,photoObserver=null,modalFocus=null;
function persist(){try{localStorage.setItem(STORE_KEY,JSON.stringify(data));return true;}catch{ui.storageWarning=true;return false;}}
function persistPlan(){if(account()){account().workingPlan=cloned(ui.plan);account().workingDraftId=ui.draftId;account().workingFrom=ui.planFrom;}else data.guestPlan=cloned(ui.plan);persist();}
if(account()?.workingPlan){ui.plan=cloned(account().workingPlan);ui.draftId=account().workingDraftId||null;ui.planFrom=account().workingFrom||null;}
function route(){const [path,query='']=(location.hash.slice(1)||'/').split('?');return {path,params:new URLSearchParams(query)};}
function go(path){if(location.hash==='#'+path){render();window.scrollTo({top:0,behavior:'instant'});}else location.hash='#'+path;}
function showToast(text){const box=document.getElementById('toast');if(!box)return;box.textContent=text;box.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>box.classList.remove('show'),4200);}
const ownedTrips=()=>account()?.trips||[];
function findTrip(id){return [...ownedTrips(),...(account()?.previews||[]),...(!account()?SEEDS:[])].find(t=>t.id===id)||null;}
const allActivities=t=>array(t?.days).flatMap(d=>array(d.activities));
function nearbyEntries(t){
 const rows=[];
 for(const d of array(t.days))for(const a of array(d.activities))for(const n of array(a.nearby))
  rows.push({...n,anchor_activity_id:n.anchor_activity_id||a.activity_id,associated_day:n.associated_day||d.date});
 rows.push(...array(t.nearby),...array(t.reference_recommendations));
 const seen=new Set();
 return rows.filter(n=>{const k=JSON.stringify([n.place_id||n.source_place_id||n.place_name,n.associated_day,n.anchor_activity_id,n.reason]);if(seen.has(k))return false;seen.add(k);return true;});
}
const tripStats=t=>({dayCount:array(t.days).length,stopCount:allActivities(t).filter(a=>!isFree(a)).length,transfers:array(t.transfers).length,nearby:nearbyEntries(t).length});
function locateMap(p,t){return 'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent([p.place_name||p.title,p.location||p.area||t?.destination].filter(Boolean).join(', '))+(p.source_place_id?'&query_place_id='+encodeURIComponent(p.source_place_id):'');}
function photo(key='nature',cls='cover-img'){
 const p=PHOTOS[key]||PHOTOS.nature;
 return `<span class="media-wrap"><img class="${cls}" src="${FALLBACK[key]||FALLBACK.nature}" data-remote="${esc(p.url)}" alt="${esc(p.alt)}" loading="lazy"><span class="media-credit" data-credit="Unsplash">Illustration</span></span>`;
}
function placePhoto(p,cls='cover-img'){
 // This prototype never uses Unsplash to stand in for a specific place photograph.
 const f=FALLBACK[p.image_key]||FALLBACK.nature;
 return `<span class="place-photo-fallback" title="Photo unavailable. Illustration shown."><img class="${cls}" src="${f}" alt="Illustration for ${esc(activityName(p))}" loading="lazy"><span class="media-credit">Illustration</span></span>`;
}
function loadPhotos(){photoObserver?.disconnect();const load=img=>{const url=img.dataset.remote;if(!url)return;img.removeAttribute('data-remote');const pre=new Image();pre.onload=()=>{if(img.isConnected){img.src=url;const c=img.parentElement.querySelector('.media-credit');if(c)c.textContent=c.dataset.credit;}};pre.onerror=()=>{img.dataset.unavailable='true';};pre.src=url;};if('IntersectionObserver'in window){photoObserver=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){load(e.target);photoObserver.unobserve(e.target);}}),{rootMargin:'300px'});document.querySelectorAll('img[data-remote]').forEach(img=>photoObserver.observe(img));}else document.querySelectorAll('img[data-remote]').forEach(load);}
function avatar(profile,large=false){return `<span class="avatar${large?' large':''}">${profile?.avatar?`<img src="${esc(profile.avatar)}" alt="Your avatar">`:esc((profile?.name||'T').slice(0,2).toUpperCase())}</span>`;}
function formProblem(p){
 const today=localToday(),last=addDays(today,13);
 if(!p.destination.trim())return 'Enter a destination.';
 if(!validDate(p.start_date)||!validDate(p.end_date))return 'Choose valid start and end dates.';
 if(p.end_date<p.start_date)return 'The end date must be on or after the start date.';
 if(p.start_date<today||p.end_date>last)return `Choose travel dates between ${fmtDate(today)} and ${fmtDate(last)}. Historical trips remain readable.`;
 if(inclusiveDays(p.start_date,p.end_date)>10)return 'Plan up to 10 days, including both dates.';
 if(!Number.isInteger(Number(p.people))||Number(p.people)<1)return 'Enter at least one traveler.';
 if(!finite(p.activity_budget)||Number(p.activity_budget)<0)return 'Enter a non-negative whole-trip budget.';
 return '';
}
function capturePlan(){const form=document.getElementById('planForm');if(!form)return;const fd=new FormData(form);for(const k of ['destination','start_date','end_date','people','activity_budget','currency','required','exclusions'])ui.plan[k]=String(fd.get(k)??'').trim();if(reconcileNotesEdit(ui.plan,String(fd.get('notes')??''))){ui.polish=null;ui.polishUndo=null;}persistPlan();}
function task(){return account()?.task||null;}
function running(){return task()?.status==='running';}
function tickTask(){
 const t=task();if(!t||t.status!=='running')return false;
 const elapsed=Date.now()-t.started_at;
 const step=Math.min(4,Math.floor(elapsed/(t.duration/5)));
 if(elapsed<t.duration){t.step=step;return false;}
 if(t.scenario==='failed'||t.scenario==='clarification'){
   t.status=t.scenario;t.finished_at=Date.now();t.step=2;
 }else{
   const result=buildDemoItinerary(t.plan);account().previews.unshift(result);t.status='completed';t.preview_id=result.id;t.finished_at=Date.now();t.step=5;ui.displayPreview=result.id;
 }
 persist();return true;
}
function buildDemoItinerary(p){
 const seed=/sydney/i.test(p.destination)?SEEDS[0]:/kyoto/i.test(p.destination)?SEEDS[1]:/melbourne/i.test(p.destination)?SEEDS[2]:null;
 const days=[],transfers=[],count=inclusiveDays(p.start_date,p.end_date);
 for(let i=0;i<count;i++){
  const date=addDays(p.start_date,i),source=seed?.days[i%seed.days.length];
  const templates=source?cloned(source.activities):[{title:'Explore a local neighborhood',place_name:'Neighborhood exploration',category:'City discovery',start_time:'T10:00:00',end_time:'T11:30:00',image_key:'city'},{title:'Time to explore at your own pace',time_use:'free_window',start_time:'T13:00:00',end_time:'T15:00:00',image_key:'nature'}];
  const activities=templates.map((a,j)=>({...a,activity_id:`activity-${i}-${j}`,start_time:date+'T'+(/T(\d{2}:\d{2})/.exec(a.start_time)?.[1]||'10:00')+':00',end_time:date+'T'+(/T(\d{2}:\d{2})/.exec(a.end_time)?.[1]||'11:30')+':00',time_use:isFree(a)?'free_window':'scheduled',estimated_cost:null,location:a.location||p.destination,notes:'Confirm current opening hours, costs and access before visiting.',nearby:[]}));
  // Fixture transfers are explicitly created here, never inferred by the renderer.
  for(let j=0;j<activities.length-1;j++){const a=activities[j],b=activities[j+1];if(!isFree(a)&&!isFree(b))transfers.push({from_activity_id:a.activity_id,to_activity_id:b.activity_id,mode:null,provider_duration_seconds:null,distance_meters:null,reserve_seconds:0,validation_state:'UNKNOWN',estimate_kind:'unverified',unknowns:['No live route estimate is available in this prototype.'],preceding_end_time:a.end_time,following_start_time:b.start_time});}
  for(const n of array(seed?.nearby).filter(n=>n.associated_day===source?.date)){
   const sourceIndex=source.activities.findIndex(a=>a.activity_id===n.anchor_activity_id);
   if(sourceIndex>=0)activities[sourceIndex].nearby.push({...cloned(n),associated_day:date,anchor_activity_id:activities[sourceIndex].activity_id});
  }
  days.push({date,activities,weather:{status:'unavailable',forecast:null}});
 }
 return {id:uid('preview'),title:`${p.destination} · ${count}-day itinerary`,destination:p.destination,start_date:p.start_date,end_date:p.end_date,days,transfers,nearby:[],status:'preview',origin:'generated',cover:seed?.cover||'nature',created_at:new Date().toISOString(),description:'A little structure for your days, with room to discover.',people:Number(p.people),activity_budget:p.activity_budget,currency:p.currency,interests:cloned(p.interests),pace:p.pace,transport:cloned(p.transport),request:productInput(p),plan:cloned(p),policy_completion:'unassessed'};
}
function requireAccount(action,payload=null){if(account())return true;capturePlan();data.pending={action,payload,returnTo:location.hash.slice(1)||'/plan'};persist();ui.authError='';go('/login');return false;}
function beginGenerate(){
 capturePlan();if(!requireAccount('generate'))return;
 tickTask();if(running()){openModal({type:'busy'});return;}
 const error=formProblem(ui.plan);if(error){ui.formError=error;render();return;}
 ui.formError='';ui.displayPreview=null;account().task={id:uid('task'),status:'running',plan:cloned(ui.plan),started_at:Date.now(),duration:22000,step:0,scenario:'complete',seen:false};persist();render();document.getElementById('generation-progress')?.scrollIntoView({behavior:'smooth',block:'center'});
}
function saveResult(id){
 if(!requireAccount('save-preview',id))return;
 const existing=ownedTrips().find(t=>t.id===id);if(existing){go('/trips/'+id);return;}
 const a=account(),t=a.previews.find(t=>t.id===id);if(!t)return;
 t.status='saved';t.saved_at=new Date().toISOString();a.trips.unshift(t);a.previews=a.previews.filter(p=>p.id!==id);ui.displayPreview=null;persist();go('/trips/'+id);showToast('Saved to My trips.');
}
function saveDraft(){
 capturePlan();if(!requireAccount('save-draft'))return;
 if(!ui.plan.destination){ui.formError='Enter a destination before saving a draft.';render();return;}
 let d=ownedTrips().find(t=>t.id===ui.draftId&&t.status==='draft');
 if(!d){d={id:uid('draft'),title:ui.plan.destination+' · Planning draft',status:'draft',origin:'draft',created_at:new Date().toISOString(),days:[],transfers:[],nearby:[]};ownedTrips().unshift(d);ui.draftId=d.id;}
 Object.assign(d,{destination:ui.plan.destination,start_date:ui.plan.start_date,end_date:ui.plan.end_date,plan:cloned(ui.plan),people:Number(ui.plan.people),activity_budget:ui.plan.activity_budget,currency:ui.plan.currency,cover:/sydney/i.test(ui.plan.destination)?'sydney':'nature',description:'Your travel ideas, ready when you are.',updated_at:new Date().toISOString()});persistPlan();showToast('Draft saved.');
}
function replan(t){
 if(!t)return;const p=t.plan?cloned(t.plan):freshPlan();
 if(!t.plan){const req=t.request||{};Object.assign(p,{destination:req.destination||t.destination||'',start_date:req.start_date||t.start_date||'',end_date:req.end_date||t.end_date||'',people:String(req.traveler_count??t.people??''),activity_budget:String(req.budget?.amount??t.activity_budget??''),currency:req.budget?.currency||t.currency||'AUD',pace:'',transport:[],interests:[],required:'',exclusions:'',notes:req.additional_preferences||'',promptBindings:[]});}
 ui.plan=p;ui.draftId=t.status==='draft'?t.id:null;ui.planFrom=t.id;ui.displayPreview=null;ui.polish=null;ui.polishUndo=null;ui.formError='';persistPlan();go('/plan');
}
function duplicate(id){if(!requireAccount('duplicate',id))return;const source=findTrip(id)||SEEDS.find(t=>t.id===id);if(!source)return;const t=cloned(source);t.id=uid('trip');t.title=source.title+' (copy)';t.status=source.status==='draft'?'draft':'saved';t.source_origin=source.source_origin||source.origin;t.origin=t.source_origin==='imported'?'imported':'copy';t.created_at=new Date().toISOString();t.source_title=source.title;ownedTrips().unshift(t);persist();ui.modal=null;go('/trips');showToast('An independent copy was added to My trips.');}
