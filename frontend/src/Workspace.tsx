import { useState } from 'react';
import { App } from './App';
import { DistrictSandbox as Sandbox } from './DistrictSandbox';
import './sandbox.css';
export function Workspace() {
  const [tab, setTab] = useState(location.hash === '#astana' ? 'astana' : 'sandbox');
  function select(next: string) { setTab(next); history.replaceState(null, '', `#${next}`); }
  return <><nav className="workspace-nav" aria-label="Режим города"><a className="workspace-brand" href="#sandbox" onClick={e => {e.preventDefault(); select('sandbox');}}><span>а.</span>аким<span className="brand-caption">ГОРОДСКАЯ ЛАБОРАТОРИЯ</span></a><div className="workspace-tabs"><button aria-pressed={tab === 'astana'} onClick={() => select('astana')}>Астана</button><button aria-pressed={tab === 'sandbox'} onClick={() => select('sandbox')}>Песочница <span>NEW</span></button></div><span className="workspace-note">Маленький город. Большие перемены.</span></nav>{tab === 'sandbox' ? <Sandbox/> : <App/>}</>;
}
