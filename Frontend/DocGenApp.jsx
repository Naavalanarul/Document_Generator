import React, { useState, useEffect, useRef, useCallback } from 'react';

/* ═══════════════════════════════════════════════════════════════════════════
   CSS CUSTOM PROPERTIES & GLOBAL STYLES
   ═══════════════════════════════════════════════════════════════════════════ */
const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
      --color-sidebar-bg: #1a1a1a;
      --color-sidebar-hover: #2a2a2a;
      --color-sidebar-active: #333333;
      --color-sidebar-text: #e5e5e5;
      --color-sidebar-text-muted: #888888;
      --color-main-bg: #ffffff;
      --color-surface: #f7f7f8;
      --color-border: #e5e5e5;
      --color-accent: #d97757;
      --color-accent-hover: #c4673f;
      --color-accent-light: rgba(217, 119, 87, 0.1);
      --color-text-primary: #0d0d0d;
      --color-text-muted: #6b7280;
      --color-text-secondary: #374151;
      --color-error: #ef4444;
      --color-error-bg: #fef2f2;
      --color-success: #22c55e;
      --color-success-bg: #f0fdf4;
      --radius-card: 12px;
      --radius-input: 8px;
      --shadow-light: 0 1px 3px rgba(0,0,0,0.08);
      --shadow-composer: 0 -1px 8px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.08);
      --font-family: 'Inter', system-ui, -apple-system, sans-serif;
      --sidebar-width: 260px;
      --main-max-width: 720px;
      --drawer-width: 380px;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html, body, #root {
      height: 100%;
      font-family: var(--font-family);
      color: var(--color-text-primary);
      background: var(--color-main-bg);
      -webkit-font-smoothing: antialiased;
    }

    button, input, select, textarea {
      font-family: inherit;
      font-size: inherit;
    }

    button { cursor: pointer; }

    *:focus-visible {
      outline: 2px solid var(--color-accent);
      outline-offset: 2px;
    }

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    @keyframes slideInRight {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
    @keyframes slideInUp {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
      }
    }
  `}</style>
);


/* ═══════════════════════════════════════════════════════════════════════════
   CONSTANTS & HELPERS
   ═══════════════════════════════════════════════════════════════════════════ */
const API_BASE = 'http://localhost:8000';
const MAX_FILE_SIZE = 50 * 1024 * 1024;

const DEFAULT_PARAMS = {
  chunk_size: 3000,
  overlap: 300,
  chunk_summary_length: 200,
  temperature: 0.2,
  max_retries: 3,
  json_mode: true,
  request_timeout: 300,
  tone: 'Neutral',
  max_sections: null,
  max_slides: null,
  bullets_min: 3,
  bullets_max: 7,
  include_speaker_notes: true,
  sub_bullet_depth: '1 level',
};

function loadFromStorage(key, fallback) {
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : fallback;
  } catch { return fallback; }
}

function saveToStorage(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

function formatTime(seconds) {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

function formatTimestamp(ts) {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return d.toLocaleDateString();
}


/* ═══════════════════════════════════════════════════════════════════════════
   SVG ICONS
   ═══════════════════════════════════════════════════════════════════════════ */
const Icons = {
  logo: (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  plus: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  settings: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  file: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
      <polyline points="13 2 13 9 20 9" />
    </svg>
  ),
  link: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  ),
  search: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  download: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  ),
  x: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  chevronDown: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  chevronRight: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  refresh: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  ),
  monitor: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  ),
  cloud: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
    </svg>
  ),
  alertTriangle: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  copy: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  ),
  send: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  ),
  externalLink: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  ),
  check: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
};

const Spinner = ({ size = 16, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ animation: 'spin 1s linear infinite', flexShrink: 0 }}>
    <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" strokeDasharray="32" strokeLinecap="round" opacity="0.25" />
    <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" strokeDasharray="32" strokeDashoffset="20" strokeLinecap="round" />
  </svg>
);


/* ═══════════════════════════════════════════════════════════════════════════
   CUSTOM UI PRIMITIVES
   ═══════════════════════════════════════════════════════════════════════════ */

function SliderInput({ label, description, value, onChange, min, max, step = 1, unit = '', onReset, defaultValue }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <label style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text-primary)' }}>{label}</label>
        {onReset && value !== defaultValue && (
          <button onClick={onReset} title="Reset to default" aria-label={`Reset ${label} to default`}
            style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', padding: 2, display: 'flex', cursor: 'pointer' }}>
            {Icons.refresh}
          </button>
        )}
      </div>
      {description && <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, lineHeight: 1.4 }}>{description}</p>}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <input type="range" min={min} max={max} step={step} value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          aria-label={label} aria-valuenow={value} aria-valuemin={min} aria-valuemax={max}
          style={{
            flex: 1, height: 6, appearance: 'none', WebkitAppearance: 'none',
            background: `linear-gradient(to right, var(--color-accent) ${pct}%, var(--color-border) ${pct}%)`,
            borderRadius: 3, outline: 'none', cursor: 'pointer',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <input type="number" min={min} max={max} step={step} value={value}
            onChange={(e) => { const v = parseFloat(e.target.value); if (!isNaN(v) && v >= min && v <= max) onChange(v); }}
            style={{
              width: 64, padding: '4px 8px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)',
              textAlign: 'center', fontSize: 13, background: 'var(--color-main-bg)', color: 'var(--color-text-primary)',
            }}
          />
          {unit && <span style={{ fontSize: 12, color: 'var(--color-text-muted)', minWidth: 32 }}>{unit}</span>}
        </div>
      </div>
    </div>
  );
}

function Stepper({ label, description, value, onChange, min, max, step = 1, allowNull = false, nullLabel = 'No limit', onReset, defaultValue }) {
  const displayValue = value === null ? nullLabel : value;
  const canDec = value !== null && (allowNull || value > min);
  const canInc = value === null || value < max;

  const dec = () => {
    if (value === null) return;
    if (allowNull && value <= min) onChange(null);
    else if (value > min) onChange(value - step);
  };
  const inc = () => {
    if (value === null) onChange(min);
    else if (value < max) onChange(value + step);
  };

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <label style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text-primary)' }}>{label}</label>
        {onReset && value !== defaultValue && (
          <button onClick={onReset} title="Reset to default" aria-label={`Reset ${label} to default`}
            style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', padding: 2, display: 'flex', cursor: 'pointer' }}>
            {Icons.refresh}
          </button>
        )}
      </div>
      {description && <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, lineHeight: 1.4 }}>{description}</p>}
      <div style={{ display: 'inline-flex', alignItems: 'center', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', overflow: 'hidden' }}>
        <button onClick={dec} disabled={!canDec} aria-label={`Decrease ${label}`}
          style={{
            width: 36, height: 36, border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: canDec ? 'var(--color-surface)' : 'transparent', fontSize: 18,
            color: canDec ? 'var(--color-text-primary)' : 'var(--color-border)', cursor: canDec ? 'pointer' : 'default',
            transition: 'background 200ms',
          }}>−</button>
        <span style={{ minWidth: 64, textAlign: 'center', fontSize: 13, fontWeight: 500, padding: '0 8px', color: value === null ? 'var(--color-text-muted)' : 'var(--color-text-primary)' }}>
          {displayValue}
        </span>
        <button onClick={inc} disabled={!canInc} aria-label={`Increase ${label}`}
          style={{
            width: 36, height: 36, border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: canInc ? 'var(--color-surface)' : 'transparent', fontSize: 18,
            color: canInc ? 'var(--color-text-primary)' : 'var(--color-border)', cursor: canInc ? 'pointer' : 'default',
            transition: 'background 200ms',
          }}>+</button>
      </div>
    </div>
  );
}

function Toggle({ label, description, value, onChange, onReset, defaultValue }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ flex: 1, marginRight: 12 }}>
          <label style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text-primary)' }}>{label}</label>
          {description && <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2, lineHeight: 1.4 }}>{description}</p>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {onReset && value !== defaultValue && (
            <button onClick={onReset} title="Reset to default" aria-label={`Reset ${label} to default`}
              style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', padding: 2, display: 'flex', cursor: 'pointer' }}>
              {Icons.refresh}
            </button>
          )}
          <button role="switch" aria-checked={value} aria-label={label} onClick={() => onChange(!value)}
            style={{
              width: 44, height: 24, borderRadius: 12, border: 'none', padding: 2, cursor: 'pointer',
              background: value ? 'var(--color-accent)' : 'var(--color-border)', transition: 'background 200ms',
              position: 'relative',
            }}>
            <span style={{
              display: 'block', width: 20, height: 20, borderRadius: '50%', background: '#fff',
              transition: 'transform 200ms', transform: value ? 'translateX(20px)' : 'translateX(0)',
              boxShadow: '0 1px 2px rgba(0,0,0,0.15)',
            }} />
          </button>
        </div>
      </div>
    </div>
  );
}

function SelectInput({ label, description, value, onChange, options, onReset, defaultValue }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <label style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text-primary)' }}>{label}</label>
        {onReset && value !== defaultValue && (
          <button onClick={onReset} title="Reset to default" aria-label={`Reset ${label} to default`}
            style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', padding: 2, display: 'flex', cursor: 'pointer' }}>
            {Icons.refresh}
          </button>
        )}
      </div>
      {description && <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, lineHeight: 1.4 }}>{description}</p>}
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}
          style={{
            padding: '8px 32px 8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)',
            background: 'var(--color-main-bg)', color: 'var(--color-text-primary)', fontSize: 13, appearance: 'none',
            WebkitAppearance: 'none', cursor: 'pointer', minWidth: 140,
          }}>
          {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
        <span style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--color-text-muted)' }}>
          {Icons.chevronDown}
        </span>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   SETTINGS DRAWER
   ═══════════════════════════════════════════════════════════════════════════ */
function SettingsDrawer({ open, params, onParamChange, onReset, onClose }) {
  const drawerRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const handler = (e) => {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.key !== 'Tab') return;
      const el = drawerRef.current;
      if (!el) return;
      const focusable = el.querySelectorAll('button, input, select, [tabindex]:not([tabindex="-1"])');
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const p = (k) => params[k];
  const set = (k) => (v) => onParamChange(k, v);
  const rst = (k) => () => onParamChange(k, DEFAULT_PARAMS[k]);

  const CollapsibleSection = ({ title, defaultOpen = true, children }) => {
    const [exp, setExp] = useState(defaultOpen);
    return (
      <div style={{ marginBottom: 8 }}>
        <button onClick={() => setExp(!exp)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0', border: 'none',
            background: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13, color: 'var(--color-text-muted)',
            textTransform: 'uppercase', letterSpacing: '0.05em',
          }}>
          <span style={{ transform: exp ? 'rotate(90deg)' : 'none', transition: 'transform 200ms', display: 'flex' }}>
            {Icons.chevronRight}
          </span>
          {title}
        </button>
        {exp && <div style={{ paddingLeft: 4 }}>{children}</div>}
      </div>
    );
  };

  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.2)', zIndex: 40 }} />
      <div ref={drawerRef} role="dialog" aria-label="Generation parameters" aria-modal="true"
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(var(--drawer-width), 100vw)',
          background: 'var(--color-main-bg)', borderLeft: '1px solid var(--color-border)', zIndex: 50,
          display: 'flex', flexDirection: 'column', animation: 'slideInRight 250ms ease-out',
          boxShadow: '-4px 0 16px rgba(0,0,0,0.08)',
        }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid var(--color-border)' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Generation parameters</h2>
          <button ref={closeRef} onClick={onClose} aria-label="Close settings"
            style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', padding: 4, display: 'flex', borderRadius: 4, cursor: 'pointer' }}>
            {Icons.x}
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
          <CollapsibleSection title="Chunking">
            <SliderInput label="Chunk size" description="Max characters per chunk before splitting" value={p('chunk_size')} onChange={set('chunk_size')} min={500} max={8000} step={100} unit="chars" onReset={rst('chunk_size')} defaultValue={DEFAULT_PARAMS.chunk_size} />
            <SliderInput label="Overlap" description="Characters of overlap between consecutive chunks" value={p('overlap')} onChange={set('overlap')} min={0} max={1000} step={50} unit="chars" onReset={rst('overlap')} defaultValue={DEFAULT_PARAMS.overlap} />
            <SliderInput label="Chunk summary length" description="Target word count when summarising each chunk" value={p('chunk_summary_length')} onChange={set('chunk_summary_length')} min={50} max={500} step={10} unit="words" onReset={rst('chunk_summary_length')} defaultValue={DEFAULT_PARAMS.chunk_summary_length} />
          </CollapsibleSection>

          <CollapsibleSection title="Model behaviour">
            <SliderInput label="Temperature" description="Higher = more creative, lower = more precise" value={p('temperature')} onChange={set('temperature')} min={0} max={1} step={0.05} onReset={rst('temperature')} defaultValue={DEFAULT_PARAMS.temperature} />
            <Stepper label="Max retries" description="How many times to retry if the model returns a bad schema" value={p('max_retries')} onChange={set('max_retries')} min={1} max={5} onReset={rst('max_retries')} defaultValue={DEFAULT_PARAMS.max_retries} />
            <Toggle label="JSON mode" description="Forces model output to be valid JSON at the token level" value={p('json_mode')} onChange={set('json_mode')} onReset={rst('json_mode')} defaultValue={DEFAULT_PARAMS.json_mode} />
            <SliderInput label="Request timeout" description="Cancel the request if no response in this time" value={p('request_timeout')} onChange={set('request_timeout')} min={30} max={900} step={30} unit="sec" onReset={rst('request_timeout')} defaultValue={DEFAULT_PARAMS.request_timeout} />
          </CollapsibleSection>

          <CollapsibleSection title="Output shape">
            <SelectInput label="Document tone" description="Appended to planner system prompt" value={p('tone')} onChange={set('tone')} options={['Neutral', 'Executive', 'Academic', 'Casual']} onReset={rst('tone')} defaultValue={DEFAULT_PARAMS.tone} />
            <Stepper label="Max sections (doc)" description="Hint to the model; added to system prompt" value={p('max_sections')} onChange={set('max_sections')} min={1} max={20} allowNull nullLabel="No limit" onReset={rst('max_sections')} defaultValue={DEFAULT_PARAMS.max_sections} />
            <Stepper label="Max slides (pptx)" description="Hint to the model; added to system prompt" value={p('max_slides')} onChange={set('max_slides')} min={1} max={30} allowNull nullLabel="No limit" onReset={rst('max_slides')} defaultValue={DEFAULT_PARAMS.max_slides} />
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <label style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text-primary)' }}>Bullets per slide</label>
                {(p('bullets_min') !== DEFAULT_PARAMS.bullets_min || p('bullets_max') !== DEFAULT_PARAMS.bullets_max) && (
                  <button onClick={() => { set('bullets_min')(DEFAULT_PARAMS.bullets_min); set('bullets_max')(DEFAULT_PARAMS.bullets_max); }}
                    title="Reset to default" aria-label="Reset bullets per slide to default"
                    style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', padding: 2, display: 'flex', cursor: 'pointer' }}>
                    {Icons.refresh}
                  </button>
                )}
              </div>
              <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, lineHeight: 1.4 }}>Included in slide system prompt</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Min</span>
                <input type="number" min={1} max={p('bullets_max')} value={p('bullets_min')}
                  onChange={(e) => { const v = parseInt(e.target.value); if (!isNaN(v) && v >= 1 && v <= p('bullets_max')) set('bullets_min')(v); }}
                  style={{ width: 56, padding: '4px 8px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', textAlign: 'center', fontSize: 13, background: 'var(--color-main-bg)', color: 'var(--color-text-primary)' }} />
                <span style={{ color: 'var(--color-text-muted)' }}>–</span>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Max</span>
                <input type="number" min={p('bullets_min')} max={12} value={p('bullets_max')}
                  onChange={(e) => { const v = parseInt(e.target.value); if (!isNaN(v) && v >= p('bullets_min') && v <= 12) set('bullets_max')(v); }}
                  style={{ width: 56, padding: '4px 8px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', textAlign: 'center', fontSize: 13, background: 'var(--color-main-bg)', color: 'var(--color-text-primary)' }} />
              </div>
            </div>
            <Toggle label="Include speaker notes" description="When off, speaker_notes omitted from slide prompt" value={p('include_speaker_notes')} onChange={set('include_speaker_notes')} onReset={rst('include_speaker_notes')} defaultValue={DEFAULT_PARAMS.include_speaker_notes} />
            <SelectInput label="Sub-bullet depth" description="Whether to allow nested bullets in documents" value={p('sub_bullet_depth')} onChange={set('sub_bullet_depth')} options={['None', '1 level']} onReset={rst('sub_bullet_depth')} defaultValue={DEFAULT_PARAMS.sub_bullet_depth} />
          </CollapsibleSection>
        </div>

        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--color-border)' }}>
          <button onClick={onReset}
            style={{
              width: '100%', padding: '10px 16px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)',
              background: 'transparent', color: 'var(--color-text-primary)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
              transition: 'background 200ms',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-surface)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
            Reset all to defaults
          </button>
        </div>
      </div>
    </>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════════════════════════════════════ */
function Sidebar({ sessions, currentSessionId, onNewSession, onSelectSession, onOpenSettings }) {
  return (
    <aside style={{
      width: 'var(--sidebar-width)', minWidth: 'var(--sidebar-width)', height: '100vh',
      background: 'var(--color-sidebar-bg)', display: 'flex', flexDirection: 'column', flexShrink: 0,
    }}>
      <div style={{ padding: '20px 20px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ color: 'var(--color-accent)', display: 'flex' }}>{Icons.logo}</span>
        <span style={{ color: 'var(--color-sidebar-text)', fontWeight: 600, fontSize: 18, letterSpacing: '-0.01em' }}>DocGen</span>
      </div>

      <div style={{ padding: '0 12px 12px' }}>
        <button onClick={onNewSession}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px',
            border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-input)', background: 'transparent',
            color: 'var(--color-sidebar-text)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
            transition: 'background 200ms, border-color 200ms',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-sidebar-hover)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}>
          {Icons.plus} New session
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '0 8px' }}>
        {sessions.length === 0 && (
          <p style={{ color: 'var(--color-sidebar-text-muted)', fontSize: 12, padding: 12, textAlign: 'center' }}>No sessions yet</p>
        )}
        {sessions.map((s) => (
          <button key={s.id} onClick={() => onSelectSession(s.id)}
            style={{
              width: '100%', textAlign: 'left', padding: '10px 12px', border: 'none',
              borderRadius: 'var(--radius-input)', cursor: 'pointer', marginBottom: 2, display: 'block',
              background: s.id === currentSessionId ? 'var(--color-sidebar-active)' : 'transparent',
              color: 'var(--color-sidebar-text)', transition: 'background 200ms',
            }}
            onMouseEnter={(e) => { if (s.id !== currentSessionId) e.currentTarget.style.background = 'var(--color-sidebar-hover)'; }}
            onMouseLeave={(e) => { if (s.id !== currentSessionId) e.currentTarget.style.background = 'transparent'; }}>
            <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {s.title || 'Untitled'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-sidebar-text-muted)', marginTop: 2 }}>
              {formatTimestamp(s.timestamp)}
            </div>
          </button>
        ))}
      </div>

      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
        <button onClick={onOpenSettings} aria-label="Open settings"
          style={{
            display: 'flex', alignItems: 'center', gap: 8, background: 'none', border: 'none',
            color: 'var(--color-sidebar-text-muted)', cursor: 'pointer', padding: '8px 4px', width: '100%',
            borderRadius: 'var(--radius-input)', transition: 'color 200ms, background 200ms', fontSize: 13,
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-sidebar-text)'; e.currentTarget.style.background = 'var(--color-sidebar-hover)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-sidebar-text-muted)'; e.currentTarget.style.background = 'none'; }}>
          {Icons.settings} Settings
        </button>
      </div>
    </aside>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   MODEL BAR
   ═══════════════════════════════════════════════════════════════════════════ */
function ModelBar({ mode, model, apiKey, models, modelsLoading, modelsError, healthOk, onModeChange, onModelChange, onApiKeyChange, onRetryModels }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', background: 'var(--color-surface)',
      borderRadius: 'var(--radius-card)', marginBottom: 8, flexWrap: 'wrap',
    }}>
      <div style={{ display: 'flex', border: '1px solid var(--color-border)', borderRadius: 20, overflow: 'hidden', flexShrink: 0 }}>
        {['offline', 'online'].map((m) => (
          <button key={m} onClick={() => onModeChange(m)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', border: 'none', fontSize: 12, fontWeight: 500,
              background: mode === m ? 'var(--color-accent)' : 'transparent',
              color: mode === m ? '#fff' : 'var(--color-text-muted)', cursor: 'pointer', transition: 'all 200ms',
            }}>
            {m === 'offline' ? Icons.monitor : Icons.cloud}
            {m === 'offline' ? 'Local' : 'Cloud'}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 160 }}>
        {modelsLoading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--color-text-muted)' }}>
            <Spinner size={14} /> Loading models…
          </div>
        ) : modelsError ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-error)' }}>
            {Icons.alertTriangle}
            <span>{mode === 'offline' ? 'Ollama not reachable' : 'Failed to load models'}</span>
            <button onClick={onRetryModels}
              style={{ background: 'none', border: 'none', color: 'var(--color-accent)', fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}>
              Retry
            </button>
          </div>
        ) : (
          <div style={{ position: 'relative', flex: 1 }}>
            <select value={model} onChange={(e) => onModelChange(e.target.value)} aria-label="Select model"
              style={{
                width: '100%', padding: '6px 28px 6px 10px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)',
                background: 'var(--color-main-bg)', color: 'var(--color-text-primary)', fontSize: 13,
                appearance: 'none', WebkitAppearance: 'none', cursor: 'pointer',
              }}>
              {models.length === 0 && (
                <option value="">{mode === 'offline' ? 'No models — run: ollama pull llama3.1' : 'No models available'}</option>
              )}
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <span style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--color-text-muted)' }}>
              {Icons.chevronDown}
            </span>
          </div>
        )}

        {!modelsLoading && !modelsError && (
          <span title={healthOk ? 'Backend healthy' : 'Backend unhealthy'}
            style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0, background: healthOk ? 'var(--color-success)' : 'var(--color-error)' }} />
        )}
      </div>

      {mode === 'online' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <input type="password" placeholder="Ollama Cloud API key" value={apiKey} onChange={(e) => onApiKeyChange(e.target.value)}
            style={{
              padding: '6px 10px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)',
              background: 'var(--color-main-bg)', color: 'var(--color-text-primary)', fontSize: 12, width: 180,
            }} />
          <a href="https://ollama.com" target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, color: 'var(--color-accent)', textDecoration: 'none', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 3 }}>
            Get key {Icons.externalLink}
          </a>
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   STRUCTURED PLAN VIEWER
   ═══════════════════════════════════════════════════════════════════════════ */
function PlanViewer({ plan }) {
  const [expanded, setExpanded] = useState(false);
  if (!plan) return null;

  const renderPlan = () => {
    if (plan.sections) {
      return (
        <ol style={{ paddingLeft: 0, margin: 0, listStyle: 'none' }}>
          {plan.sections.map((section, i) => (
            <li key={i} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-accent)', fontVariantNumeric: 'tabular-nums', minWidth: 24 }}>{i + 1}.</span>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-text-primary)' }}>{section.title || section.heading || `Section ${i + 1}`}</span>
                  {(section.description || section.content) && (
                    <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2, lineHeight: 1.5 }}>
                      {(section.description || (typeof section.content === 'string' ? section.content : '')).substring(0, 200)}
                    </p>
                  )}
                  {section.bullets && section.bullets.length > 0 && (
                    <ul style={{ marginTop: 4, paddingLeft: 16, listStyleType: 'disc' }}>
                      {section.bullets.map((b, j) => (
                        <li key={j} style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 2 }}>
                          {typeof b === 'string' ? b : b.text || JSON.stringify(b)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      );
    }
    if (plan.slides) {
      return (
        <ol style={{ paddingLeft: 0, margin: 0, listStyle: 'none' }}>
          {plan.slides.map((slide, i) => (
            <li key={i} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 11, color: 'var(--color-accent)', fontVariantNumeric: 'tabular-nums', minWidth: 50, whiteSpace: 'nowrap' }}>Slide {i + 1}</span>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-text-primary)' }}>{slide.title}</span>
                  {slide.bullets && slide.bullets.length > 0 && (
                    <ul style={{ marginTop: 4, paddingLeft: 16, listStyleType: 'disc' }}>
                      {slide.bullets.map((b, j) => (
                        <li key={j} style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 2 }}>
                          {typeof b === 'string' ? b : b.text || JSON.stringify(b)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      );
    }
    return (
      <pre style={{ fontSize: 12, color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0, lineHeight: 1.6 }}>
        {JSON.stringify(plan, null, 2)}
      </pre>
    );
  };

  return (
    <div style={{ marginTop: 16, borderTop: '1px solid var(--color-border)', paddingTop: 12 }}>
      <button onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none',
          cursor: 'pointer', color: 'var(--color-text-muted)', fontSize: 13, fontWeight: 500, padding: 0,
        }}>
        <span style={{ transform: expanded ? 'rotate(90deg)' : 'none', transition: 'transform 200ms', display: 'flex' }}>{Icons.chevronRight}</span>
        Structured plan
      </button>
      {expanded && <div style={{ marginTop: 12 }}>{renderPlan()}</div>}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   OUTPUT AREA
   ═══════════════════════════════════════════════════════════════════════════ */
function OutputArea({ result, isLoading, progress, error, onDismissError, backendOffline }) {
  const outputRef = useRef(null);

  useEffect(() => {
    if (result && outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [result]);

  const handleDownload = async (downloadUrl, filename) => {
    try {
      const res = await fetch(`${API_BASE}${downloadUrl}`);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'document';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download error:', err);
    }
  };

  const formatBadge = (format) => {
    const colors = { docx: '#2563eb', pptx: '#ea580c', pdf: '#dc2626' };
    return (
      <span style={{
        display: 'inline-flex', padding: '3px 10px', borderRadius: 12,
        background: colors[format?.toLowerCase()] || 'var(--color-text-muted)', color: '#fff',
        fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{format}</span>
    );
  };

  const steps = ['Extracting text', 'Planning structure', 'Rendering file'];

  return (
    <div ref={outputRef} aria-live="polite"
      style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', justifyContent: result ? 'flex-end' : 'center', padding: '24px 0' }}>

      {backendOffline && (
        <div style={{
          margin: '0 auto 16px', maxWidth: 'var(--main-max-width)', width: '100%', padding: '12px 16px',
          background: 'var(--color-error-bg)', border: '1px solid #fecaca', borderRadius: 'var(--radius-input)',
          display: 'flex', alignItems: 'center', gap: 12, fontSize: 13, color: '#991b1b', animation: 'slideInUp 300ms ease-out',
        }}>
          {Icons.alertTriangle}
          <div style={{ flex: 1 }}>
            <strong>Backend offline.</strong> Run:
            <code style={{ display: 'inline-block', background: '#fff', padding: '2px 8px', borderRadius: 4, marginLeft: 6, fontSize: 12, fontFamily: 'monospace', userSelect: 'all' }}>
              uvicorn main:app --reload
            </code>
          </div>
          <button onClick={() => navigator.clipboard?.writeText('uvicorn main:app --reload')}
            title="Copy command" aria-label="Copy startup command"
            style={{ background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer', padding: 4, display: 'flex' }}>
            {Icons.copy}
          </button>
        </div>
      )}

      {error && (
        <div style={{
          margin: '0 auto 16px', maxWidth: 'var(--main-max-width)', width: '100%', padding: '12px 16px',
          background: 'var(--color-error-bg)', border: '1px solid #fecaca', borderRadius: 'var(--radius-input)',
          display: 'flex', alignItems: 'center', gap: 12, fontSize: 13, color: '#991b1b', animation: 'slideInUp 300ms ease-out',
        }}>
          {Icons.alertTriangle}
          <span style={{ flex: 1 }}>{error}</span>
          <button onClick={onDismissError} aria-label="Dismiss error"
            style={{ background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer', padding: 4, display: 'flex' }}>
            {Icons.x}
          </button>
        </div>
      )}

      {!result && !isLoading && (
        <div style={{ textAlign: 'center', padding: '60px 24px', margin: 'auto 0' }}>
          <div style={{ width: 80, height: 80, margin: '0 auto 24px', background: 'var(--color-surface)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 15, lineHeight: 1.6 }}>
            Choose a source and model, then click Generate.
          </p>
        </div>
      )}

      {isLoading && (
        <div style={{ maxWidth: 'var(--main-max-width)', width: '100%', margin: '0 auto', padding: '0 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 24, animation: 'slideInUp 300ms ease-out' }}>
            {steps.map((step, i) => (
              <React.Fragment key={i}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 600, flexShrink: 0, transition: 'all 300ms',
                    background: progress >= i ? 'var(--color-accent)' : 'var(--color-surface)',
                    color: progress >= i ? '#fff' : 'var(--color-text-muted)',
                  }}>
                    {progress > i ? Icons.check : progress === i ? <Spinner size={14} color="#fff" /> : i + 1}
                  </div>
                  <span style={{
                    fontSize: 12, whiteSpace: 'nowrap', transition: 'color 300ms',
                    fontWeight: progress >= i ? 600 : 400,
                    color: progress >= i ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                  }}>{step}</span>
                </div>
                {i < steps.length - 1 && (
                  <div style={{
                    height: 2, flex: '0 0 24px', margin: '0 4px', borderRadius: 1, transition: 'background 300ms',
                    background: progress > i ? 'var(--color-accent)' : 'var(--color-border)',
                  }} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div style={{ maxWidth: 'var(--main-max-width)', width: '100%', margin: '0 auto', padding: '0 24px', animation: 'fadeInUp 400ms ease-out' }}>
          <div style={{ background: 'var(--color-surface)', borderRadius: 'var(--radius-card)', padding: 24, border: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: 17, fontWeight: 600, marginBottom: 8, color: 'var(--color-text-primary)' }}>
                  {result.title || 'Generated Document'}
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  {formatBadge(result.format)}
                  {result.model && <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Model: {result.model}</span>}
                  {result.generationTime != null && <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{formatTime(result.generationTime)}</span>}
                </div>
              </div>
              <button onClick={() => handleDownload(result.downloadUrl, result.filename)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', border: 'none',
                  borderRadius: 'var(--radius-input)', background: 'var(--color-accent)', color: '#fff',
                  fontSize: 14, fontWeight: 600, cursor: 'pointer', transition: 'background 200ms', flexShrink: 0,
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-accent-hover)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'var(--color-accent)'}>
                {Icons.download} Download
              </button>
            </div>
            <PlanViewer plan={result.plan} />
          </div>
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   COMPOSER
   ═══════════════════════════════════════════════════════════════════════════ */
function Composer({ sourceType, onSourceTypeChange, file, onFileChange, url, onUrlChange, searchQuery, onSearchQueryChange,
  instructions, onInstructionsChange, outputFormat, onOutputFormatChange, onGenerate, isGenerating, stillWorking, onCancel }) {

  const fileRef = useRef(null);
  const taRef = useRef(null);

  const handleFilePick = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > MAX_FILE_SIZE) { alert('File too large. Maximum size is 50MB.'); return; }
    onFileChange(f);
  };

  useEffect(() => {
    const ta = taRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 200) + 'px'; }
  }, [instructions]);

  const sources = [
    { type: 'file', icon: Icons.file, label: 'File' },
    { type: 'url', icon: Icons.link, label: 'URL' },
    { type: 'search', icon: Icons.search, label: 'Search' },
  ];
  const formats = ['docx', 'pptx', 'pdf'];

  return (
    <div style={{ padding: '0 24px 24px', maxWidth: 'var(--main-max-width)', width: '100%', margin: '0 auto' }}>
      {stillWorking && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 14px',
          background: 'var(--color-accent-light)', borderRadius: '8px 8px 0 0', fontSize: 13, color: 'var(--color-accent)',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Spinner size={14} color="var(--color-accent)" /> Still working…
          </span>
          <button onClick={onCancel}
            style={{ background: 'none', border: 'none', color: 'var(--color-accent)', cursor: 'pointer', fontSize: 12, fontWeight: 600, textDecoration: 'underline' }}>
            Cancel
          </button>
        </div>
      )}

      <div style={{
        background: 'var(--color-main-bg)', border: '1px solid var(--color-border)',
        borderRadius: stillWorking ? '0 0 var(--radius-card) var(--radius-card)' : 'var(--radius-card)',
        boxShadow: 'var(--shadow-composer)', padding: 16,
        pointerEvents: isGenerating ? 'none' : 'auto', opacity: isGenerating ? 0.6 : 1, transition: 'opacity 200ms',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
          {sources.map(({ type, icon, label }) => (
            <button key={type} onClick={() => onSourceTypeChange(type)} aria-label={`Source: ${label}`} title={label}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
                border: '1px solid', borderRadius: 'var(--radius-input)', fontSize: 12, fontWeight: 500,
                cursor: 'pointer', transition: 'all 200ms',
                borderColor: sourceType === type ? 'var(--color-accent)' : 'var(--color-border)',
                background: sourceType === type ? 'var(--color-accent-light)' : 'transparent',
                color: sourceType === type ? 'var(--color-accent)' : 'var(--color-text-muted)',
              }}>
              {icon} {label}
            </button>
          ))}
        </div>

        {sourceType === 'file' && (
          <div style={{ marginBottom: 12 }}>
            {file ? (
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 12px',
                background: 'var(--color-surface)', borderRadius: 'var(--radius-input)', fontSize: 13, color: 'var(--color-text-primary)',
              }}>
                {Icons.file}
                <span style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                <button onClick={() => onFileChange(null)} aria-label="Remove file"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)', padding: 0, display: 'flex' }}>
                  {Icons.x}
                </button>
              </div>
            ) : (
              <button onClick={() => fileRef.current?.click()}
                style={{
                  padding: '8px 14px', border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-input)',
                  background: 'transparent', color: 'var(--color-text-muted)', fontSize: 13, cursor: 'pointer',
                  transition: 'border-color 200ms',
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--color-accent)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--color-border)'}>
                Choose file (PDF, DOCX, PPTX, TXT, MD, CSV)
              </button>
            )}
            <input ref={fileRef} type="file" accept=".pdf,.docx,.pptx,.txt,.md,.csv" onChange={handleFilePick} style={{ display: 'none' }} aria-hidden="true" />
          </div>
        )}

        {sourceType === 'url' && (
          <input type="url" placeholder="https://example.com/article" value={url} onChange={(e) => onUrlChange(e.target.value)}
            style={{
              width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)',
              background: 'var(--color-main-bg)', color: 'var(--color-text-primary)', fontSize: 13, marginBottom: 12,
            }} />
        )}

        {sourceType === 'search' && (
          <input type="text" placeholder="Search query…" value={searchQuery} onChange={(e) => onSearchQueryChange(e.target.value)}
            style={{
              width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)',
              background: 'var(--color-main-bg)', color: 'var(--color-text-primary)', fontSize: 13, marginBottom: 12,
            }} />
        )}

        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
          <textarea ref={taRef} value={instructions} onChange={(e) => onInstructionsChange(e.target.value)}
            placeholder="Additional instructions… (e.g. executive tone, focus on financials, max 5 sections)"
            rows={1}
            style={{
              flex: 1, resize: 'none', border: 'none', outline: 'none', padding: '8px 0', fontSize: 14,
              lineHeight: 1.5, background: 'transparent', color: 'var(--color-text-primary)', maxHeight: 200, overflow: 'auto',
            }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
            <div style={{ display: 'flex', borderRadius: 'var(--radius-input)', border: '1px solid var(--color-border)', overflow: 'hidden', marginRight: 8 }}>
              {formats.map((fmt) => (
                <button key={fmt} onClick={() => onOutputFormatChange(fmt)}
                  style={{
                    padding: '6px 12px', border: 'none', fontSize: 12, fontWeight: 600, textTransform: 'uppercase',
                    letterSpacing: '0.03em', cursor: 'pointer', transition: 'all 200ms',
                    background: outputFormat === fmt ? 'var(--color-accent)' : 'transparent',
                    color: outputFormat === fmt ? '#fff' : 'var(--color-text-muted)',
                  }}>{fmt}</button>
              ))}
            </div>

            <button onClick={onGenerate} disabled={isGenerating} aria-busy={isGenerating}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 20px', border: 'none',
                borderRadius: 'var(--radius-input)', color: '#fff', fontSize: 14, fontWeight: 600,
                whiteSpace: 'nowrap', transition: 'background 200ms',
                background: isGenerating ? 'var(--color-accent-hover)' : 'var(--color-accent)',
                cursor: isGenerating ? 'default' : 'pointer',
              }}
              onMouseEnter={(e) => { if (!isGenerating) e.currentTarget.style.background = 'var(--color-accent-hover)'; }}
              onMouseLeave={(e) => { if (!isGenerating) e.currentTarget.style.background = 'var(--color-accent)'; }}>
              {isGenerating ? <><Spinner size={16} color="#fff" /> Generating…</> : <>{Icons.send} Generate</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════════════════
   APP ROOT
   ═══════════════════════════════════════════════════════════════════════════ */
export default function App() {
  // Sessions
  const [sessions, setSessions] = useState(() => loadFromStorage('docgen_sessions', []));
  const [currentSessionId, setCurrentSessionId] = useState(null);

  // Model / mode
  const [mode, setMode] = useState('offline');
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState(() => loadFromStorage('docgen_api_key', ''));
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState(false);
  const [healthOk, setHealthOk] = useState(false);
  const [backendOffline, setBackendOffline] = useState(false);

  // Composer
  const [sourceType, setSourceType] = useState('file');
  const [file, setFile] = useState(null);
  const [uploadedFilePath, setUploadedFilePath] = useState('');
  const [url, setUrl] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [instructions, setInstructions] = useState('');
  const [outputFormat, setOutputFormat] = useState('docx');

  // Generation
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stillWorking, setStillWorking] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const stillRef = useRef(null);

  // Settings
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [params, setParams] = useState(() => loadFromStorage('docgen_params', { ...DEFAULT_PARAMS }));

  // Persist
  useEffect(() => { saveToStorage('docgen_sessions', sessions); }, [sessions]);
  useEffect(() => { saveToStorage('docgen_api_key', apiKey); }, [apiKey]);
  useEffect(() => { saveToStorage('docgen_params', params); }, [params]);

  // Fetch models
  const fetchModels = useCallback(async () => {
    setModelsLoading(true);
    setModelsError(false);
    try {
      const qp = new URLSearchParams({ mode });
      if (mode === 'online' && apiKey) qp.set('api_key', apiKey);
      const res = await fetch(`${API_BASE}/models?${qp}`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      const list = Array.isArray(data) ? data : (data.models || []);
      setModels(list);
      if (list.length > 0 && !list.includes(model)) setModel(list[0]);
      setBackendOffline(false);
    } catch {
      setModelsError(true);
      setModels([]);
    } finally {
      setModelsLoading(false);
    }
  }, [mode, apiKey, model]);

  useEffect(() => { fetchModels(); }, [mode]); // eslint-disable-line

  // Health poll
  useEffect(() => {
    const check = async () => {
      try {
        const qp = new URLSearchParams({ mode });
        if (model) qp.set('model', model);
        if (mode === 'online' && apiKey) qp.set('api_key', apiKey);
        const res = await fetch(`${API_BASE}/health?${qp}`);
        setHealthOk(res.ok);
        setBackendOffline(false);
      } catch {
        setHealthOk(false);
        setBackendOffline(true);
      }
    };
    check();
    const iv = setInterval(check, 10000);
    return () => clearInterval(iv);
  }, [mode, model, apiKey]);

  // Param handlers
  const handleParamChange = (k, v) => setParams(prev => ({ ...prev, [k]: v }));
  const handleResetParams = () => setParams({ ...DEFAULT_PARAMS });

  // Session handlers
  const handleNewSession = () => {
    setCurrentSessionId(null); setResult(null); setError(null);
    setFile(null); setUploadedFilePath(''); setUrl(''); setSearchQuery(''); setInstructions('');
  };

  const handleSelectSession = (id) => {
    const s = sessions.find(x => x.id === id);
    if (s) { setCurrentSessionId(id); setResult(s.result); setError(null); }
  };

  // Generate
  const handleGenerate = async () => {
    setError(null); setIsGenerating(true); setProgress(0); setStillWorking(false); setResult(null);

    const ac = new AbortController();
    abortRef.current = ac;
    const timers = [];
    timers.push(setTimeout(() => setProgress(1), 3000));
    stillRef.current = setTimeout(() => setStillWorking(true), 120000);
    const t0 = Date.now();

    try {
      // Upload if needed
      let fp = uploadedFilePath;
      if (sourceType === 'file' && file && !uploadedFilePath) {
        const fd = new FormData();
        fd.append('file', file);
        const r = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd, signal: ac.signal });
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'File upload failed'); }
        fp = (await r.json()).file_path || (await r.json()).file_id || '';
        setUploadedFilePath(fp);
      }

      // Build form
      const fd = new FormData();
      fd.append('output_format', outputFormat);
      fd.append('source_type', sourceType);
      fd.append('mode', mode);
      fd.append('model', model);
      if (mode === 'online' && apiKey) fd.append('api_key', apiKey);
      if (instructions) fd.append('instructions', instructions);
      if (instructions) fd.append('prompt', instructions);
      if (sourceType === 'file' && fp) fd.append('file_path', fp);
      if (sourceType === 'url' && url) fd.append('url', url);
      if (sourceType === 'search' && searchQuery) fd.append('search_query', searchQuery);
      fd.append('chunk_size', String(params.chunk_size));
      fd.append('overlap', String(params.overlap));
      fd.append('chunk_overlap', String(params.overlap));
      fd.append('chunk_summary_length', String(params.chunk_summary_length));
      fd.append('temperature', String(params.temperature));
      fd.append('max_retries', String(params.max_retries));
      fd.append('json_mode', String(params.json_mode));
      fd.append('request_timeout', String(params.request_timeout));
      fd.append('tone', params.tone);
      if (params.max_sections !== null) fd.append('max_sections', String(params.max_sections));
      if (params.max_slides !== null) fd.append('max_slides', String(params.max_slides));
      fd.append('bullets_min', String(params.bullets_min));
      fd.append('bullets_max', String(params.bullets_max));
      fd.append('include_speaker_notes', String(params.include_speaker_notes));
      fd.append('sub_bullet_depth', params.sub_bullet_depth);

      const res = await fetch(`${API_BASE}/generate`, { method: 'POST', body: fd, signal: ac.signal });
      setProgress(2);

      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Generation failed (${res.status})`); }

      const data = await res.json();
      const genTime = (Date.now() - t0) / 1000;
      const fname = data.filename || data.file_path?.split('/').pop() || `document.${outputFormat}`;
      const newResult = {
        title: data.plan?.title || data.title || fname,
        format: outputFormat, model, generationTime: genTime,
        downloadUrl: data.download_url || `/download/${fname}`,
        filename: fname,
        plan: data.plan || null,
      };

      setResult(newResult);
      const sid = currentSessionId || `session_${Date.now()}`;
      const session = { id: sid, title: newResult.title, timestamp: Date.now(), result: newResult };
      setSessions(prev => {
        const idx = prev.findIndex(s => s.id === sid);
        if (idx >= 0) { const u = [...prev]; u[idx] = session; return u; }
        return [session, ...prev];
      });
      setCurrentSessionId(sid);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsGenerating(false); setProgress(0); setStillWorking(false);
      timers.forEach(clearTimeout); clearTimeout(stillRef.current); abortRef.current = null;
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    setIsGenerating(false); setProgress(0); setStillWorking(false);
  };

  return (
    <>
      <GlobalStyles />
      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
        <Sidebar sessions={sessions} currentSessionId={currentSessionId}
          onNewSession={handleNewSession} onSelectSession={handleSelectSession}
          onOpenSettings={() => setSettingsOpen(true)} />
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'var(--color-main-bg)' }}>
          <div style={{ padding: '12px 24px 0', maxWidth: 'var(--main-max-width)', width: '100%', margin: '0 auto' }}>
            <ModelBar mode={mode} model={model} apiKey={apiKey} models={models}
              modelsLoading={modelsLoading} modelsError={modelsError} healthOk={healthOk}
              onModeChange={setMode} onModelChange={setModel} onApiKeyChange={setApiKey} onRetryModels={fetchModels} />
          </div>
          <OutputArea result={result} isLoading={isGenerating} progress={progress}
            error={error} onDismissError={() => setError(null)} backendOffline={backendOffline} />
          <Composer sourceType={sourceType} onSourceTypeChange={setSourceType}
            file={file} onFileChange={(f) => { setFile(f); setUploadedFilePath(''); }}
            url={url} onUrlChange={setUrl} searchQuery={searchQuery} onSearchQueryChange={setSearchQuery}
            instructions={instructions} onInstructionsChange={setInstructions}
            outputFormat={outputFormat} onOutputFormatChange={setOutputFormat}
            onGenerate={handleGenerate} isGenerating={isGenerating}
            stillWorking={stillWorking} onCancel={handleCancel} />
        </main>
        <SettingsDrawer open={settingsOpen} params={params}
          onParamChange={handleParamChange} onReset={handleResetParams}
          onClose={() => setSettingsOpen(false)} />
      </div>
    </>
  );
}
