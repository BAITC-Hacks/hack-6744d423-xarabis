import * as THREE from "three";
import type { CustomLayerInterface, CustomRenderMethodInput, Map as CityMap } from "maplibre-gl";
import type { DistrictId } from "./caseData";
import type { ProjectPreview } from "./projectPreview";
import { geographicPoint, localPoint, MERCATOR_ORIGIN, MERCATOR_SCALE, neighborhoodRoutes, parkTrees, prepareRoutes, sampleRoute, type ParkCollection, type RoadCollection, type TravelRoute, type XY } from "./cityLifeData";

export type LifeOptions = { districtId: DistrictId; playing: boolean; active: boolean; speed: number; projects: ProjectPreview[] };
export type LifeSummary = { vehicles: number; buses: number; trees: number; street: string; transitProject: boolean };
type Vehicle = { route: TravelRoute; direction: number; phase: number; speed: number; bus: boolean; color: number; project: boolean };
type Batch = { mesh: THREE.InstancedMesh; count: number };

/** Display-only miniature traffic. No density/score/forecast is derived here. */
export class CityLifeLayer implements CustomLayerInterface {
  readonly id = "akim-city-life";
  readonly type = "custom" as const;
  readonly renderingMode = "3d" as const;
  private map!: CityMap;
  private renderer!: THREE.WebGLRenderer;
  private camera = new THREE.Camera();
  private scene = new THREE.Scene();
  private modelMatrix = new THREE.Matrix4().makeTranslation(MERCATOR_ORIGIN[0], MERCATOR_ORIGIN[1],0).scale(new THREE.Vector3(MERCATOR_SCALE,-MERCATOR_SCALE,MERCATOR_SCALE));
  private matrix = new THREE.Matrix4();
  private object = new THREE.Object3D();
  private color = new THREE.Color();
  private batches: Record<string, Batch> = {};
  private routes: TravelRoute[];
  private neighborhood: TravelRoute[]=[];
  private vehicles: Vehicle[]=[];
  private time = 0;
  private previousTime = 0;
  private lastPaint = 0;
  private frame = 0;
  private mounted = false;
  private configurationKey = "";
  private signals: {x:number;y:number;angle:number;phase:number}[]=[];
  constructor(roads: RoadCollection, private parks: ParkCollection, private options: LifeOptions, private onSummary: (summary: LifeSummary)=>void) {
    this.routes=prepareRoutes(roads);
  }

  onAdd(map: CityMap, gl: WebGLRenderingContext | WebGL2RenderingContext) {
    this.map=map;
    this.renderer=new THREE.WebGLRenderer({ canvas: map.getCanvas(), context: gl as WebGL2RenderingContext, antialias:true });
    this.renderer.autoClear=false;
    this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.scene.add(new THREE.AmbientLight(0xffffff,2));
    const sunlight=new THREE.DirectionalLight(0xfff2d7,2.5);
    sunlight.position.set(-90,-100,200); this.scene.add(sunlight);
    const box=new THREE.BoxGeometry(1,1,1);
    const wheel=new THREE.CylinderGeometry(.42,.42,.30,10);
    const crown=new THREE.IcosahedronGeometry(1,1);
    const cone=new THREE.ConeGeometry(1,1,8); cone.rotateX(Math.PI/2);
    const trunk=new THREE.CylinderGeometry(1,1,1,7); trunk.rotateX(Math.PI/2);
    const disk=new THREE.CircleGeometry(1,16);
    const solid=(color:number)=>new THREE.MeshLambertMaterial({color});
    this.batch("body",box,solid(0xffffff),84);
    this.batch("glass",box,new THREE.MeshPhongMaterial({color:0x1d3c4d,shininess:65}),84);
    this.batch("roof",box,solid(0xffffff),84);
    this.batch("wheels",wheel,solid(0x202b30),336);
    this.batch("lamps",box,new THREE.MeshBasicMaterial({color:0xfff1b5}),168);
    this.batch("tails",box,new THREE.MeshBasicMaterial({color:0xff5c45}),168);
    this.batch("shadow",disk,new THREE.MeshBasicMaterial({color:0x152932,transparent:true,opacity:.20,depthWrite:false}),84);
    this.batch("trunks",trunk,solid(0x88654a),320);
    this.batch("crowns",crown,solid(0xffffff),320);
    this.batch("pines",cone,solid(0x3e775f),320);
    this.batch("posts",box,solid(0x465b61),42);
    this.batch("signalCases",box,solid(0x20363a),20);
    this.batch("signalLamps",box,new THREE.MeshBasicMaterial({color:0xffffff}),20);
    this.mounted=true;
    this.update(this.options);
    map.on("moveend",this.wake);
    document.addEventListener("visibilitychange",this.wake);
  }

