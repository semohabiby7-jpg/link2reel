const CACHE='marsad-v1';
const ASSETS=['./','./index.html','./manifest.json','./icon.svg','https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800;900&display=swap'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(caches.match(e.request).then(cached=>{
    const fetched=fetch(e.request).then(res=>{if(res&&res.status===200){const clone=res.clone();caches.open(CACHE).then(c=>c.put(e.request,clone));}return res;}).catch(()=>{if(cached)return cached;if(e.request.mode==='navigate')return caches.match('./index.html');return new Response('Offline',{status:503});});
    return cached||fetched;
  }));
});
