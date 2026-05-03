import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

export default function Reviews() {
  const { sem } = useAuth();
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('review');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const [reviewSection, setReviewSection] = useState('');
  const [reviewRating, setReviewRating] = useState('5');
  const [reviewText, setReviewText] = useState('');

  const [targetId, setTargetId] = useState('');
  const [complaintText, setComplaintText] = useState('');

  useEffect(() => { api.get('/reviews/data').then(r => setData(r.data)).catch(() => {}); }, []);

  const submit = async (type, payload) => {
    setBusy(true); setMsg('');
    try {
      const r = await api.post(`/reviews/${type}`, payload);
      setMsg(r.data.msg);
    } catch (err) { setMsg(err.response?.data?.msg || 'An error occurred.'); }
    finally { setBusy(false); }
  };

  if (!data) return <div className="loading">Loading…</div>;

  return (
    <>
      <div className="page-header">
        <h1>Reviews, Graduation &amp; Complaints</h1>
      </div>

      {msg && <div className="alert alert-success">{msg}</div>}

      <div className="tabs">
        {[['review','🏆 Course Review'],['graduation','🎓 Graduation'],['complaint','📢 Complaint']].map(([k,label]) => (
          <button key={k} className={`tab-btn${tab===k?' active':''}`} onClick={() => setTab(k)}>{label}</button>
        ))}
      </div>

      {tab === 'review' && (
        <div style={{ maxWidth: 600 }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 6 }}>Submit a Course Review</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--muted)', marginBottom: 18 }}>Reviews are anonymous. Only available during the Grading phase.</p>
          {sem?.phase !== 'grading' && (
            <div className="alert alert-info">Reviews are only available during the Grading phase. Current phase: <strong>{sem?.phase}</strong>.</div>
          )}
          <form onSubmit={e => { e.preventDefault(); submit('review', { section_id: parseInt(reviewSection), rating: parseInt(reviewRating), review_text: reviewText }); }}>
            <div className="form-group">
              <label>Section</label>
              <select value={reviewSection} onChange={e => setReviewSection(e.target.value)} required>
                <option value="">Select a section...</option>
                {data.my_sections.map(s => (
                  <option key={s.section_id} value={s.section_id}>{s.code} — {s.title} ({s.term_name} {s.year})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Rating</label>
              <select value={reviewRating} onChange={e => setReviewRating(e.target.value)}>
                {[['5','5 ★★★★★ — Excellent'],['4','4 ★★★★ — Good'],['3','3 ★★★ — Average'],['2','2 ★★ — Below Average'],['1','1 ★ — Poor']].map(([v,l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Review Text</label>
              <textarea value={reviewText} onChange={e => setReviewText(e.target.value)} placeholder="Share your feedback (anonymous)..." />
            </div>
            <button type="submit" className="btn-primary" disabled={busy || sem?.phase !== 'grading'} style={sem?.phase !== 'grading' ? { opacity: 0.5, cursor: 'not-allowed' } : {}}>
              Submit Review
            </button>
          </form>
        </div>
      )}

      {tab === 'graduation' && (
        <div style={{ maxWidth: 560 }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 6 }}>Apply for Graduation</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--muted)', marginBottom: 18 }}>Ensure you have completed all core courses, maintain a cumulative GPA ≥ 2.0, and have no outstanding fines or active warnings.</p>
          <div className="info-box">Required core courses: CSC101, CSC201, CSC301, CSC401, MTH101, MTH201, ENG101, CSC499.</div>
          <button className="btn-primary" disabled={busy} onClick={() => submit('graduation', {})}>Submit Graduation Application</button>
        </div>
      )}

      {tab === 'complaint' && (
        <div style={{ maxWidth: 560 }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 6 }}>Submit a Complaint</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--muted)', marginBottom: 18 }}>All complaints are reviewed confidentially by the Registrar.</p>
          <form onSubmit={e => { e.preventDefault(); submit('complaint', { target_user_id: parseInt(targetId), complaint_text: complaintText }); }}>
            <div className="form-group">
              <label>Complaint Against</label>
              <select value={targetId} onChange={e => setTargetId(e.target.value)} required>
                <option value="">Select a person...</option>
                {data.potential_targets.map(t => (
                  <option key={t.user_id} value={t.user_id}>{t.name} ({t.role})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea value={complaintText} onChange={e => setComplaintText(e.target.value)} placeholder="Describe your complaint in detail..." required />
            </div>
            <button type="submit" className="btn-primary" disabled={busy}>Submit Complaint</button>
          </form>
        </div>
      )}
    </>
  );
}
