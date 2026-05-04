import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  Terminal, 
  LogOut, 
  Play, 
  Zap,
  CalendarDays,
  Plug,
  AlertTriangle,
  CheckCircle2,
  Settings,
  RefreshCw,
  Power
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

function App() {
  const [token, setToken] = useState(localStorage.getItem('heartbeat_token'));
  const [loading, setLoading] = useState(false);
  const [digests, setDigests] = useState([]);
  const [calendarRisk, setCalendarRisk] = useState([]);
  const [calendarConfig, setCalendarConfig] = useState({ provider: 'google', calendar_id: 'primary', lookahead_hours: 48, is_active: true });
  const [calendarErrors, setCalendarErrors] = useState([]);
  const [connectorStatuses, setConnectorStatuses] = useState([]);
  const [view, setView] = useState('dashboard');
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");

  const fallbackConnectors = [
    { type: 'calendar', name: 'Calendar', status: calendarConfig.is_active ? 'Active' : 'Disabled', is_active: calendarConfig.is_active, last_sync_status: 'Ready for next scan', summary: 'Schedule risk, cancellations, and meeting prep.', config: { provider: calendarConfig.provider, calendar_id: calendarConfig.calendar_id || 'primary', lookahead_hours: calendarConfig.lookahead_hours } },
    { type: 'slack', name: 'Slack', status: 'Missing token', is_active: true, last_sync_status: 'Needs setup before live sync', summary: 'Client and team conversation signal.', config: { channel_ids: 'Not set' } },
    { type: 'gmail', name: 'Gmail', status: 'Missing credentials', is_active: true, last_sync_status: 'Needs setup before live sync', summary: 'Customer email and revenue-risk signal.', config: { credentials_path: 'Not set' } },
    { type: 'github', name: 'GitHub', status: 'Missing token', is_active: true, last_sync_status: 'Needs setup before live sync', summary: 'Customer-facing delivery commitment signal.', config: { repo: 'Not set' } },
    { type: 'notion', name: 'Notion', status: 'Missing token', is_active: true, last_sync_status: 'Needs setup before live sync', summary: 'Tasks, docs, and milestone context.', config: { database_id: 'Not set' } },
  ];

  const connectors = connectorStatuses.length ? connectorStatuses : fallbackConnectors;
  const headerConnectors = ['Calendar', 'Slack', 'Gmail'].map((name) => (
    connectors.find((connector) => connector.name === name) || fallbackConnectors.find((connector) => connector.name === name)
  ));
  const readyConnectorCount = connectors.filter((connector) => ['Active', 'OK'].includes(connector.status)).length;
  const issueConnectorCount = connectors.filter((connector) => !['Active', 'OK'].includes(connector.status)).length;
  const connectorBadge = issueConnectorCount
    ? `${issueConnectorCount} need setup`
    : `${readyConnectorCount} active`;

  const getConnectorIcon = (status) => {
    if (status === 'Active' || status === 'OK') return <CheckCircle2 size={13} />;
    if (status === 'Disabled') return <Power size={13} />;
    return <AlertTriangle size={13} />;
  };

  const getConnectorDetails = (name) => {
    switch (name) {
      case 'Calendar':
        return calendarConfig.is_active
          ? 'Feeds schedule risk, cancellations, and meeting prep.'
          : 'Enable this connector to power meeting risk signals.';
      case 'Slack':
        return 'Connect Slack to capture client and team conversations.';
      case 'Gmail':
        return 'Connect Gmail for customer emails and revenue risk alerts.';
      case 'GitHub':
        return 'Connect GitHub only for delivery blockers tied to customer commitments.';
      case 'Notion':
        return 'Connect Notion for task and milestone context.';
      default:
        return 'Connector status unavailable.';
    }
  };

  const statusClass = (status) => {
    if (status === 'Active' || status === 'OK') return 'status-chip green';
    if (status === 'Disabled') return 'status-chip red';
    if (status === 'Unconfigured' || status?.startsWith('Missing')) return 'status-chip yellow';
    return 'status-chip';
  };

  useEffect(() => {
    if (token) {
      fetchDigests();
      fetchCalendarConfig();
      fetchCalendarRisk();
      fetchConnectorStatuses();
    }
  }, [token]);

  const fetchConnectorStatuses = async () => {
    try {
      const res = await axios.get(`${API_BASE}/connectors/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConnectorStatuses(res.data.connectors || []);
    } catch (err) {
      if (err.response?.status === 401) return handleLogout();
    }
  };

  const fetchCalendarConfig = async () => {
    try {
      const res = await axios.get(`${API_BASE}/calendar/config`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCalendarConfig(res.data);
    } catch (err) {
      if (err.response?.status === 401) return handleLogout();
    }
  };

  const fetchCalendarRisk = async () => {
    try {
      const res = await axios.get(`${API_BASE}/calendar`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCalendarRisk(res.data.meetings || []);
      setCalendarErrors(res.data.source_errors || []);
      if (res.data.calendar_config) {
        setCalendarConfig(res.data.calendar_config);
      }
    } catch (err) {
      if (err.response?.status === 401) handleLogout();
    }
  };

  const fetchDigests = async () => {
    try {
      const res = await axios.get(`${API_BASE}/digests`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDigests(res.data);
    } catch (err) {
      if (err.response?.status === 401) handleLogout();
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const endpoint = isRegister ? "/register" : "/token";
      let res;
      if (isRegister) {
        res = await axios.post(`${API_BASE}${endpoint}`, { email, password });
      } else {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        res = await axios.post(`${API_BASE}${endpoint}`, formData);
      }
      const newToken = res.data.access_token;
      setToken(newToken);
      localStorage.setItem('heartbeat_token', newToken);
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication unsuccessful");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem('heartbeat_token');
  };

  const triggerHeartbeat = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/heartbeat/trigger`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchDigests();
      await fetchCalendarRisk();
      await fetchConnectorStatuses();
    } catch (err) {
      setError("Unable to trigger heartbeat");
    } finally {
      setLoading(false);
    }
  };

  const updateCalendarConfig = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/calendar/config`, calendarConfig, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchCalendarConfig();
      await fetchCalendarRisk();
      await fetchConnectorStatuses();
      setView('connectors');
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to save calendar settings");
    } finally {
      setLoading(false);
    }
  };

  const handleCalendarConfigChange = (field, value) => {
    setCalendarConfig((prev) => ({ ...prev, [field]: value }));
  };

  const toggleConnector = async (connector) => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/connectors/${connector.type}/state`, {
        is_active: !connector.is_active
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (connector.type === 'calendar') {
        setCalendarConfig((prev) => ({ ...prev, is_active: !connector.is_active }));
      }
      await fetchConnectorStatuses();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to update connector state");
    } finally {
      setLoading(false);
    }
  };

  const openConnectorEditor = (connector) => {
    if (connector.type === 'calendar') {
      setView('connectors');
      return;
    }
    setError(`${connector.name} editing is not available yet. You can enable or disable it here.`);
  };

  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4 text-center">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full"
        >
          <div className="mb-4 flex justify-center">
            <div className="p-3 rounded-full bg-indigo-500/10 text-indigo-400">
              <Zap size={32} className="pulse" />
            </div>
          </div>
          <h1 className="text-2xl font-bold mb-1">Heartbeat</h1>
          <p className="text-secondary text-sm mb-6">Founder Intelligence</p>
          
          <form onSubmit={handleAuth} className="space-y-3">
            <input 
              type="email" 
              placeholder="Email" 
              className="w-full bg-white/5 border border-white/10 rounded-xl p-2.5 text-sm outline-none focus:border-indigo-500/50"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input 
              type="password" 
              placeholder="Password" 
              className="w-full bg-white/5 border border-white/10 rounded-xl p-2.5 text-sm outline-none focus:border-indigo-500/50"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button className="button-primary w-full py-3 text-sm">
              {loading ? "..." : isRegister ? "Create Account" : "Sign In"}
            </button>
          </form>

          {error && <p className="text-red-400 mt-3 text-xs">{error}</p>}
          
          <button 
            onClick={() => setIsRegister(!isRegister)} 
            className="mt-6 text-xs text-indigo-400 hover:text-indigo-300"
          >
            {isRegister ? "Already have an account? Sign In" : "Don't have an account? Register"}
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Mini Header */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-indigo-400" strokeWidth={3} />
          <span className="font-bold text-sm tracking-tight text-white">HEARTBEAT</span>
        </div>
        <button
          onClick={() => setView('connectors')}
          className={`header-status-badge ${issueConnectorCount ? 'needs-attention' : 'ready'}`}
          title="Connector readiness"
        >
          <Plug size={13} />
          <span>{connectorBadge}</span>
        </button>
        <div className="flex gap-2">
          <button 
            onClick={triggerHeartbeat} 
            disabled={loading} 
            className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition-colors"
            title="Trigger Manual Scan"
          >
            <Play size={14} fill="currentColor" className={loading ? "animate-spin" : ""} />
          </button>
          <button 
            onClick={handleLogout} 
            className="p-2 rounded-lg bg-white/5 text-secondary hover:text-white transition-colors"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex gap-2">
          <button
            onClick={() => setView('dashboard')}
            className={`tab-button ${view === 'dashboard' ? 'active' : ''}`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setView('connectors')}
            className={`tab-button ${view === 'connectors' ? 'active' : ''}`}
          >
            Connectors
          </button>
        </div>
        <span className="text-[10px] uppercase text-secondary/70">{view === 'dashboard' ? 'Live status' : 'Connector management'}</span>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {headerConnectors.map((connector) => {
          const status = connector.status;
          return (
            <span key={connector.name} className={statusClass(status)}>
              {connector.name}: {status}
            </span>
          );
        })}
      </div>

      {error && <div className="dashboard-error">{error}</div>}

      {/* Connector Readiness Strip */}
      <div className="flex justify-between items-center px-3 py-2 bg-indigo-500/5 rounded-xl mb-4 border border-indigo-500/10">
        <div className="flex items-center gap-2 text-[10px] font-bold text-indigo-300/80 uppercase">
          <Plug size={12} /> Connector Readiness
        </div>
        <div className="flex gap-2">
          <div className="status-dot green scale-75" title="Engine Ready"></div>
          <div className="status-dot green scale-75" title="AI Active"></div>
          <div className={`status-dot ${issueConnectorCount ? 'yellow' : 'green'} scale-75`} title={`${readyConnectorCount}/${connectors.length} connectors ready`}></div>
        </div>
      </div>

      {view === 'connectors' ? (
        <div className="flex-1 overflow-y-auto pr-1 space-y-3 custom-scrollbar">
          <div className="glass-panel p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-sm font-semibold">Connector management</div>
                <div className="text-[11px] text-secondary/70">Configure connectors and keep your founder signals fresh.</div>
              </div>
              <button
                onClick={() => setView('dashboard')}
                className="tab-button"
              >
                Back to dashboard
              </button>
            </div>
            <div className="connector-readiness-row">
              <div>
                <span className="connector-readiness-number">{readyConnectorCount}</span>
                <span className="connector-readiness-label">ready</span>
              </div>
              <div>
                <span className="connector-readiness-number attention">{issueConnectorCount}</span>
                <span className="connector-readiness-label">need setup</span>
              </div>
            </div>
          </div>

          <div className="connector-card-grid">
            {connectors.map((connector) => (
              <div key={connector.type} className="connector-card">
                <div className="connector-card-header">
                  <div className="connector-title">
                    <Plug size={15} />
                    <span>{connector.name}</span>
                  </div>
                  <span className={statusClass(connector.status)}>
                    {getConnectorIcon(connector.status)}
                    {connector.status}
                  </span>
                </div>

                <div className="connector-summary">{connector.summary || getConnectorDetails(connector.name)}</div>

                <div className="connector-meta">
                  <div>
                    <span>State</span>
                    <strong>{connector.is_active ? 'Enabled' : 'Disabled'}</strong>
                  </div>
                  <div>
                    <span>Last sync</span>
                    <strong>{connector.last_sync_status || 'Not scanned yet'}</strong>
                  </div>
                </div>

                <div className="connector-config-list">
                  {Object.entries(connector.config || {}).map(([key, value]) => (
                    <div key={key}>
                      <span>{key.replaceAll('_', ' ')}</span>
                      <strong>{String(value)}</strong>
                    </div>
                  ))}
                </div>

                <div className="connector-actions">
                  <button onClick={() => openConnectorEditor(connector)} title={`Edit ${connector.name}`}>
                    <Settings size={13} />
                    Edit
                  </button>
                  <button onClick={triggerHeartbeat} disabled={loading} title={`Reconnect ${connector.name}`}>
                    <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
                    Reconnect
                  </button>
                  <button onClick={() => toggleConnector(connector)} disabled={loading} title={`${connector.is_active ? 'Disable' : 'Enable'} ${connector.name}`}>
                    <Power size={13} />
                    {connector.is_active ? 'Disable' : 'Enable'}
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="glass-panel p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <div className="font-semibold">Calendar settings</div>
              <span className="text-[10px] uppercase text-secondary/70">Live configuration</span>
            </div>
            <div className="grid gap-3">
              <label className="text-[11px] text-secondary/80">
                Provider
                <select
                  value={calendarConfig.provider}
                  onChange={(e) => handleCalendarConfigChange('provider', e.target.value)}
                  className="select-field mt-1"
                >
                  <option value="google">Google</option>
                  <option value="mock">Mock</option>
                </select>
              </label>
              <label className="text-[11px] text-secondary/80">
                Calendar ID
                <input
                  type="text"
                  value={calendarConfig.calendar_id}
                  onChange={(e) => handleCalendarConfigChange('calendar_id', e.target.value)}
                  className="input-field mt-1"
                />
              </label>
              <label className="text-[11px] text-secondary/80">
                Credentials path
                <input
                  type="text"
                  value={calendarConfig.credentials_path || ''}
                  onChange={(e) => handleCalendarConfigChange('credentials_path', e.target.value)}
                  placeholder="e.g. /path/to/credentials.json"
                  className="input-field mt-1"
                />
              </label>
              <label className="text-[11px] text-secondary/80">
                Lookahead hours
                <input
                  type="number"
                  min="6"
                  max="168"
                  value={calendarConfig.lookahead_hours}
                  onChange={(e) => handleCalendarConfigChange('lookahead_hours', Number(e.target.value))}
                  className="input-field mt-1"
                />
              </label>
              <label className="flex items-center gap-2 text-[11px] text-secondary/80">
                <input
                  type="checkbox"
                  checked={calendarConfig.is_active}
                  onChange={(e) => handleCalendarConfigChange('is_active', e.target.checked)}
                  className="checkbox-field"
                />
                Enable calendar connector
              </label>
            </div>
            <button
              onClick={updateCalendarConfig}
              className="mt-4 rounded-full bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-400"
            >
              Save connector settings
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="glass-panel p-3 mb-4 border border-indigo-500/10">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <CalendarDays size={16} className="text-indigo-300" />
                Today's client schedule risk
              </div>
              <span className="text-[10px] uppercase text-secondary/70">Calendar</span>
            </div>
            {calendarErrors.length > 0 && (
              <div className="mb-3 rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-3 text-[11px] text-yellow-200">
                <strong className="block text-[10px] uppercase tracking-[0.2em] text-yellow-200">Calendar source issue</strong>
                {calendarErrors.map((err, idx) => (
                  <div key={idx}>{err}</div>
                ))}
              </div>
            )}

            {calendarRisk.length === 0 ? (
              <p className="text-[11px] text-secondary/70">No immediate meeting risks detected. Your calendar looks clear.</p>
            ) : (
              <div className="space-y-2">
                {calendarRisk.map((item, idx) => (
                  <div key={idx} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-[10px] uppercase tracking-[0.2em] text-secondary/70">{item.severity}</span>
                      <span className={`text-[10px] font-semibold ${item.severity === 'CRITICAL' ? 'text-red-300' : item.severity === 'URGENT' ? 'text-yellow-300' : 'text-green-300'}`}>
                        {item.severity}
                      </span>
                    </div>
                    <div className="text-sm font-medium">{item.message}</div>
                    <div className="text-[11px] text-secondary/70 mt-1">{item.action}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto pr-1 space-y-3 custom-scrollbar">
            <AnimatePresence mode='popLayout'>
              {digests.length === 0 ? (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center py-12 text-center text-secondary opacity-40"
                >
                  <Terminal size={32} className="mb-2" />
                  <p className="text-xs">No active signals.<br/>Trigger a scan to begin.</p>
                </motion.div>
              ) : (
                digests.map((d, index) => (
                  <motion.div 
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel p-3 border-l-2 border-l-indigo-500/50"
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-[9px] font-mono text-indigo-400/80">
                        {new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span className="text-[9px] text-secondary/60 font-bold uppercase tracking-widest">{d.source_type}</span>
                    </div>
                    <div className="text-[11px] leading-relaxed">
                      {d.content.split('\n').map((line, i) => {
                        if (line.includes('🔴')) return <div key={i} className="text-red-400 font-bold my-1 flex items-start gap-1">{line}</div>;
                        if (line.includes('🟡')) return <div key={i} className="text-yellow-400 font-bold my-1 flex items-start gap-1">{line}</div>;
                        if (line.includes('✅')) return <div key={i} className="text-green-400 font-bold my-1 flex items-start gap-1">{line}</div>;
                        if (line.includes('📌')) return <div key={i} className="mt-2 p-1.5 rounded bg-white/5 border border-white/5 text-[10px] italic">{line}</div>;
                        return <div key={i} className="text-white/80">{line}</div>;
                      })}
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </>
      )}

      <div className="mt-4 pt-2 border-t border-white/5 text-center">
        <p className="text-[9px] text-secondary/40 font-medium">Logged in as {email}</p>
      </div>
    </div>
  );
}

export default App;
