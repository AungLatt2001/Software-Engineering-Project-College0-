// client/src/components/Layout.jsx
import React from 'react';
import { useAuth } from '../context/AuthContext';

// "General" links: shown to visitors (apply + ai), only AI to logged-in users
// (a logged-in user has no reason to apply again — issue 1).
const NAV_PUBLIC_VISITOR = [
  { id: 'home',  icon: '🏠', label: 'Home' },
  { id: 'apply', icon: '📝', label: 'Apply' },
  { id: 'ai',    icon: '🤖', label: 'AI Assistant' },
];
const NAV_PUBLIC_LOGGED_IN = [
  { id: 'home',  icon: '🏠', label: 'Home' },
  { id: 'ai',    icon: '🤖', label: 'AI Assistant' },
];

const NAV_ROLE = {
  Student:    [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'courses',   icon: '📚', label: 'My Courses' },
    { id: 'grades',    icon: '🎓', label: 'Transcript' },
    { id: 'actions',   icon: '⚙️', label: 'Reviews & More' },
  ],
  Instructor: [
    { id: 'dashboard', icon: '📊', label: 'Dashboard' },
    { id: 'courses',   icon: '📚', label: 'My Classes' },
    { id: 'grades',    icon: '✏️', label: 'Submit Grades' },
    { id: 'actions',   icon: '📣', label: 'Complaints' },
  ],
  Registrar:  [
    { id: 'dashboard',          icon: '📊', label: 'Overview' },
    { id: 'courses',            icon: '📚', label: 'Manage Courses' },
    { id: 'students',           icon: '👤', label: 'Manage Students' },
    { id: 'instructors',        icon: '👨‍🏫', label: 'Manage Instructors' },
    { id: 'instructor-reviews', icon: '🎓', label: 'Faculty Review' },
    { id: 'actions',            icon: '📋', label: 'Applications' },
  ],
};

export function Sidebar({ page, setPage, phaseLabel, semester }) {
  const { user, logout } = useAuth();
  const publicLinks = user ? NAV_PUBLIC_LOGGED_IN : NAV_PUBLIC_VISITOR;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>College0</h1>
        <span>Academic Portal</span>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">General</div>
        {publicLinks.map(item => (
          <button
            key={item.id}
            className={`nav-btn${page === item.id ? ' active' : ''}`}
            onClick={() => setPage(item.id)}
          >
            <span className="icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}

        {user && NAV_ROLE[user.role] && (
          <>
            <div className="nav-section-label" style={{ marginTop: 12 }}>My Portal</div>
            {NAV_ROLE[user.role].map(item => (
              <button
                key={item.id}
                className={`nav-btn${page === item.id ? ' active' : ''}`}
                onClick={() => setPage(item.id)}
              >
                <span className="icon">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </>
        )}
      </nav>

      {user ? (
        <div className="sidebar-user">
          <div className="sidebar-user-card">
            <div className="sidebar-user-name">{user.name}</div>
            <div className="sidebar-user-role">{user.userId} · {user.role}</div>
            <button className="signout-btn" onClick={logout}>Sign Out</button>
          </div>
        </div>
      ) : (
        <div style={{ padding: '0 12px 16px' }}>
          <button
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', fontSize: 13 }}
            onClick={() => setPage('__login__')}
          >
            Sign In
          </button>
        </div>
      )}
    </aside>
  );
}

export function TopBar({ phaseLabel, semester, semesterLabel, onLoginClick, user }) {
  return (
    <header className="topbar">
      <div className="phase-chip">📅 {phaseLabel}</div>
      <div className="topbar-divider" />
      <div className="topbar-sem">{semesterLabel || `Semester ${semester}`}</div>
      <div className="topbar-right">
        {!user && (
          <button className="btn btn-primary btn-sm" onClick={onLoginClick}>
            Sign In
          </button>
        )}
      </div>
    </header>
  );
}
