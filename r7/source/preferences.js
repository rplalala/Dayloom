/* Prototype preference controls own only their untouched generated sentences. */
const INTERESTS = ['City walks','History & culture','Art & museums','Nature','Local food','Photography','Family experiences','Free exploration'];
const PACES = ['Relaxed','Balanced','Rich'];
const TRANSPORTS = ['Walking','Public transit','Driving'];
const PREFERENCE_PROMPTS = {
  'City walks':'Enjoy neighborhood walks, local architecture and everyday city life.',
  'History & culture':'Explore historic districts, cultural landmarks and museums.',
  'Art & museums':'Visit art galleries and museums, with time to enjoy each stop.',
  'Nature':'Enjoy parks, waterfronts and gentle outdoor experiences.',
  'Local food':'Discover local food, with optional places to eat along the way.',
  'Photography':'Include scenic viewpoints and time for photography.',
  'Family experiences':'Include family-friendly experiences and time to rest.',
  'Free exploration':'Leave some unscheduled time for independent exploration.'
};
const PACE_PROMPTS = {
  Relaxed:'Travel pace: relaxed. Allow generous time at each stop and fewer transfers.',
  Balanced:'Travel pace: balanced. Balance the main sights with time to rest.',
  Rich:'Travel pace: rich. Include more experiences where time and connections allow.'
};
const PROGRESS_STEPS = ['Understand your trip','Explore your destination','Plan & check your days','Refine your itinerary','Prepare nearby ideas'];
function bindings(p){return (p.promptBindings||[]).filter(r=>p.notes.slice(r.start,r.end)===r.text);}
function detachControl(p,key){
  if(key==='pace')p.pace='';
  if(key==='transport')p.transport=[];
  if(key.startsWith('interest:'))p.interests=(p.interests||[]).filter(v=>'interest:'+v!==key);
}
function reconcileNotesEdit(p,next){
  const old=p.notes||''; if(old===next)return false;
  let start=0,suffix=0;
  while(start<old.length&&start<next.length&&old[start]===next[start])start++;
  while(suffix<old.length-start&&suffix<next.length-start&&old[old.length-1-suffix]===next[next.length-1-suffix])suffix++;
  const end=old.length-suffix,delta=next.length-old.length;
  p.promptBindings=bindings(p).map(r=>{
    if(r.end<=start)return r;
    if(r.start>=end)return {...r,start:r.start+delta,end:r.end+delta};
    detachControl(p,r.key); return null;
  }).filter(Boolean);
  p.notes=next; return true;
}
function removePrompt(p,key){
  const all=bindings(p),r=all.find(x=>x.key===key); if(!r)return;
  let start=r.start,end=r.end;
  if((start===0||p.notes[start-1]==='\n')&&(end===p.notes.length||p.notes[end]==='\n')){
    if(end<p.notes.length)end++;else if(start>0)start--;
  }
  p.notes=p.notes.slice(0,start)+p.notes.slice(end);
  p.promptBindings=all.filter(x=>x!==r).map(x=>x.start>=end?{...x,start:x.start-(end-start),end:x.end-(end-start)}:x);
}
function setPrompt(p,key,text){
  removePrompt(p,key); if(!text)return;
  if(p.notes.split('\n').includes(text))return;
  const sep=p.notes&&!p.notes.endsWith('\n')?'\n':'';
  const start=p.notes.length+sep.length;p.notes+=sep+text;
  p.promptBindings.push({key,start,end:start+text.length,text});
}
function selectInterest(p,value){
  if(p.interests.includes(value)){p.interests=p.interests.filter(v=>v!==value);removePrompt(p,'interest:'+value);}
  else{p.interests.push(value);setPrompt(p,'interest:'+value,PREFERENCE_PROMPTS[value]);}
}
function selectPace(p,value){
  const same=p.pace===value;p.pace=same?'':value;setPrompt(p,'pace',same?'':PACE_PROMPTS[value]);
}
function selectTransport(p,value){
  p.transport=p.transport.includes(value)?p.transport.filter(v=>v!==value):[...p.transport,value];
  setPrompt(p,'transport',p.transport.length?'Prefer '+p.transport.map(v=>v.toLowerCase()).join(' and ')+' where practical.':'');
}
function freshPlan(profile=null){
  const today=localToday();
  const p={destination:'',start_date:addDays(today,1),end_date:addDays(today,3),people:'2',activity_budget:'1000',currency:profile?.currency||'AUD',pace:'',transport:[],interests:[],required:'',exclusions:'',notes:profile?.notes||'',promptBindings:[]};
  for(const v of profile?.interests||[])selectInterest(p,v);
  if(profile?.pace)selectPace(p,profile.pace);else if(!profile)selectPace(p,'Balanced');
  for(const v of profile?.transport||[])selectTransport(p,v);
  return p;
}
function productInput(p){
  const text=[p.required?'Must include: '+p.required+'.':'',p.exclusions?'Please avoid: '+p.exclusions+'.':'',p.notes].filter(Boolean).join('\n');
  return {destination:p.destination,start_date:p.start_date,end_date:p.end_date,traveler_count:Number(p.people),budget:{amount:String(p.activity_budget),currency:p.currency},additional_preferences:text};
}
