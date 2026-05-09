// client/src/components/UI.jsx
import React from 'react';

export function StatCard({ label, value, sub, variant = 'navy' }) {
  return (
    <div className={`stat-card stat-${variant}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export function Badge({ children, variant = 'navy' }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function Alert({ children, variant = 'info' }) {
  return <div className={`alert alert-${variant}`}>{children}</div>;
}

export function Spinner() {
  return <div className="spinner" />;
}

export function Table({ headers, rows, colorFn }) {
  if (!rows.length) return <div className="empty-state">No data available.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{headers.map(h => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci} style={colorFn ? { color: colorFn(cell, ci, row) } : {}}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs">
      {tabs.map(t => (
        <button
          key={t.id}
          className={`tab-btn${active === t.id ? ' active' : ''}`}
          onClick={() => onChange(t.id)}
        >{t.label}</button>
      ))}
    </div>
  );
}

export function Modal({ title, onClose, children }) {
  return (
    <div style={{
      position:'fixed',inset:0,background:'rgba(26,45,90,0.45)',
      display:'flex',alignItems:'center',justifyContent:'center',zIndex:1000
    }} onClick={onClose}>
      <div style={{
        background:'var(--surface)',borderRadius:14,padding:32,
        width:'100%',maxWidth:480,boxShadow:'var(--shadow-lg)',
        maxHeight:'90vh',overflowY:'auto'
      }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between" style={{marginBottom:20}}>
          <h2 style={{fontSize:18,fontWeight:700}}>{title}</h2>
          <button onClick={onClose} style={{
            background:'none',border:'none',fontSize:20,cursor:'pointer',color:'var(--text3)'
          }}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function InfoCard({ title, items, accent = 'var(--navy)' }) {
  return (
    <div style={{
      background:'var(--surface)',border:'1px solid var(--border)',
      borderTop:`3px solid ${accent}`,borderRadius:'var(--radius)',overflow:'hidden'
    }}>
      <div style={{padding:'12px 16px',borderBottom:'1px solid var(--border)',
        fontSize:13,fontWeight:700,color:accent}}>{title}</div>
      <div style={{padding:'12px 16px'}}>
        {items.length ? items.map((item,i) => (
          <div key={i} style={{fontSize:12,color:'var(--text2)',padding:'4px 0',
            borderBottom:i<items.length-1?'1px solid var(--border)':'none'}}>
            • {item}
          </div>
        )) : <div style={{fontSize:12,color:'var(--text3)'}}>No data available.</div>}
      </div>
    </div>
  );
}
