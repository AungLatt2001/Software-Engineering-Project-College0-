import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

export default function Registrar() {
  const { sem, setSem } = useAuth();
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState('');
  const [warningUser, setWarningUser] = useState('');
  const [warningReason, setWarningReason] = useState('');

  const load = () => api.get('/registrar').then(r => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const act = async (url, body) => {
    try {
      const r = await api.post(url, body);
      setMsg(r.data.msg || 'Done.');
      load();
      if (r.data.sem) setSem(r.data.sem);
    } catch (err) { setMsg(err.response?.data?.msg || 'Error.'); }
  };

  if (!data) return <div className="loading">Loading…</div>;

  const PHASES = ['setup','registration','running','grading','closed'];

  return (
    <>
      <div className="page-header">
        <h1>Registrar Dashboard</h1>
        <p>Manage semesters, students, applications, complaints and graduation requests.</p>
      </div>

      {msg && <div className="alert alert-success">{msg}</div>}

      {/* SEMESTER CONTROL */}
      <div className="panel">
        <div className="panel-title">Semester Control</div>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          {data.all_semesters.map(s => (
            <div key={s.semester_id} style={{ background: s.semester_id === sem?.semester_id ? 'var(--blue-soft)' : '#f8f9fb', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 18px', minWidth: 200 }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--muted)', marginBottom: 4 }}>{s.term_name} {s.year}</div>
              <span className="phase-badge" style={{ fontSize: '0.75rem', padding: '3px 10px', marginBottom: 10, display: 'inline-block', background: 'var(--blue)', color: '#fff' }}>{s.phase}</span>
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <select className="select-sm" defaultValue={s.phase} id={`phase-${s.semester_id}`}>
                  {PHASES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <button className="btn-primary btn-sm" onClick={() => {
                  const el = document.getElementById(`phase-${s.semester_id}`);
                  act('/registrar/phase', { semester_id: s.semester_id, phase: el.value });
                }}>Set</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* WARNINGS */}
      {data.warnings.length > 0 && (
        <div className="panel">
          <div className="panel-title">Active Warnings ({data.warnings.length})</div>
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>User</th><th>Reason</th><th>Source</th><th>Issued</th></tr></thead>
              <tbody>{data.warnings.map(w => (
                <tr key={w.warning_id}>
                  <td>{w.user_name}</td><td>{w.reason}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{w.source_module}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{w.issued_at?.slice(0,10)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}

      {/* STUDENTS */}
      <div className="panel">
        <div className="panel-title">Students ({data.students.length})</div>
        <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Status</th><th>Cum GPA</th><th>Warnings</th><th>Honors</th><th>Fine</th></tr></thead>
            <tbody>{data.students.map(s => (
              <tr key={s.user_id}>
                <td>#{s.user_id}</td>
                <td>{s.name}</td>
                <td style={{ fontSize: '0.75rem' }}>{s.email}</td>
                <td><span style={{ color: s.status==='active' ? 'var(--green)' : s.status==='suspended' ? 'var(--red)' : 'var(--muted)', fontWeight: 600 }}>{s.status}</span></td>
                <td style={{ color: 'var(--green)', fontWeight: 600 }}>{Number(s.cumulative_gpa).toFixed(3)}</td>
                <td style={{ color: s.warning_count > 0 ? 'var(--orange)' : undefined, fontWeight: s.warning_count > 0 ? 600 : undefined }}>{s.warning_count}/3</td>
                <td>{s.honor_count}</td>
                <td>{s.fine_due > 0 ? <span style={{ color: 'var(--red)', fontWeight: 600 }}>${Number(s.fine_due).toFixed(2)}</span> : '—'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 8 }}>Issue Manual Warning</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="select-sm" style={{ minWidth: 180 }} value={warningUser} onChange={e => setWarningUser(e.target.value)}>
              <option value="">Select student...</option>
              {data.students.map(s => <option key={s.user_id} value={s.user_id}>{s.name}</option>)}
            </select>
            <input value={warningReason} onChange={e => setWarningReason(e.target.value)} placeholder="Reason for warning" style={{ flex: 1, minWidth: 200, padding: '6px 10px', border: '1.5px solid var(--border)', borderRadius: 6, fontSize: '0.82rem', fontFamily: 'inherit' }} />
            <button className="btn-secondary btn-sm" onClick={() => { act('/registrar/warning', { user_id: parseInt(warningUser), reason: warningReason }); setWarningUser(''); setWarningReason(''); }}>Issue Warning</button>
          </div>
        </div>
      </div>

      {/* APPLICATIONS */}
      <div className="panel">
        <div className="panel-title">Visitor Applications ({data.applications.length})</div>
        {data.applications.length === 0 ? <p style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>No applications.</p> : (
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Type</th><th>GPA</th><th>Justification</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>{data.applications.map(a => (
                <tr key={a.application_id}>
                  <td>{a.applicant_name}</td>
                  <td style={{ fontSize: '0.75rem' }}>{a.email}</td>
                  <td>{a.application_type}</td>
                  <td>{a.prior_gpa ? Number(a.prior_gpa).toFixed(2) : '—'}</td>
                  <td style={{ fontSize: '0.78rem', maxWidth: 220 }}>{a.justification || '—'}</td>
                  <td><span style={{ fontWeight: 600, color: a.status==='approved' ? 'var(--green)' : a.status==='rejected' ? 'var(--red)' : 'var(--orange)' }}>{a.status}</span></td>
                  <td>{a.status === 'pending' ? (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn-primary btn-sm" onClick={() => act(`/registrar/application/${a.application_id}`, { decision: 'approved' })}>Approve</button>
                      <button className="btn-secondary btn-sm" onClick={() => act(`/registrar/application/${a.application_id}`, { decision: 'rejected' })}>Reject</button>
                    </div>
                  ) : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>

      {/* COMPLAINTS */}
      <div className="panel">
        <div className="panel-title">Complaints ({data.complaints.length})</div>
        {data.complaints.length === 0 ? <p style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>No complaints.</p> : (
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>Filed By</th><th>Against</th><th>Description</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>{data.complaints.map(c => (
                <tr key={c.complaint_id}>
                  <td>{c.filer_name}</td>
                  <td>{c.target_name}</td>
                  <td style={{ fontSize: '0.78rem', maxWidth: 260 }}>{c.complaint_text}</td>
                  <td><span style={{ fontWeight: 600, color: c.status==='resolved' ? 'var(--green)' : c.status==='open' ? 'var(--orange)' : 'var(--muted)' }}>{c.status.replace('_',' ')}</span></td>
                  <td>{['open','under_review'].includes(c.status) ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <input placeholder="Resolution note" id={`note-${c.complaint_id}`} style={{ padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 4, fontSize: '0.75rem', minWidth: 150, fontFamily: 'inherit' }} />
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="btn-primary btn-sm" onClick={() => act(`/registrar/complaint/${c.complaint_id}`, { status: 'resolved', resolution_note: document.getElementById(`note-${c.complaint_id}`)?.value })}>Resolve</button>
                        <button className="btn-secondary btn-sm" onClick={() => act(`/registrar/complaint/${c.complaint_id}`, { status: 'dismissed', resolution_note: '' })}>Dismiss</button>
                      </div>
                    </div>
                  ) : <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{c.resolution_note || '—'}</span>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>

      {/* GRADUATION APPS */}
      <div className="panel">
        <div className="panel-title">Graduation Applications ({data.grad_apps.length})</div>
        {data.grad_apps.length === 0 ? <p style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>No graduation applications.</p> : (
          <div className="table-wrap" style={{ boxShadow: 'none', border: '1px solid var(--border)' }}>
            <table>
              <thead><tr><th>Student</th><th>GPA</th><th>Submitted</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>{data.grad_apps.map(g => (
                <tr key={g.graduation_app_id}>
                  <td>{g.student_name}</td>
                  <td style={{ color: 'var(--green)', fontWeight: 600 }}>{Number(g.cumulative_gpa).toFixed(3)}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{g.submitted_at?.slice(0,10)}</td>
                  <td><span style={{ fontWeight: 600, color: g.decision_status==='approved' ? 'var(--green)' : g.decision_status==='rejected' ? 'var(--red)' : 'var(--orange)' }}>{g.decision_status}</span></td>
                  <td>{g.decision_status === 'pending' ? (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn-primary btn-sm" onClick={() => act(`/registrar/graduation/${g.graduation_app_id}`, { decision: 'approved' })}>Approve</button>
                      <button className="btn-secondary btn-sm" onClick={() => act(`/registrar/graduation/${g.graduation_app_id}`, { decision: 'rejected' })}>Reject</button>
                    </div>
                  ) : '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
