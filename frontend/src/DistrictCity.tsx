import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {advanceTraffic,createTraffic,daylight,isSignalGreen,ratingColor,trafficProfile,type TrafficCar} from './traffic';
import type {DistrictId,DistrictState} from './districtApi';
import {ROAD_LENGTH,roadPoint,signalPost} from './roadGeometry';

type Props={districts:DistrictState[];selected:DistrictId;onSelect:(id:DistrictId)=>void;paused:boolean;hour:number};
const POSITIONS:Record<DistrictId,[number,number]>={esil:[-38,-21],almaty:[0,-21],saryarka:[38,-21],baikonur:[-20,16],nura:[20,16]};
const LOOP=ROAD_LENGTH;
export function DistrictCity(props:Props){
  const hostRef=useRef<HTMLDivElement>(null),labelsRef=useRef<HTMLDivElement>(null);
  const current=useRef(props);current.current=props;
  const view=useRef<{position:THREE.Vector3;target:THREE.Vector3;zoom:number}|null>(null);
  const [error,setError]=useState('');
  const layoutKey=props.districts.map(d=>`${d.id}:${d.built.join(',')}:${d.values.transport}`).join('|');
  useEffect(()=>{
    const host=hostRef.current,labels=labelsRef.current;if(!host||!labels)return;
    let renderer:THREE.WebGLRenderer;
    try{renderer=new THREE.WebGLRenderer({antialias:true});}catch{setError('WebGL недоступен. Выбери район в карточках под картой — расчёты и улучшения работают.');return;}
    setError('');renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    renderer.domElement.setAttribute('role','img');renderer.domElement.setAttribute('aria-label','Пять районов: Есиль, Алматы, Сарыарка, Байконур и Нура. Цветные границы, дороги, здания и транспорт.');host.appendChild(renderer.domElement);
    const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-90,90,75,-75,.1,500);
    camera.position.copy(view.current?.position??new THREE.Vector3(110,160,170));camera.zoom=view.current?.zoom??1;
    const controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(view.current?.target??new THREE.Vector3(0,0,-3));controls.enableDamping=true;controls.enablePan=false;controls.minZoom=.7;controls.maxZoom=2.5;controls.minPolarAngle=.3;controls.maxPolarAngle=1.05;controls.update();
    const ambient=new THREE.HemisphereLight(0xf6f5ff,0x959bb7,2.4);scene.add(ambient);
    const sun=new THREE.DirectionalLight(0xfff0d7,3);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-95,right:95,top:85,bottom:-85,near:1,far:300});sun.shadow.normalBias=.09;scene.add(sun);
    const palette=new Map<string,THREE.MeshStandardMaterial>();
    function mat(color:THREE.ColorRepresentation){const key=String(color);if(!palette.has(key))palette.set(key,new THREE.MeshStandardMaterial({color,roughness:.9}));return palette.get(key)!;}
    function box(w:number,h:number,d:number,x:number,y:number,z:number,color:THREE.ColorRepresentation,parent:THREE.Object3D=scene){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat(color));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
    const litWindow=new THREE.MeshStandardMaterial({color:0x94a8b8,emissive:0xffc773,emissiveIntensity:0});
    const lampMaterial=new THREE.MeshStandardMaterial({color:0xffefc0,emissive:0xffd27f,emissiveIntensity:0});
    const lampPools:THREE.Mesh[]=[];
    function tree(parent:THREE.Object3D,x:number,z:number,s=1){box(.18,1.2*s,.18,x,.9*s,z,0xa5937d,parent);const m=new THREE.Mesh(new THREE.IcosahedronGeometry(.85*s,1),mat(0x82aa94));m.position.set(x,1.7*s,z);m.castShadow=true;parent.add(m);}
    function building(parent:THREE.Object3D,x:number,z:number,w:number,d:number,h:number,color:number){box(w,h,d,x,.65+h/2,z,color,parent);box(w+.16,.2,d+.16,x,.75+h,z,0xf5f1e7,parent);for(let y=1.7;y<h;y+=1.4)for(let dx=-w/2+.75;dx<w/2-.2;dx+=1.2){const mesh=new THREE.Mesh(new THREE.BoxGeometry(.42,.62,.06),litWindow);mesh.position.set(x+dx,y,z+d/2+.04);parent.add(mesh);}for(let y=1.7;y<h;y+=1.4)for(let dz=-d/2+.7;dz<d/2-.2;dz+=1.2){const mesh=new THREE.Mesh(new THREE.BoxGeometry(.06,.62,.42),litWindow);mesh.position.set(x+w/2+.04,y,z+dz);parent.add(mesh);}}
    box(118,2,80,0,-.8,-3,0xd9dbe4);box(117,.18,79,0,.3,-3,0xe5e9e6);
    // Wide separating boulevards and an embankment make district edges explicit.
    box(116,.12,5,0,.47,-2.5,0x9aa3b0);box(4,.12,70,-19,.47,-3,0xa1a9b3);box(4,.12,70,19,.47,-3,0xa1a9b3);
    for(let x=-56;x<57;x+=4)box(1.8,.02,.12,x,.55,-2.5,0xeee7c9);
    box(115,.1,5,0,.45,33,0x87bfd1);box(115,.12,.6,0,.5,29.9,0xd7c7b0);
    for(let x=-54;x<55;x+=5)tree(scene,x,37,.8);
    const picks:THREE.Object3D[]=[];
    const districtVisuals:{id:DistrictId;group:THREE.Group;border:THREE.Mesh[];plate:THREE.Mesh;label:HTMLButtonElement;anchor:THREE.Vector3;cars:TrafficCar[];vehicles:THREE.Group[];smoke:THREE.Mesh[];signals:THREE.Mesh[];config:{quality:number;repaired:boolean;signals:boolean;loopLength:number}}[]=[];
    const colors=[0xd8dedb,0xe0d7ce,0xd6d2e3,0xd9dfca,0xccd9df];
    props.districts.forEach((district,index)=>{
      const [x,z]=POSITIONS[district.id],group=new THREE.Group();group.position.set(x,0,z);group.userData.districtId=district.id;scene.add(group);
      const color=new THREE.Color(ratingColor(district.score));const fill=color.clone().lerp(new THREE.Color(0xffffff),.8);
      const plate=new THREE.Mesh(new THREE.BoxGeometry(34,.28,29),new THREE.MeshStandardMaterial({color:fill,roughness:1}));plate.position.y=.48;plate.receiveShadow=true;group.add(plate);picks.push(plate);
      const borderMat=new THREE.MeshStandardMaterial({color,emissive:color,emissiveIntensity:.08});
      const border:THREE.Mesh[]=[];
      for(const [w,d,bx,bz] of [[34,.3,0,14.35],[34,.3,0,-14.35],[.3,29,-16.85,0],[.3,29,16.85,0]]){const m=new THREE.Mesh(new THREE.BoxGeometry(w,.28,d),borderMat);m.position.set(bx,.7,bz);group.add(m);border.push(m);}
      const repaired=district.built.includes('repair'),quality=district.values.transport;
      const roadColor=repaired?0x737e91:quality<40?0xa89587:0x8a939f;
      box(29,.12,3.3,0,.72,9,roadColor,group);box(29,.12,3.3,0,.72,-9,roadColor,group);box(3.3,.12,18,13,.72,0,roadColor,group);box(3.3,.12,18,-13,.72,0,roadColor,group);
      for(let v=0;v<LOOP;v+=3){const p=roadPoint(v,'center');const stripe=box(1,.02,.08,p.x,.8,p.z,0xeee7c7,group);stripe.rotation.y=p.angle;}
      if(!repaired){const damage=trafficProfile(quality).damage;for(let j=0;j<Math.ceil(damage*10);j++){const p=roadPoint(LOOP*(.45+j*.014),j%2);const pot=new THREE.Mesh(new THREE.CircleGeometry(.22+damage*.35,7),mat(0x5b5351));pot.rotation.x=-Math.PI/2;pot.position.set(p.x,.805,p.z);group.add(pot);const crack=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(p.x-.8,.81,p.z-.3),new THREE.Vector3(p.x-.2,.81,p.z+.25),new THREE.Vector3(p.x+.5,.81,p.z-.2)]),new THREE.LineBasicMaterial({color:0x5b5351}));group.add(crack);}}
      building(group,-6,3,4,3,5+index%3,colors[index]);building(group,0,3,3.5,3,7+(index===0?3:0),0xe4dfd5);
      building(group,6,3,3.6,3,4.5,0xd7cbd0);
      if(district.built.includes('school')){building(group,-6,-3,5.5,3.5,3.4,0xe6c682);box(5.7,.25,3.7,-6,4.2,-3,0xae8c87,group);box(3,.05,2,-6,.7,-5.8,0x8fad96,group);}else{box(6,.09,5,-6,.69,-3,0xd4c9b7,group);box(5.4,.4,.16,-6,.93,-5.4,0xc1aa8f,group);}
      if(district.built.includes('park')){box(5.8,.1,5,0,.7,-3,0xadc29a,group);for(const [tx,tz]of[[-1.6,-4.5],[1.6,-4.5],[-1.6,-1.5],[1.6,-1.5]])tree(group,tx,tz,.95);box(1.7,.4,.6,0,.95,-2.4,0xb59878,group);}else box(5.8,.08,5,0,.69,-3,0xdfd8bd,group);
      const filtered=district.built.includes('filter');building(group,6,-3,4,4,2.7,filtered?0xa7c5b8:0xc0b7b9);box(.7,4,.7,7,3,-4,0xb39283,group);
      const smoke:THREE.Mesh[]=[];for(let i=0;i<3;i++){const s=new THREE.Mesh(new THREE.IcosahedronGeometry(.55,1),new THREE.MeshStandardMaterial({color:0xa5a7b2,transparent:true,opacity:filtered?.025:(100-district.values.air)/180,depthWrite:false}));group.add(s);smoke.push(s);}
      for(const [tx,tz]of[[-10,5],[10,5],[-10,-5],[10,-5],[-4,12.3],[4,12.3]])tree(group,tx,tz,.65);
      for(const [lx,lz]of[[-11,11],[11,-11],[-11,-11],[11,11]]){box(.12,2.4,.12,lx,1.9,lz,0x8f959f,group);const bulb=new THREE.Mesh(new THREE.SphereGeometry(.22,8,8),lampMaterial);bulb.position.set(lx,3.1,lz);group.add(bulb);const glow=new THREE.Mesh(new THREE.CircleGeometry(2,20),new THREE.MeshBasicMaterial({color:0xffd581,transparent:true,opacity:0,depthWrite:false}));glow.rotation.x=-Math.PI/2;glow.position.set(lx,.83,lz);group.add(glow);lampPools.push(glow);}
      const signals:THREE.Mesh[]=[];
      for(const lane of [0,1])for(const f of [.25,.75]){const p=roadPoint(LOOP*f,lane),post=signalPost(LOOP*f,lane);box(.1,1.8,.1,post.x,.9,post.z,0x6a7180,group);const bulb=new THREE.Mesh(new THREE.SphereGeometry(.2,8,8),new THREE.MeshBasicMaterial({color:0xe76d68}));bulb.position.set(post.x,2,post.z);group.add(bulb);signals.push(bulb);const stop=box(.15,.022,1.1,p.x,.81,p.z,0xf2edde,group);stop.rotation.y=p.angle;}
      if(district.built.includes('bus')){box(23,.025,.65,0,.81,8.2,0xa397d0,group);box(2.5,1,.12,6,1.2,11.3,0xb6d3dd,group);box(2.8,.16,1.2,6,1.9,11.3,0x9682c5,group);}
      const trafficQuality=Math.min(100,quality+(district.built.includes('bus')?8:0));const cars=createTraffic(trafficQuality,LOOP);
      const vehicles=cars.map((car,i)=>{const v=new THREE.Group(),bus=district.built.includes('bus')&&i===0;group.add(v);box(bus?2.45:1.45,.45,.7,0,.95,0,bus?0x9985c7:[0xd9dce5,0xe8bc96,0x92aaa8,0xbca5c8][i%4],v);box(bus?1.9:.8,.3,.6,0,1.3,0,0xcad8df,v);for(const xx of [-.45,.45])for(const zz of [-.35,.35])box(.25,.25,.13,xx,.74,zz,0x515a68,v);for(const zz of [-.23,.23]){const head=new THREE.Mesh(new THREE.BoxGeometry(.08,.15,.12),lampMaterial);head.position.set(bus?1.24:.74,1,zz);v.add(head);}return v;});
      const label=document.createElement('button');label.type='button';label.className='district-pin';label.style.setProperty('--district-color',ratingColor(district.score));label.setAttribute('aria-label',`Выбрать район ${district.name}, рейтинг ${district.score}`);const name=document.createElement('span');name.textContent=district.name;const score=document.createElement('strong');score.textContent=district.score.toFixed(1);label.append(name,score);label.onclick=()=>current.current.onSelect(district.id);labels.appendChild(label);
      districtVisuals.push({id:district.id,group,border,plate,label,anchor:new THREE.Vector3(x,11,z-2),cars,vehicles,smoke,signals,config:{quality:trafficQuality,repaired,signals:district.built.includes('signals'),loopLength:LOOP}});
    });
    const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let down=[0,0];
    const onDown=(event:PointerEvent)=>{down=[event.clientX,event.clientY];};
    const onUp=(event:PointerEvent)=>{if(Math.hypot(event.clientX-down[0],event.clientY-down[1])>6)return;const r=host.getBoundingClientRect();pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(picks)[0];if(hit){const id=hit.object.parent?.userData.districtId as DistrictId;if(id)current.current.onSelect(id);}};
    renderer.domElement.addEventListener('pointerdown',onDown);renderer.domElement.addEventListener('pointerup',onUp);
    const resize=()=>{const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;const ratio=w/h,extent=67*Math.max(1,1.25/ratio);camera.left=-extent*ratio;camera.right=extent*ratio;camera.top=extent;camera.bottom=-extent;camera.updateProjectionMatrix();renderer.setSize(w,h);};const observer=new ResizeObserver(resize);observer.observe(host);resize();
    let frame=0,last=performance.now(),elapsed=0,visualHour=current.current.hour;const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
    const sky=new THREE.Color(),daySky=new THREE.Color(0xf0f1f7),nightSky=new THREE.Color(0x141c34);
    function draw(now:number){frame=requestAnimationFrame(draw);const dt=Math.min(.05,(now-last)/1000);last=now;const moving=!current.current.paused&&!reduceMotion;
      // Interpolate clock changes through the shortest arc across midnight.
      let hourDelta=((current.current.hour-visualHour+36)%24)-12;visualHour=(visualHour+hourDelta*Math.min(1,dt*2)+24)%24;
      const light=daylight(visualHour);sky.copy(nightSky).lerp(daySky,light.light);renderer.setClearColor(sky);ambient.intensity=.48+light.light*1.9;sun.intensity=.22+light.light*2.8;sun.color.setHex(light.light>.8?0xfff0d7:0xb1c2fc);sun.position.set(Math.sin(visualHour/24*Math.PI*2)*110,45+Math.max(0,light.sunHeight)*100,60);litWindow.emissiveIntensity=light.night*1.6;lampMaterial.emissiveIntensity=light.night*2.8;lampPools.forEach(pool=>(pool.material as THREE.MeshBasicMaterial).opacity=light.night*.18);
      for(const visual of districtVisuals){if(moving)visual.cars=advanceTraffic(visual.cars,visual.config,dt,elapsed);
        visual.cars.forEach((car,i)=>{const p=roadPoint(car.distance,car.lane);const v=visual.vehicles[i];v.position.set(p.x,0,p.z);v.rotation.y=p.angle;});
        visual.signals.forEach(signal=>(signal.material as THREE.MeshBasicMaterial).color.setHex(isSignalGreen(elapsed,visual.config.signals)?0x67c9a5:0xea716e));
        visual.smoke.forEach((smoke,i)=>{const t=(elapsed*.3+i*.8)%2.4;smoke.position.set(7+t*.6,5+t*1.2,-4);smoke.scale.setScalar(.6+t*.45);});
        const selected=visual.id===current.current.selected;visual.label.classList.toggle('selected',selected);visual.label.setAttribute('aria-pressed',String(selected));visual.border.forEach(border=>{border.scale.y=selected?2.1:1;(border.material as THREE.MeshStandardMaterial).emissiveIntensity=selected?.5:.08;});
        const p=visual.anchor.clone().project(camera);visual.label.style.left=`${(p.x+1)/2*host!.clientWidth}px`;visual.label.style.top=`${(1-p.y)/2*host!.clientHeight}px`;visual.label.style.visibility=p.z>1||p.z< -1?'hidden':'visible';
      }
      if(moving)elapsed+=dt;controls.update();renderer.render(scene,camera);
    }
    frame=requestAnimationFrame(draw);
    return()=>{view.current={position:camera.position.clone(),target:controls.target.clone(),zoom:camera.zoom};cancelAnimationFrame(frame);observer.disconnect();controls.dispose();renderer.domElement.removeEventListener('pointerdown',onDown);renderer.domElement.removeEventListener('pointerup',onUp);districtVisuals.forEach(v=>v.label.remove());const materials=new Set<THREE.Material>();scene.traverse(obj=>{if(obj instanceof THREE.Mesh||obj instanceof THREE.Line){obj.geometry.dispose();(Array.isArray(obj.material)?obj.material:[obj.material]).forEach(m=>materials.add(m));}});materials.forEach(m=>m.dispose());litWindow.dispose();lampMaterial.dispose();sun.shadow.dispose();renderer.dispose();renderer.domElement.remove();};
  },[layoutKey]);
  return <><div className="district-canvas" ref={hostRef}/><div className="district-pins" ref={labelsRef}/>{error&&<p className="webgl-error" role="alert">{error}</p>}</>;
}

