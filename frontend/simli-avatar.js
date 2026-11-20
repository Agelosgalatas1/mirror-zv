import {wavToPCM} from './simli-pcm.js';
const p=new URLSearchParams(location.search),mid=p.get('m'),turn=p.get('turn'),cid=p.get('cid'),view=p.get('v'),auto=p.get('auto')==='1';
const names={ceo:'Kate',sales:'Hank',finance:'Zahra'},status=document.querySelector('#status'),start=document.querySelector('#start'),stop=document.querySelector('#stop');
const video=document.querySelector('#simli-video'),audio=document.querySelector('#simli-audio'),placeholder=document.querySelector('#placeholder'),portrait=document.querySelector('#portrait');
document.querySelector('#employee-name').textContent=p.get('name')||names[mid]||'MIRROR';
let client=null,lease=null,ended=false,working=false,heartbeat=null,deadline=null,spoke=false;
const controller=new AbortController();
async function request(path,body){
  const options={credentials:'same-origin',signal:controller.signal};
  if(body!==undefined){options.method='POST';options.headers={'Content-Type':'application/json','X-Mirror-Request':'1'};options.body=JSON.stringify(body)}
  const r=await fetch(path,options);
  if(!r.ok){const e=await r.json().catch(()=>({}));if(r.status===403&&e.code==='mirror_access')parent.postMessage({type:'mirror:access-denied',mirror_id:mid,view_id:view},location.origin);throw Object.assign(Error(e.error||'Η σύνδεση avatar δεν είναι διαθέσιμη.'),{code:e.code})}
  return r;
}
function releaseLease(){
  if(lease)fetch(`/api/voice/${turn}/simli/${lease}/close`,{method:'POST',credentials:'same-origin',keepalive:true,headers:{'Content-Type':'application/json','X-Mirror-Request':'1'},body:'{}'}).catch(()=>{});
}
// fallback: the face failed before speaking, so the page plays the same checked answer as audio.
async function finish(message='Η συνεδρία βίντεο ολοκληρώθηκε.',fallback=false){
  if(ended)return;ended=true;
  if(fallback&&!spoke)parent.postMessage({type:'mirror:avatar-fallback',mirror_id:mid,view_id:view,turn},location.origin);
  clearInterval(heartbeat);clearTimeout(deadline);controller.abort();
  try{client?.ClearBuffer()}catch{}
  try{Promise.resolve(client?.stop()).catch(()=>{})}catch{}
  video.pause();audio.pause();video.srcObject=null;audio.srcObject=null;
  releaseLease();
  start.disabled=true;stop.disabled=true;placeholder.hidden=false;portrait.hidden=false;status.textContent=message;
}
async function begin(){
  if(working||ended)return;working=true;parent.postMessage({type:'mirror:avatar-start',mirror_id:mid,view_id:view},location.origin);start.disabled=true;status.textContent='Σύνδεση με το avatar…';
  try{
    const meta=await(await request(`/api/voice/${turn}`)).json();
    if(!meta.has_audio||meta.mirror_id!==mid||String(meta.conversation_id)!==cid)throw Error('Η απάντηση δεν ανήκει σε αυτή τη συζήτηση.');
    const pcm=wavToPCM(await(await request(`/api/voice/${turn}/audio`)).arrayBuffer());
    if(ended)return;
    // One click (send, replay or choosing 3D avatar) mints one bounded session. The only retry is a single
    // wait for the previous answer's session to finish its short stop grace; provider errors never retry.
    const mint=async()=>(await request(`/api/voice/${turn}/simli`,{conversation_id:cid})).json();
    let session;
    try{session=await mint()}
    catch(error){
      if(!auto||error.code!=='simli_busy')throw error;
      status.textContent='Ολοκληρώνεται η προηγούμενη απάντηση…';
      await new Promise(resolve=>setTimeout(resolve,3500));
      if(ended)return;
      session=await mint();
    }
    lease=session.lease_id;
    if(ended){releaseLease();return}
    const {SimliClient,LogLevel}=await import('./vendor/simli.bundle.js');
    if(ended)return;
    client=new SimliClient(session.session_token,video,audio,null,LogLevel.ERROR);
    client.on('error',()=>finish('Το avatar σταμάτησε. Η απάντηση συνεχίζει με ήχο.',true));
    client.on('stop',()=>finish());
    client.on('speaking',()=>{spoke=true;placeholder.hidden=true;portrait.hidden=true});
    deadline=setTimeout(()=>finish('Η σύνδεση βίντεο άργησε. Η απάντηση ακούγεται μόνο με ήχο.',true),20000);
    await client.start();
    if(ended){try{await client.stop()}catch{}return}
    // Revalidate after connection setup, before any checked answer leaves us.
    await request(`/api/voice/${turn}/simli/${lease}`);
    if(ended)return;
    stop.disabled=false;status.textContent='Η κάμερά σου παραμένει κλειστή.';
    heartbeat=setInterval(async()=>{try{await request(`/api/voice/${turn}/simli/${lease}`)}catch{finish('Η πρόσβαση στον ήχο έληξε ή άλλαξε.')}},3000);
    clearTimeout(deadline);
    deadline=setTimeout(()=>finish(),Math.min(session.max_seconds,session.audio_seconds+15)*1000);
    // Small bounded chunks of a single checked answer, never a live microphone.
    for(let offset=0;offset<pcm.length&&!ended;offset+=6000)client.sendAudioData(pcm.subarray(offset,offset+6000));
  }catch(error){await finish(error.name==='AbortError'?'Η συνεδρία ακυρώθηκε.':error.message,error.name!=='AbortError')}
}
if(names[mid]){portrait.src=`/simli-faces/${names[mid].toLowerCase()}.${names[mid]==='Kate'?'jpg':'avif'}`;portrait.alt='Συνθετικό πρόσωπο του AI αντιγράφου'}
if(!names[mid])status.textContent='Μη διαθέσιμο avatar.';
else if(!turn||!cid)status.textContent='Γράψε ή μίλησε στο chat. Το βίντεο ξεκινά μόνο για έτοιμη, ελεγμένη απάντηση.';
else if(!/^[\w-]{8,64}$/.test(turn)||!/^[\w-]{1,64}$/.test(cid))status.textContent='Μη έγκυρη συζήτηση.';
else{start.onclick=begin;if(auto)begin();else{status.textContent='Έτοιμη η φωνητική απάντηση. Πάτα Έναρξη βίντεο για να ξεκινήσει το avatar.';start.disabled=false}}
stop.onclick=()=>finish();
window.addEventListener('pagehide',()=>finish());
document.addEventListener('visibilitychange',()=>{if(document.hidden)finish('Η συνεδρία έκλεισε όταν έκρυψες την καρτέλα.')});
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===parent&&e.data==='mirror:stop')finish()});
