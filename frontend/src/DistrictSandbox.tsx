import {useEffect,useRef,useState} from 'react';
import {ConsultantPanel} from './ConsultantPanel';
import {DistrictCity} from './DistrictCity';
import {districtApi,loadDistrictGame,type DistrictCatalog,type DistrictGame,type DistrictId,type DistrictDecision} from './districtApi';
import {ratingCategory,ratingColor} from './traffic';
import './districts.css';
const SAVE='akim.sandbox.districts.v2';
const METRICS={transport:'Дороги',air:'Воздух',education:'Образование'};
const ICONS={bus:'↔',signals:'⑂',park:'♧',filter:'≈',school:'▥',repair:'⌁'};
function savedTurns():DistrictDecision[][]{try{const data=JSON.parse(localStorage.getItem(SAVE)??'[]');return Array.isArray(data)?data:[];}catch{return[];}}
export function DistrictSandbox(){
  const [catalog,setCatalog]=useState<DistrictCatalog|null>(null);
  const [city,setCity]=useState<DistrictGame|null>(null);
  const [active,setActive]=useState<DistrictId>('nura');
  const [plan,setPlan]=useState<DistrictDecision[]>([]);
  const [busy,setBusy]=useState(true),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [retry,setRetry]=useState(0),[paused,setPaused]=useState(false),[resetPrompt,setResetPrompt]=useState(false),[gameId,setGameId]=useState(0);
  const [hour,setHour]=useState(14),[autoTime,setAutoTime]=useState(true);
  const mounted=useRef(true),flight=useRef(false);
  useEffect(()=>{if(!autoTime)return;const timer=setInterval(()=>setHour(h=>(h+24/180)%24),1000);return()=>clearInterval(timer);},[autoTime]);
  useEffect(()=>{mounted.current=true;const controller=new AbortController();setBusy(true);setError('');
    loadDistrictGame(savedTurns(),controller.signal).then(data=>{if(!controller.signal.aborted){setCatalog(data.catalog);setCity(data.city);}})
      .catch(reason=>{if(!controller.signal.aborted)setError(reason instanceof Error?reason.message:'Не удалось загрузить город');})
      .finally(()=>{if(!controller.signal.aborted)setBusy(false);});
    return()=>{mounted.current=false;controller.abort();};
  },[retry]);
  async function nextQuarter(reset=false){
    if(flight.current||(!city&&!reset))return;flight.current=true;setBusy(true);setError('');
    try{const fresh=reset?await loadDistrictGame([]):null;const next=fresh?.city??await districtApi.simulate([...city!.turns,plan]);
      if(!mounted.current)return;if(fresh)setCatalog(fresh.catalog);setCity(next);setPlan([]);setResetPrompt(false);
      if(reset){setGameId(v=>v+1);setNotice('Начата новая история пяти районов.');}
      else setNotice(`Квартал завершён: выполнено проектов — ${plan.length}. Доход города +${next.last_income} ед.`);
      try{localStorage.setItem(SAVE,JSON.stringify(next.turns));}catch{setNotice('Ход рассчитан, но браузер не разрешил сохранить прогресс.');}
    }catch(reason){if(mounted.current)setError(reason instanceof Error?reason.message:'Не удалось выполнить ход');}
    finally{flight.current=false;if(mounted.current)setBusy(false);}
  }
  const district=city?.districts.find(d=>d.id===active);
  const spent=plan.reduce((sum,p)=>sum+(catalog?.improvements.find(i=>i.id===p.improvement_id)?.cost??0),0);
  const critical=city?.districts.filter(d=>d.score<40).length??0;
  const built=city?.districts.reduce((sum,d)=>sum+d.built.length,0)??0;
  const context=city&&catalog?{rules_version:city.rules_version,city_name:city.city_name,quarter:city.quarter,budget:city.budget,score:city.score,districts:city.districts,selected_district_id:active,selected_improvements:plan,available_improvements:catalog.improvements,last_changes:city.last_changes}:null;
  const hh=String(Math.floor(hour)).padStart(2,'0'),mm=String(Math.floor((hour%1)*60)).padStart(2,'0');
  function chooseTime(value:number){setHour(value);setAutoTime(false);}
  return <main className="sandbox-shell district-shell">
    <div className="sandbox-title"><div><div className="sandbox-eyebrow"><span/> ГОРОДСКАЯ ПЕСОЧНИЦА / ПЯТЬ РАЙОНОВ</div><h1>Один город. <span>Пять историй.</span></h1><p>Новый Берег · названия районов из кейса Астаны, вымышленная планировка.</p></div><div className="quarter-pill"><span>ПЛАН РАЗВИТИЯ</span><strong>Квартал {city?.quarter??'—'}<small> / 13</small></strong></div></div>
    {error&&<div className="sandbox-error" role="alert">{error}<button disabled={busy} onClick={()=>setRetry(v=>v+1)}>Повторить</button><button disabled={busy} onClick={()=>void nextQuarter(true)}>Начать новую игру</button></div>}
    <section className="sandbox-stats" aria-label="Показатели города"><div><span className="stat-icon purple">◈</span><div><label>Рейтинг города</label><strong>{city?.score.toFixed(1)??'—'}<small>/100</small></strong></div></div><div><span className="stat-icon red">!</span><div><label>Районов ниже 40</label><strong>{city?critical:'—'}<small>/5 районов</small></strong></div></div><div><span className="stat-icon green">↗</span><div><label>Построено проектов</label><strong>{city?built:'—'}<small>по всему городу</small></strong></div></div><div><span className="stat-icon gold">◎</span><div><label>Общая казна</label><strong>{city?.budget??'—'}<small>ед.</small></strong></div></div></section>
    <div className="district-layout"><section className="sandbox-map-card district-map-card"><header><div><span className="sandbox-eyebrow">01 / ГОРОД ЦЕЛИКОМ</span><h2>Выбери район на карте</h2></div><span className="live-chip"><i/>{city?'API ПОДКЛЮЧЁН':'ЗАГРУЗКА РАЙОНОВ'}</span></header>
      <div className="district-map" data-night={hour<6||hour>19}><DistrictCity districts={city?.districts??[]} selected={active} onSelect={setActive} paused={paused} hour={hour}/><div className="district-map-caption">НОВЫЙ БЕРЕГ <span>живой макет города</span></div><div className="district-time-badge">{hour<6||hour>19?'☾':'☀'} {hh}:{mm}</div><div className="district-map-hint">Вращение — перетаскиванием · Масштаб — колесом</div></div>
      <div className="district-map-toolbar"><div className="district-color-legend"><span>0</span><i/><span>100</span><small>Красный &lt;40 · Жёлтый 40–64 · Зелёный ≥65</small></div><button onClick={()=>setPaused(v=>!v)} aria-pressed={paused}>{paused?'▶ Движение':'Ⅱ Пауза машин'}</button></div>
      <div className="district-clock"><span>☀ День и ночь</span><button onClick={()=>chooseTime(14)} aria-pressed={!autoTime&&hour===14}>День</button><input aria-label="Время суток" type="range" min="0" max="23.99" step=".1" value={hour} onChange={e=>chooseTime(Number(e.target.value))}/><button onClick={()=>chooseTime(22)} aria-pressed={!autoTime&&hour===22}>Ночь</button><button className={autoTime?'active':''} onClick={()=>setAutoTime(v=>!v)} aria-pressed={autoTime}>Авто</button></div>
      <div className="district-cards" aria-label="Все районы">{city?.districts.map(d=><button key={d.id} onClick={()=>setActive(d.id)} aria-pressed={active===d.id} style={{'--district-color':ratingColor(d.score)} as React.CSSProperties}><span>{d.name}</span><strong>{d.score.toFixed(1)}</strong><i/><small>{ratingCategory(d.score)==='critical'?'Критический':ratingCategory(d.score)==='good'?'Благополучный':'Развивается'}</small></button>)}</div>
      <p className="district-rating-note">Рейтинг района — среднее дорог, воздуха и образования. Отдельный показатель ниже 40 остаётся критичным при любом общем рейтинге.</p>
    </section><aside className="sandbox-projects district-projects"><span className="sandbox-eyebrow">02 / ВЫБРАННЫЙ РАЙОН</span><div className="district-detail-title"><h2>{district?.name??'Загрузка…'}</h2><strong style={{color:ratingColor(district?.score??0)}}>{district?.score.toFixed(1)??'—'}<small>/100</small></strong></div><p className="district-description">{district?.description??'Показатели появятся после ответа API.'}</p>
      <div className="district-indicators">{district&&Object.entries(district.values).map(([id,value])=><div key={id}><span>{METRICS[id as keyof typeof METRICS]}</span><div><i style={{width:`${value}%`,background:ratingColor(value)}}/></div><strong>{value}</strong>{value<40&&<small>критично</small>}</div>)}</div>
      <div className="district-project-head"><h3>Улучшения района</h3><span>{city?city.budget-spent:'—'} ед. свободно</span></div>
      <div className="sandbox-upgrades">{catalog?.improvements.map(item=>{const done=district?.built.includes(item.id);const checked=plan.some(p=>p.district_id===active&&p.improvement_id===item.id);const disabled=busy||!!done||!district||city?.status!=='playing'||!checked&&(plan.length>=3||item.cost>(city?.budget??0)-spent);
        return <button key={item.id} className={`upgrade-card ${checked?'chosen':''} ${done?'built':''}`} disabled={disabled} aria-pressed={checked} onClick={()=>setPlan(old=>checked?old.filter(p=>!(p.district_id===active&&p.improvement_id===item.id)):[...old,{district_id:active,improvement_id:item.id}])}><span className={`upgrade-icon ${item.zone_id}`}>{ICONS[item.id]}</span><span className="upgrade-copy"><strong>{item.name}</strong><span>{item.description}</span><em>{done?'✓ Построено в районе':`${item.cost} ед. · +${item.gain} ${METRICS[item.zone_id].toLowerCase()}`}</em></span><span className="upgrade-check">{done?'✓':checked?'−':'+'}</span></button>;})}</div>
    </aside></div>
    <section className="district-plan" aria-label="План улучшений города"><div><span className="sandbox-eyebrow">03 / ПЛАН НА КВАРТАЛ</span><h3>{plan.length} из 3 проектов <small>· {spent} ед.</small></h3></div><div className="district-plan-items">{plan.length?plan.map(p=><div key={`${p.district_id}:${p.improvement_id}`}><strong>{city?.districts.find(d=>d.id===p.district_id)?.name}</strong><span>{catalog?.improvements.find(i=>i.id===p.improvement_id)?.name}</span><button disabled={busy} aria-label={`Убрать ${p.improvement_id} в ${p.district_id}`} onClick={()=>setPlan(old=>old.filter(i=>i!==p))}>×</button></div>):<p>Выбери район и проект. В одном ходе можно улучшить разные районы.</p>}</div><div className="district-next"><button className="next-quarter" disabled={busy||!city||city.status!=='playing'} onClick={()=>void nextQuarter()}>{busy?'Рассчитываем…':'Следующий квартал'} →</button><small>+{catalog?.quarterly_income??25} ед. после хода</small></div></section>
    <div className="sandbox-update" role="status">{city?.status==='won'?'✦ Все пять районов достигли цели! Можно начать новую историю.':city?.status==='finished'?'Сезон завершён. Попробуй другой план развития.':notice||'Цель: все три показателя каждого района — не ниже 65. Плохие дороги создают ямы и очереди; ремонт и транспортные проекты меняют движение.'}</div>
    <ConsultantPanel key={gameId} sandbox sandboxVersion="v2" context={context}/>
    <footer className="sandbox-footer"><span>Модель транспорта условная · освещение меняется независимо от игровых кварталов · прогресс сохраняется в браузере</span>{resetPrompt?<span>Сбросить пять районов? <button disabled={busy} onClick={()=>void nextQuarter(true)}>Да, начать заново</button><button onClick={()=>setResetPrompt(false)}>Отмена</button></span>:<button onClick={()=>setResetPrompt(true)}>↺ Новая игра</button>}</footer>
  </main>;
}
