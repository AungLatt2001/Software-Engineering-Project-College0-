import React from 'react';
import { useLocation, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../App';
import LoginModal from './LoginModal';

export default function Layout({ children }) {
  const { user, sem, loading, logout, setLoginOpen } = useAuth();
  const loc = useLocation();

  const navItem = (to, icon, label) => (
    <Link to={to} className={`nav-item${loc.pathname === to ? ' active' : ''}`}>
      <span className="nav-icon">{icon}</span>
      <span className="nav-text">{label}</span>
    </Link>
  );

  return (
    <>
      <header className="topbar">
        <div className="topbar-left">
          <div className="logo">
            <Link to="/" style={{ textDecoration: 'none' }}>
              <span className="logo-text">College0</span>
              <span className="logo-sub">Academic Portal</span>
            </Link>
          </div>
        </div>
        <div className="topbar-center">
          {sem && <>
            <span className="phase-badge">{sem.phase}</span>
            <span className="semester-label">{sem.term_name} {sem.year}</span>
          </>}
        </div>
        <div className="topbar-right">
          {user
            ? <button className="btn-signin" onClick={logout}>Sign Out</button>
            : <button className="btn-signin" onClick={() => setLoginOpen(true)}>Sign In</button>
          }
        </div>
      </header>

      <div className="layout">
        <nav className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-label">General</div>
            {navItem('/', '⌂', 'Home')}
            {navItem('/apply', '📄', 'Apply')}
            {navItem('/ai-assistant', '🤖', 'AI Assistant')}
          </div>

          {user?.role === 'student' && (
            <div className="sidebar-section">
              <div className="sidebar-label">My Portal</div>
              {navItem('/dashboard', '⎇', 'Dashboard')}
              {navItem('/my-courses', '📚', 'My Courses')}
              {navItem('/transcript', '📋', 'Transcript')}
              {navItem('/reviews', '⭐', 'Reviews & More')}
            </div>
          )}

          {user?.role === 'instructor' && (
            <div className="sidebar-section">
              <div className="sidebar-label">Instructor</div>
              {navItem('/instructor', '⎇', 'My Classes')}
            </div>
          )}

          {user?.role === 'registrar' && (
            <div className="sidebar-section">
              <div className="sidebar-label">Admin</div>
              {navItem('/registrar', '⎇', 'Registrar')}
            </div>
          )}

          {user && (
            <div className="sidebar-user">
              <div className="sidebar-user-name">{user.first_name} {user.last_name}</div>
              <div className="sidebar-user-id">#{user.user_id} · {user.role}</div>
              <button className="btn-signout" onClick={logout}>Sign Out</button>
            </div>
          )}
        </nav>

        <main className="main-content">{children}</main>
      </div>

      <LoginModal />
    </>
  );
}
