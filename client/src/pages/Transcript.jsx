import React, { useEffect, useState } from 'react';
import { useAuth } from '../App';
import api from '../api';

export default function Transcript() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  useEffect(() => { api.get('/transcript').then(r => setData(r.data)).catch(() => {}); }, []);
  if (!data) return <div className="loading">Loading…</div>;
  const { st, history } = data;

  return (
    <>
      <div className="page-header">
        <h1>Academic Transcript</h1>
        <p>Your complete grade history and academic standing.</p>
      </div>

      <div className="transcript-stats">
        <div className="transcript-stat">
          <div className="ts-label">Cumulative GPA</div>
          <div className="ts-value">{Number(st?.cumulative_gpa).toFixed(3)}</div>
        </div>
        <div className="transcript-stat">
          <div className="ts-label">Semester GPA</div>
          <div className="ts-value">{Number(st?.semester_gpa).toFixed(3)}</div>
        </div>
        <div className="transcript-stat">
          <div className="ts-label">Warnings</div>
          <div className={`ts-value ${user?.warning_count > 0 ? 'warn' : 'neutral'}`}>{user?.warning_count}/3</div>
        </div>
        <div className="transcript-stat">
          <div className="ts-label">Honor Count</div>
          <div className="ts-value neutral">{st?.honor_count}</div>
          <div className="ts-sub">Each removes 1 warning</div>
        </div>
        {st?.fine_due > 0 && (
          <div className="transcript-stat">
            <div className="ts-label">Fine Due</div>
            <div className="ts-value warn">${Number(st.fine_due).toFixed(2)}</div>
          </div>
        )}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Code</th><th>Course Title</th><th>Credits</th><th>Grade</th><th>Points</th><th>Semester</th></tr>
          </thead>
          <tbody>
            {history.length === 0 && (
              <tr><td colSpan={6} style={{ color: 'var(--muted)', padding: 18 }}>No completed courses yet.</td></tr>
            )}
            {history.map((h, i) => (
              <tr key={i}>
                <td><strong>{h.code}</strong></td>
                <td>{h.title}</td>
                <td>{h.credit_hours}</td>
                <td><strong>{h.letter_grade}</strong></td>
                <td>{Number(h.grade_points).toFixed(2)}</td>
                <td>{h.term_name} {h.year}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