  private batch(name:string,geometry:THREE.BufferGeometry,material:THREE.Material,capacity:number) {
    const mesh=new THREE.InstancedMesh(geometry,material,capacity);
    mesh.frustumCulled=false; mesh.count=0;
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.scene.add(mesh); this.batches[name]={mesh,count:0};
  }
  private put(name:string,x:number,y:number,z:number,sx:number,sy:number,sz:number,angle=0,color?:number) {
    const batch=this.batches[name];
    if(batch.count>=batch.mesh.instanceMatrix.count) return;
    this.object.position.set(x,y,z); this.object.rotation.set(0,0,angle); this.object.scale.set(sx,sy,sz); this.object.updateMatrix();
    batch.mesh.setMatrixAt(batch.count,this.object.matrix);
    if(color!==undefined) batch.mesh.setColorAt(batch.count,this.color.setHex(color));
    batch.count++;
  }
  private flush(names:string[]) {
    for(const name of names) {
      const {mesh,count}=this.batches[name]; mesh.count=count; mesh.instanceMatrix.needsUpdate=true;
      if(mesh.instanceColor) mesh.instanceColor.needsUpdate=true;
    }
  }
  private reset(names:string[]) { for(const name of names) this.batches[name].count=0; }

  update(options:LifeOptions) {
    this.options=options;
    if(!this.mounted) return;
    const localProjects=options.projects.filter((p)=>p.districtId===options.districtId);
    const key=`${options.districtId}:${localProjects.map(p=>p.id).sort().join(",")}`;
    if(key!==this.configurationKey) {
      this.configurationKey=key;
      this.neighborhood=neighborhoodRoutes(this.routes,options.districtId);
      this.vehicles=[];
      const palette=[0xe7ece9,0x527d93,0xdbae55,0xc46757,0x2f485a,0x90a499];
      const transit=localProjects.some((p)=>p.kind==="bus"||p.kind==="lrt");
      for(const [index,route] of this.neighborhood.entries()) {
        const count=Math.min(6,Math.max(2,Math.floor(route.length/75)));
        for(let car=0;car<count;car++) this.vehicles.push({route,direction:route.oneWay||car%2===0?1:-1,phase:(car+.25+(index%3)*.12)/count,speed:7.5+(index%5)*1.5,bus:car===0&&index%4===0,color:palette[(index+car)%palette.length],project:false});
        if(transit&&index<3) this.vehicles.push({route,direction:1,phase:.58,speed:8.5,bus:true,color:0x1f9c80,project:true});
      }
      this.vehicles=this.vehicles.slice(0,84);
      this.buildScenery(localProjects);
      this.updateRoadHighlight(transit);
      this.onSummary({vehicles:this.vehicles.length,buses:this.vehicles.filter(v=>v.bus).length,trees:this.batches.trunks.count,street:this.neighborhood[0]?.name??"Улица района",transitProject:transit});
    }
    this.previousTime=0;
    this.map.triggerRepaint();
    this.wake();
  }

  private updateRoadHighlight(transit:boolean) {
    const source=this.map.getSource("akim-life-roads") as {setData:(data:unknown)=>void}|undefined;
    source?.setData({type:"FeatureCollection",features:this.neighborhood.map((route,index)=>({type:"Feature",properties:{transit:transit&&index<3},geometry:{type:"LineString",coordinates:route.points.map(geographicPoint)}}))});
  }

  private buildScenery(projects:ProjectPreview[]) {
    const staticNames=["trunks","crowns","pines","posts","signalCases"];
    this.reset(staticNames); this.signals=[];
    const trees=parkTrees(this.parks,this.options.districtId);
    for(const project of projects.filter((p)=>["park","greenery"].includes(p.kind))) {
      const p=localPoint(project.coordinates);
      for(let i=0;i<18;i++) trees.push([p[0]+Math.cos(i*2.4)*(8+Math.sqrt(i)*7),p[1]+Math.sin(i*2.4)*(8+Math.sqrt(i)*7)]);
    }
    trees.slice(0,320).forEach(([x,y],i)=>{
      const height=7+(i%5)*1.5;
      this.put("trunks",x,y,height*.3,.8,.8,height*.6);
      if(i%4===0) this.put("pines",x,y,height*.75,4.4,4.4,height);
      else this.put("crowns",x,y,height*.78,4.5+(i%3),4.5+(i%3),height*.55,0,[0x688f54,0x468268,0x87a968,0x5b9672][i%4]);
    });
    // Lamps and signals are illustrative street furniture, not an OSM inventory.
    this.neighborhood.slice(0,10).forEach((route,index)=>{
      const p=sampleRoute(route,route.length*.42,1,7);
      this.put("posts",p.x,p.y,3.8,.38,.38,7.6);
      this.put("posts",p.x,p.y,7.6,2.4,.45,.3,p.angle);
      if(index%2===0) {
        const signal=sampleRoute(route,route.length*.66,1,5.5);
        this.put("posts",signal.x,signal.y,2.3,.3,.3,4.6);
        this.put("signalCases",signal.x,signal.y,4.8,.65,.65,1.6,signal.angle);
        this.signals.push({...signal,phase:index*1.7});
      }
    });
    this.flush(staticNames);
  }

