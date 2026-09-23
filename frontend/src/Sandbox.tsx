import { useEffect, useRef, useState } from 'react';
import { ConsultantPanel } from './ConsultantPanel';
import { SandboxCity } from './SandboxCity';
import { sandboxApi, loadSandbox, type SandboxCatalog, type SandboxState, type UpgradeId, type ZoneId } from './sandboxApi';

const SAVE_KEY = 'akim.sandbox.turns.v1';
const ZONE_LABELS = {transport: 'Дороги', air: 'Воздух', education: 'Образование'};
const ICONS = {bus: '↔', signals: '⑂', park: '♧', filter: '≈', school: '▥'};
function loadTurns(): UpgradeId[][] {
  try { const value = JSON.parse(localStorage.getItem(SAVE_KEY) ?? '[]'); return Array.isArray(value) ? value : []; } catch { return []; }
}
export function Sandbox() {
  const [catalog, setCatalog] = useState<SandboxCatalog | null>(null);
  const [city, setCity] = useState<SandboxState | null>(null);
  const [selectedZone, setSelectedZone] = useState<ZoneId>('transport');
  const [selected, setSelected] = useState<UpgradeId[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [retry, setRetry] = useState(0);
  const [paused, setPaused] = useState(false);
  const [resetPrompt, setResetPrompt] = useState(false);
  const [gameId, setGameId] = useState(0);
  const flight = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    setBusy(true); setError('');
    loadSandbox(loadTurns(), controller.signal).then(({catalog: config, city: state}) => {
      if (!controller.signal.aborted) {setCatalog(config); setCity(state);}
    }).catch(reason => {if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Не удалось загрузить город');})
      .finally(() => {if (!controller.signal.aborted) setBusy(false);});
    return () => { mounted.current = false; controller.abort(); };
  }, [retry]);
  async function advance(reset = false) {
    if (flight.current || !city && !reset) return;
    flight.current = true; setBusy(true); setError('');
    try {
      const fresh = reset ? await loadSandbox([]) : null;
      const next = fresh?.city ?? await sandboxApi.simulate([...city!.turns, [...selected]]);
      if (!mounted.current) return;
      if (fresh) setCatalog(fresh.catalog);
      setCity(next); setSelected([]); setResetPrompt(false);
      if (reset) {setGameId(old => old + 1); setNotice('Новая история города начинается.');}
      else setNotice(selected.length ? `Квартал завершён. Построено: ${selected.length}. Доход +${next.last_income}.` : `Прошёл квартал. Казна пополнилась на ${next.last_income}.`);
      try {localStorage.setItem(SAVE_KEY, JSON.stringify(next.turns));} catch {setNotice('Ход рассчитан, но браузер не разрешил сохранить прогресс.');}
    } catch (reason) {if (mounted.current) setError(reason instanceof Error ? reason.message : 'Не удалось выполнить ход');}
    finally {flight.current = false; if (mounted.current) setBusy(false);}
  }
  const spent = selected.reduce((sum, id) => sum + (catalog?.improvements.find(item => item.id === id)?.cost ?? 0), 0);
  const activeZone = city?.zones.find(zone => zone.id === selectedZone);
  const critical = city?.zones.filter(zone => zone.value < (catalog?.critical_threshold ?? 40)).length ?? 0;
  const context = city && catalog ? {city_name: city.city_name, quarter: city.quarter, budget: city.budget, score: city.score, zones: city.zones, built: city.built, selected_improvements: selected, available_improvements: catalog.improvements.filter(item => !city.built.includes(item.id)), last_changes: city.last_changes} : null;
  function toggle(id: UpgradeId) {
    setSelected(old => old.includes(id) ? old.filter(item => item !== id) : [...old, id]);
  }
  return <main className="sandbox-shell">
    <div className="sandbox-title"><div><div className="sandbox-eyebrow"><span/> СВОБОДНЫЙ РЕЖИМ · ВЫМЫШЛЕННЫЙ ГОРОД</div><h1>Новый Берег<span>.</span></h1><p>Город с характером. И с проблемами, которые ты можешь решить.</p></div><div className="quarter-pill"><span>ТВОЯ ИСТОРИЯ</span><strong>Квартал {city?.quarter ?? '—'}<small> / 13</small></strong></div></div>
    {error && <div className="sandbox-error" role="alert">{error}<button disabled={busy} onClick={() => setRetry(old => old + 1)}>Повторить</button><button disabled={busy} onClick={() => void advance(true)}>Начать новую игру</button></div>}
    <section className="sandbox-stats" aria-label="Показатели города"><div><span className="stat-icon purple">◈</span><div><label>Качество жизни</label><strong>{city?.score.toFixed(1) ?? '—'}<small> / 100</small></strong></div></div><div><span className="stat-icon red">!</span><div><label>Критические зоны</label><strong>{city ? critical : '—'}<small> / 3 зоны</small></strong></div></div><div><span className="stat-icon green">↗</span><div><label>Улучшений построено</label><strong>{city?.built.length ?? '—'}<small> / 5 проектов</small></strong></div></div><div><span className="stat-icon gold">◎</span><div><label>Городская казна</label><strong>{city?.budget ?? '—'}<small> ед.</small></strong></div></div></section>
    <div className="sandbox-layout"><section className="sandbox-map-card"><header><div><span className="sandbox-eyebrow">01 / ЖИВОЙ ГОРОД</span><h2>У каждого квартала своя история</h2></div><span className="live-chip"><i/> {city ? 'API ПОДКЛЮЧЁН' : 'ПОДКЛЮЧЕНИЕ'}</span></header>
      <div className="sandbox-scene"><SandboxCity built={city?.built ?? []} zones={city?.zones ?? []} selectedZone={selectedZone} onSelectZone={setSelectedZone} paused={paused}/><div className="scene-label-top">НОВЫЙ БЕРЕГ <span>изометрический макет</span></div><div className="scene-legend"><i/>Критическая зона <i/>Нуждается в развитии <i/>Цель достигнута</div><div className="scene-controls"><span>Перетаскивай для вращения · Колесо для масштаба</span><button onClick={() => setPaused(old => !old)} aria-pressed={paused}>{paused ? '▶ Продолжить' : 'Ⅱ Пауза'}</button></div></div>
      <div className="zone-cards" aria-label="Проблемные зоны">{city?.zones.map(zone => <button key={zone.id} className={selectedZone === zone.id ? 'selected' : ''} aria-pressed={selectedZone === zone.id} onClick={() => setSelectedZone(zone.id)}><div><span className={zone.value < 40 ? 'zone-dot critical' : zone.value >= 65 ? 'zone-dot good' : 'zone-dot warning'}/>{ZONE_LABELS[zone.id]}<strong>{zone.value}<small>/100</small></strong></div><p>{zone.name}</p><div className="zone-track"><i style={{width: `${zone.value}%`, background: zone.value < 40 ? '#ee806b' : zone.value >= 65 ? '#56a790' : '#daa45a'}}/></div></button>)}</div>
      {activeZone && <div className="zone-story"><span>↳</span><div><strong>{activeZone.name}</strong><p>{activeZone.value >= 65 ? 'Цель достигнута. Этот квартал стал комфортнее для жителей.' : activeZone.description} Выбирай связанные проекты справа.</p></div><b>{activeZone.value < 40 ? 'Критично' : activeZone.value >= 65 ? 'Благополучно' : 'Развивается'}</b></div>}
    </section><aside className="sandbox-projects"><div className="project-heading"><span className="sandbox-eyebrow">02 / ПЛАН НА КВАРТАЛ</span><h2>Что изменим?</h2><p>До трёх проектов за ход.<br/>Результат появится в следующем квартале.</p></div><div className="sandbox-budget"><span>Свободно после выбора</span><strong>{city ? city.budget - spent : '—'} <small>ед.</small></strong><div><i style={{width: `${city ? Math.max(0,(city.budget-spent)/Math.max(city.budget,1)*100) : 0}%`}}/></div></div>
      <div className="sandbox-upgrades">{catalog?.improvements.map(upgrade => {
        const built = city?.built.includes(upgrade.id); const checked = selected.includes(upgrade.id);
        const disabled = busy || !!built || city?.status !== 'playing' || !checked && (selected.length >= 3 || upgrade.cost > (city?.budget ?? 0) - spent);
        return <button key={upgrade.id} disabled={disabled} aria-pressed={checked} className={`upgrade-card ${checked ? 'chosen' : ''} ${built ? 'built' : ''} ${upgrade.zone_id === selectedZone ? 'related' : ''}`} onClick={() => toggle(upgrade.id)}><span className={`upgrade-icon ${upgrade.zone_id}`}>{ICONS[upgrade.id]}</span><span className="upgrade-copy"><small>{ZONE_LABELS[upgrade.zone_id]}</small><strong>{upgrade.name}</strong><span>{upgrade.description}</span><em>{built ? '✓ Построено' : `${upgrade.cost} ед. · +${upgrade.gain} к показателю`}</em></span><span className="upgrade-check">{built ? '✓' : checked ? '−' : '+'}</span></button>;
      })}</div>
      <div className="sandbox-turn"><div><span>{selected.length} проекта в плане</span><strong>−{spent} ед.</strong></div><button className="next-quarter" disabled={busy || !city || city.status !== 'playing'} onClick={() => void advance()}>{busy ? 'Город готовится…' : 'Следующий квартал'} <span>→</span></button><p>+{catalog?.quarterly_income ?? 12} ед. дохода после хода</p></div>
    </aside></div>
    <div className="sandbox-update" role="status">{city?.status === 'won' ? '✦ Город преобразился! Все три показателя достигли цели. Ты справился.' : city?.status === 'finished' ? 'Сезон завершён. Начни заново и попробуй другой план развития.' : notice || 'Твоя цель — поднять каждый показатель до 65 за 12 ходов. Начни с красных зон.'}</div>
    <ConsultantPanel key={gameId} sandbox context={context}/>
    <footer className="sandbox-footer"><span>Вымышленный город · игровые правила · прогресс хранится в этом браузере</span>{resetPrompt ? <span>Сбросить прогресс? <button disabled={busy} onClick={() => void advance(true)}>Да, начать заново</button><button onClick={() => setResetPrompt(false)}>Отмена</button></span> : <button onClick={() => setResetPrompt(true)}>↺ Новая игра</button>}</footer>
  </main>;
}
