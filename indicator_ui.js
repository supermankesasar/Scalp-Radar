'use strict';
(()=>{
 const form=document.getElementById('indicatorForm');
 const status=document.getElementById('indicatorStatus');
 const save=document.getElementById('indicatorSave');
 const reset=document.getElementById('indicatorReset');
 if(!form)return;
 let defaults=null;
 const setStatus=(msg,bad=false)=>{status.textContent=msg;status.style.color=bad?'#ff9c9c':'#b7d4e5'};
 const fill=values=>{for(const [key,value] of Object.entries(values)){const el=form.elements.namedItem(key);if(el)el.value=value;}};
 async function load(){
   try{
     const response=await fetch('/api/settings',{cache:'no-store'});
     const data=await response.json();
     if(!response.ok)throw Error(data.error||'Tidak bisa membaca pengaturan');
     defaults=data.defaults;fill(data.values);
     setStatus('Aktif: revisi '+data.revision+(data.updated_ms?' · tersimpan':' · default'));
   }catch(e){setStatus('Gagal memuat: '+e.message,true);}
 }
 async function persist(values){
   save.disabled=true;reset.disabled=true;setStatus('Menyimpan...');
   try{
     const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
       cache:'no-store',body:JSON.stringify(values)});
     const text=await response.text();
     let data;try{data=JSON.parse(text)}catch{data={error:text}}
     if(!response.ok)throw Error(data.error||('HTTP '+response.status));
     defaults=data.defaults;fill(data.values);
     setStatus('Tersimpan revisi '+data.revision+' · berlaku pada scan berikutnya');
   }catch(e){setStatus('Gagal menyimpan: '+e.message,true);}
   finally{save.disabled=false;reset.disabled=false;}
 }
 form.addEventListener('submit',e=>{
   e.preventDefault();
   if(!form.reportValidity())return;
   const values={};
   for(const input of form.querySelectorAll('input[name]'))values[input.name]=Number(input.value);
   persist(values);
 });
 reset.addEventListener('click',()=>{if(defaults)persist(defaults);else setStatus('Default belum tersedia',true)});
 load();
})();
