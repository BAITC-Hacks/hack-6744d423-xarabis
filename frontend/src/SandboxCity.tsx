import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { UpgradeId, Zone, ZoneId } from './sandboxApi';

type Props = {built: UpgradeId[]; zones: Zone[]; selectedZone: ZoneId; onSelectZone: (id: ZoneId) => void; paused: boolean};
const LOCATIONS: Record<ZoneId, [number, number]> = {transport: [3, 10], air: [21,-15], education: [-12,-14]};
export function SandboxCity(props: Props) {
  const container = useRef<HTMLDivElement>(null);
  const current = useRef(props); current.current = props;
  const [failure, setFailure] = useState('');
  const builtKey = props.built.join(',');
  useEffect(() => {
    const host = container.current;
    if (!host) return;
    let renderer: THREE.WebGLRenderer;
    try {renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});}
    catch {setFailure('3D недоступно. Включи WebGL в браузере. Играть можно через карточки районов ниже.'); return;}
    setFailure('');
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.7));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setClearColor(0xf5f4fa, 1);
    host.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label', 'Вымышленный 3D-город: река, кварталы, машины и три проблемные зоны');
    renderer.domElement.setAttribute('role', 'img');
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-50,50,35,-35,0.1,350);
    camera.position.set(80,87,96);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0,0,-1); controls.enableDamping = true; controls.enablePan = false;
    controls.minZoom = .65; controls.maxZoom = 2.4;
    controls.minPolarAngle = .3; controls.maxPolarAngle = 1.2; controls.update();
    scene.add(new THREE.HemisphereLight(0xffffff, 0xc3c5dc, 2.4));
    const sun = new THREE.DirectionalLight(0xfff8ef, 3.2); sun.position.set(-30,65,25); sun.castShadow = true;
    sun.shadow.mapSize.set(2048,2048); Object.assign(sun.shadow.camera, {left:-65,right:65,top:65,bottom:-65,near:1,far:160});
    sun.shadow.normalBias = .04; scene.add(sun);
    const materials = new Map<number, THREE.MeshStandardMaterial>();
    function material(color: number) {if (!materials.has(color)) materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.85})); return materials.get(color)!;}
    function box(w:number,h:number,d:number,x:number,y:number,z:number,color:number,parent:THREE.Object3D=scene) {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material(color)); mesh.position.set(x,y,z); mesh.castShadow=true;mesh.receiveShadow=true;parent.add(mesh);return mesh;
    }
    function tree(x:number,z:number,scale=1) {
      box(.3,1.5*scale,.3,x,.5+scale*.75,z,0xb09983);
      const foliage = new THREE.Mesh(new THREE.IcosahedronGeometry(1.2*scale,1),material(0x89b6a2));
      foliage.position.set(x,1.6*scale+.5,z); foliage.castShadow=true; scene.add(foliage);
    }
    function building(x:number,z:number,w:number,d:number,h:number,color:number) {
      const g = new THREE.Group();g.position.set(x,0,z);scene.add(g);
      box(w,h,d,0,h/2+.55,0,color,g);box(w+.25,.25,d+.25,0,h+.7,0,0xf8f5ec,g);
      box(w*.45,.6,d*.35,0,h+1.1,0,0xc8cace,g);
      for (let level=1;level<h-1;level+=1.6) {
        for(let a=-w/2+.9;a<w/2-.4;a+=1.6) box(.55,.8,.07,a,level+.8,d/2+.04,0x8193a2,g);
        for(let a=-d/2+.9;a<d/2-.4;a+=1.6) box(.07,.8,.55,w/2+.04,level+.8,a,0x9cacb6,g);
      }
      box(.9,1.3,.1,0,1.2,d/2+.07,0x7c8c9c,g);
      return g;
    }
    box(78,2,60,0,-.9,0,0xdedee9);box(77,.25,59,0,.2,0,0xebede8);
    // River, embankment and the two bridges make a legible little city.
    box(10,.15,59,-28,.4,0,0x97cbd6);box(.6,.2,59,-22.6,.53,0,0xe9dac2);box(.6,.2,59,-33.5,.53,0,0xe9dac2);
    for(let z=-25;z<28;z+=4) box(5,.018,.08,-28,.49,z,0xc5e5e9);
    const roads = [box(69,.15,5,3,.5,7,0x989aa8),box(57,.15,4,8,.5,-8,0xa1a2b0),box(4,.15,52,-1,.5,-1,0x9699a7),box(4,.15,52,29,.5,-1,0xa2a4b0)];
    roads.forEach(mesh=>mesh.castShadow=false);
    for(const z of [7,-8]) {box(12,.7,5,-28,.68,z,0xb2afc1);box(12,.65,.18,-28,1.2,z-2.4,0xf4f0e8);box(12,.65,.18,-28,1.2,z+2.4,0xf4f0e8);}
    for(let x=-34;x<36;x+=3) {box(1.25,.02,.1,x,.6,7,0xf6efcf); if(x>-20) box(1.25,.02,.1,x,.6,-8,0xf6efcf);}
    for(let z=-25;z<26;z+=3) for(const x of [-1,29]) box(.1,.02,1.3,x,.6,z,0xf6efcf);
    for(const x of [-1,29]) for(const z of [7,-8]) for(let p=-1.5;p<2;p+=.8) {
      box(.4,.03,1.3,x+p,.61,z-3.5,0xf6f4ed);box(1.1,.03,.4,x-3.1,.61,z+p,0xf6f4ed);
    }
    // Each block has a distinct skyline and a handful of street trees.
    building(-16,18,5,5,10,0xe3ddd1);building(-8,19,4.7,6,14,0xd7dbec);building(7,18,5,6,8,0xe8d5ca);box(10,.08,9,16,.53,17,0xe1ddcf);
    building(8,-1,5,6,11,0xc6d7d4);building(18,-1,5,6,7,0xe9ddca);building(-14,-1,8,5,5,0xc5c3dd);
    building(7,-19,5,7,9,0xe3e0d6);building(-14,-24,6,4,9,0xd8e0e0);building(-7,-23,4,5,13,0xe6d9d0);
    for(const [x,z] of [[-19,13],[-18,24],[0,26],[23,20],[24,13],[33,20],[33,-20],[-18,-6],[-20,-24],[4,-26],[12,25],[-35,-21],[-35,-16],[-35,17],[-35,23]]) tree(x,z,.85);
    // Factory and smoke shrink when filters are installed.
    building(20,-19,8,7,4.5,0xbdb9c9);
    box(1.4,7,1.4,23,4,-22,0xba8f81);box(1.4,5,1.4,19,3,-22,0xcbab93);
    const smoke: THREE.Mesh[]=[];
    for(let i=0;i<5;i++) {const mat=new THREE.MeshStandardMaterial({color:0xb2adbb,transparent:true,opacity:props.built.includes('filter')?.07:.32,depthWrite:false}); const m=new THREE.Mesh(new THREE.IcosahedronGeometry(1.05,1),mat);scene.add(m);smoke.push(m);}
    if(props.built.includes('filter')) {box(8,.5,7,20,5.4,-19,0x7fb8a4);box(2,2.5,2,25,1.8,-19,0xaacbba);}
    if(props.built.includes('park')) {
      box(10,.15,9,16,.54,17,0xb1c9a3);box(8,.06,1,16,.64,17,0xe6d4b7);
      for(const [x,z] of [[12,14],[20,14],[12,20],[20,20],[17,20]])tree(x,z,1.1);
      box(2,.4,.7,16,.9,14,0xb79778);
    }
    // The empty northern lot becomes a recognizable school campus.
    box(11,.12,10,-12,.54,-15,0xe8d9c5);
    if(props.built.includes('school')) {building(-12,-15,9,5,4.5,0xe4bf80);box(4,.4,6,-12,5.4,-15,0xc18b7e);box(6,.08,3,-12,.66,-11,0xa5baa6);box(.15,5,.15,-18,3,-13,0x9699a8);box(1.7,.9,.04,-17.2,4.8,-13,0x9279d1);}
    else {for(const x of [-16,-8])box(.12,1.1,.12,x,1.2,-12,0xb9a58c);box(8,.8,.12,-12,1.5,-12,0xd5c2a7);}
    if(props.built.includes('bus')) {box(54,.035,1.2,7,.6,8.7,0xa79cd3);box(5,2,.25,12,1.55,11,0xc5d8df);box(5,.15,1.5,12,2.6,11,0x8c82be);}
    if(props.built.includes('signals')) for(const x of [-3,31]) for(const z of [4,-11]) {box(.18,2.5,.18,x,1.8,z,0x7d8593);box(.5,.8,.4,x,3,z,0x525d6c);box(.24,.24,.07,x,2.85,z+.24,0x93d8ad);}
    const carColors=[0xebae89,0xd3dceb,0xf8f3e8,0x829cac,0xb6a5d0,0x97b9ad];
    const cars: {group:THREE.Group; phase:number; lane:number; bus:boolean}[]=[];
    for(let i=0;i<22;i++) {
      const bus=props.built.includes('bus')&&i%8===0;const g=new THREE.Group();scene.add(g);
      box(bus?3.4:1.7,.5,.85,0,.7,0,bus?0x8f83c8:carColors[i%carColors.length],g);box(bus?2.8:.9,.42,.72,0,1.14,0,0xe5edf1,g);
      for(const x of [-.55,.55])for(const z of [-.44,.44])box(.3,.3,.13,x,.48,z,0x58606c,g);
      cars.push({group:g,phase:i/22,lane:i%2,bus});
    }
    const rings: Record<string,THREE.Mesh>={};const dots: THREE.Mesh[]=[];
    for(const id of ['transport','air','education'] as ZoneId[]) {
      const [x,z]=LOCATIONS[id];const ring=new THREE.Mesh(new THREE.RingGeometry(3.5,3.75,64),new THREE.MeshBasicMaterial({color:0xee8873,transparent:true,opacity:.65,side:THREE.DoubleSide,depthWrite:false}));ring.rotation.x=-Math.PI/2;ring.position.set(x,.68,z);scene.add(ring);rings[id]=ring;
      const pin=new THREE.Mesh(new THREE.SphereGeometry(.7,16,12),new THREE.MeshStandardMaterial({color:0xea806c}));pin.position.set(x,4,z);pin.userData.zone=id;scene.add(pin);dots.push(pin);
      box(.08,3,.08,x,2.3,z,0xd3a396);
    }
    const raycaster=new THREE.Raycaster();const pointer=new THREE.Vector2();let down=[0,0];
    const pointerDown=(e:PointerEvent)=>{down=[e.clientX,e.clientY];};
    const click=(e:PointerEvent)=>{if(Math.hypot(e.clientX-down[0],e.clientY-down[1])>6)return;const rect=host.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects(dots)[0];if(hit)current.current.onSelectZone(hit.object.userData.zone);};
    renderer.domElement.addEventListener('pointerdown',pointerDown);renderer.domElement.addEventListener('pointerup',click);
    const resize=()=>{const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;const extent=39;camera.left=-extent*w/h;camera.right=extent*w/h;camera.top=extent;camera.bottom=-extent;camera.updateProjectionMatrix();renderer.setSize(w,h);};
    const observer=new ResizeObserver(resize);observer.observe(host);resize();
    let frame=0,last=performance.now(),elapsed=0;
    const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const animate=(now:number)=>{
      frame=requestAnimationFrame(animate);const dt=Math.min((now-last)/1000,.05);last=now;if(!current.current.paused&&!reduceMotion)elapsed+=dt;
      const transport=current.current.zones.find(z=>z.id==='transport')?.value??28;
      const speed=.011+transport*.00025;
      for(const car of cars) {const t=((elapsed*speed+car.phase)%1)*4;const x0=-19+car.lane*1.3,x1=28-car.lane*1.3,z0=-7+car.lane*1.1,z1=6-car.lane*1.1;
        if(t<1){car.group.position.set(x0+(x1-x0)*t,0,z1);car.group.rotation.y=0;}
        else if(t<2){car.group.position.set(x1,0,z1-(z1-z0)*(t-1));car.group.rotation.y=Math.PI/2;}
        else if(t<3){car.group.position.set(x1-(x1-x0)*(t-2),0,z0);car.group.rotation.y=Math.PI;}
        else {car.group.position.set(x0,0,z0+(z1-z0)*(t-3));car.group.rotation.y=-Math.PI/2;}
      }
      smoke.forEach((mesh,i)=>{const t=(elapsed*.3+i*.6)%3;mesh.position.set(23+t*.9,7.9+t*2,-22);mesh.scale.setScalar(.7+t*.5);});
      for(const zone of current.current.zones){const ring=rings[zone.id];const color=zone.value<40?0xeb826c:zone.value>=65?0x66b195:0xd7ae63;(ring.material as THREE.MeshBasicMaterial).color.setHex(color);const selected=zone.id===current.current.selectedZone;ring.scale.setScalar(selected?1.2+Math.sin(elapsed*2)*.05:1);const pin=dots.find(dot=>dot.userData.zone===zone.id)!;(pin.material as THREE.MeshStandardMaterial).color.setHex(color);}
      controls.update();renderer.render(scene,camera);
    };frame=requestAnimationFrame(animate);
    return ()=>{cancelAnimationFrame(frame);observer.disconnect();controls.dispose();renderer.domElement.removeEventListener('pointerdown',pointerDown);renderer.domElement.removeEventListener('pointerup',click);const mats=new Set<THREE.Material>();scene.traverse(obj=>{if(obj instanceof THREE.Mesh){obj.geometry.dispose();(Array.isArray(obj.material)?obj.material:[obj.material]).forEach(m=>mats.add(m));}});mats.forEach(m=>m.dispose());renderer.dispose();renderer.domElement.remove();};
  }, [builtKey]);
  return <><div className="sandbox-canvas" ref={container}/>{failure&&<p className="webgl-error" role="alert">{failure}</p>}</>;
}

