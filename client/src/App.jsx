import React, { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import api from './api';
import Layout from './components/Layout';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import MyCourses from './pages/MyCourses';
import Transcript from './pages/Transcript';
import Reviews from './pages/Reviews';
import Instructor from './pages/Instructor';
import Registrar from './pages/Registrar';
import Apply from './pages/Apply';
import AIAssistant from './pages/AIAssistant';

export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function RequireRole({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading">Loading…</div>;
  if (!user || user.role !== role) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sem, setSem] = useState(null);
  const [loginOpen, setLoginOpen] = useState(false);

  useEffect(() => {
    api.get('/me').then(r => {
      setUser(r.data.user);
      setSem(r.data.sem);
    }).catch(() => {
      api.get('/sem').then(r => setSem(r.data)).catch(() => {});
    }).finally(() => setLoading(false));
  }, []);

  const logout = () => {
    api.post('/logout').then(() => { setUser(null); window.location.href = '/'; });
  };

  return (
    <AuthContext.Provider value={{ user, setUser, sem, setSem, loading, logout, loginOpen, setLoginOpen }}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/apply" element={<Apply />} />
            <Route path="/ai-assistant" element={<AIAssistant />} />
            <Route path="/dashboard" element={
              <RequireRole role="student"><Dashboard /></RequireRole>
            } />
            <Route path="/my-courses" element={
              <RequireRole role="student"><MyCourses /></RequireRole>
            } />
            <Route path="/transcript" element={
              <RequireRole role="student"><Transcript /></RequireRole>
            } />
            <Route path="/reviews" element={
              <RequireRole role="student"><Reviews /></RequireRole>
            } />
            <Route path="/instructor" element={
              <RequireRole role="instructor"><Instructor /></RequireRole>
            } />
            <Route path="/registrar" element={
              <RequireRole role="registrar"><Registrar /></RequireRole>
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