  streetView() {
    const route=this.neighborhood.find((r)=>r.length>170)??this.neighborhood[0];
    if(!route) return;
    const p=sampleRoute(route,route.length*.5,1,0);
    this.map.flyTo({center:geographicPoint([p.x,p.y]),zoom:17.25,pitch:63,bearing:20,duration:window.matchMedia("(prefers-reduced-motion: reduce)").matches?0:850});
  }

  private canAnimate() { return this.mounted&&this.options.active&&this.options.playing&&!document.hidden&&this.map.getZoom()>=13.2; }
  private wake=()=>{
    if(!this.mounted) return;
    cancelAnimationFrame(this.frame); this.frame=0; this.previousTime=0;
    if(this.canAnimate()) this.frame=requestAnimationFrame(this.tick);
  };
  private tick=(now:number)=>{
    if(!this.canAnimate()) {this.previousTime=0;this.frame=0;return;}
    if(now-this.lastPaint>=33) {this.map.triggerRepaint();this.lastPaint=now;}
    this.frame=requestAnimationFrame(this.tick);
  };

  render(_gl:WebGLRenderingContext|WebGL2RenderingContext,args:CustomRenderMethodInput) {
    if(!this.mounted||this.map.getZoom()<13.2) return;
    const now=performance.now();
    if(this.canAnimate()&&this.previousTime) this.time+=Math.min(.1,(now-this.previousTime)/1000)*this.options.speed;
    this.previousTime=now;
    const names=["body","glass","roof","wheels","lamps","tails","shadow","signalLamps"];
    this.reset(names);
    for(const vehicle of this.vehicles) {
      const progress=(vehicle.phase*vehicle.route.length+this.time*vehicle.speed)%vehicle.route.length;
      const distance=vehicle.direction===1?progress:vehicle.route.length-progress;
      const p=sampleRoute(vehicle.route,distance,vehicle.direction,vehicle.route.oneWay?0:2.6);
      const scale=Math.min(1,progress/7,(vehicle.route.length-progress)/7)*1.35;
      const length=vehicle.bus?10.5:4.8,width=vehicle.bus?2.5:2,height=vehicle.bus?2.9:1.0;
      const z=vehicle.route.bridge?1.7:.28;
      const place=(name:string,dx:number,dy:number,h:number,sx:number,sy:number,sz:number,color?:number)=>{
        this.put(name,p.x+(Math.cos(p.angle)*dx-Math.sin(p.angle)*dy)*scale,p.y+(Math.sin(p.angle)*dx+Math.cos(p.angle)*dy)*scale,z+h*scale,sx*scale,sy*scale,sz*scale,p.angle,color);
      };
      place("shadow",0,0,.01,length*.65,width*.8,1);
      place("body",0,0,.75+height/2,length,width,height,vehicle.bus?(vehicle.project?0x168d71:0x258ab4):vehicle.color);
      place("glass",vehicle.bus?0:-.2,0,vehicle.bus?2.6:1.9,length*(vehicle.bus?.88:.55),width*.88,vehicle.bus?1.1:.7);
      place("roof",vehicle.bus?0:-.2,0,vehicle.bus?3.25:2.3,length*(vehicle.bus?.94:.51),width*.91,.15,vehicle.bus?0xf1f5e9:vehicle.color);
      for(const dx of [-length*.31,length*.31]) for(const dy of [-width*.53,width*.53]) place("wheels",dx,dy,.52,1,1,1);
      for(const dy of [-width*.32,width*.32]) {place("lamps",length*.51,dy,.9,.12,.43,.27);place("tails",-length*.51,dy,.9,.12,.4,.25);}
    }
    for(const signal of this.signals) {
      const phase=(this.time+signal.phase)%14;
      this.put("signalLamps",signal.x,signal.y,5.4,.76,.76,.35,0,phase<7?0x70edaa:phase<9?0xffd15c:0xf05d50);
    }
    this.flush(names);
    this.matrix.fromArray(args.defaultProjectionData.mainMatrix).multiply(this.modelMatrix);
    this.camera.projectionMatrix.copy(this.matrix);
    this.renderer.resetState(); this.renderer.render(this.scene,this.camera);
  }

  onRemove() {
    this.mounted=false;cancelAnimationFrame(this.frame);
    this.map.off("moveend",this.wake); document.removeEventListener("visibilitychange",this.wake);
    const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>();
    for(const {mesh} of Object.values(this.batches)) {geometries.add(mesh.geometry);for(const m of Array.isArray(mesh.material)?mesh.material:[mesh.material]) materials.add(m);mesh.dispose();}
    geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());this.scene.clear();this.renderer.dispose();
  }
}
