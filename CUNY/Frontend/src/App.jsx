// client/src/App.jsx
import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar, TopBar } from './components/Layout';
import {
  HomePage, LoginModal, ApplyPage, AIPage, TutorialModal,
  StudentDashboard, StudentCourses, StudentGrades, StudentActions,
  InstructorDashboard, InstructorCourses, InstructorGrades, InstructorComplaints,
  RegistrarDashboard, RegistrarCourses, RegistrarStudents, RegistrarActions,
  RegistrarInstructorReviews, RegistrarInstructors,
} from './pages/Pages';
import { api } from './context/AuthContext';
import './index.css';

function AppShell() {
  const { user, logout } = useAuth();
  const [page, setPage] = useState('home');
  const [phase, setPhase] = useState({ label: 'Class Setup', semester: 1, semesterLabel: 'Spring 2025' });
  const [showLogin, setShowLogin] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);

  useEffect(() => {
    api.get('/public').then(r => setPhase({
      label: r.data.phaseLabel,
      semester: r.data.semester,
      semesterLabel: r.data.label || `Semester ${r.data.semester}`,
    })).catch(() => {});
  }, [page]);

  useEffect(() => {
    if (!user) setPage('home');
  }, [user]);

  // Intercept the sidebar's __login__ signal
  const handleSetPage = (p) => {
    if (p === '__login__') { setShowLogin(true); return; }
    setPage(p);
  };

  // After login: if it was a first login (password just changed), show the
  // tutorial for newly approved users. This matches the spec requirement:
  // "Once approved, the system provides a tutorial to introduce the
  // functionalities to the student/instructor."
  const handleLoginSuccess = (u, wasFirstLogin) => {
    setShowLogin(false);
    setPage('dashboard');
    if (wasFirstLogin) setShowTutorial(true);
  };

  const renderPage = () => {
    switch (page) {
      case 'home':      return <HomePage onLogin={() => setShowLogin(true)} />;
      case 'apply':     return <ApplyPage />;
      case 'ai':        return <AIPage />;
      case 'dashboard': return user?.role === 'Student'    ? <StudentDashboard onShowTutorial={() => setShowTutorial(true)} />
                             : user?.role === 'Instructor' ? <InstructorDashboard onShowTutorial={() => setShowTutorial(true)} />
                             : <RegistrarDashboard />;
      case 'courses':   return user?.role === 'Student'    ? <StudentCourses />
                             : user?.role === 'Instructor' ? <InstructorCourses />
                             : <RegistrarCourses />;
      case 'grades':    return user?.role === 'Student'    ? <StudentGrades />
                             : user?.role === 'Instructor' ? <InstructorGrades />
                             : <RegistrarStudents />;
      case 'actions':   return user?.role === 'Student'    ? <StudentActions />
                             : user?.role === 'Instructor' ? <InstructorComplaints />
                             : <RegistrarActions />;
      case 'students':           return <RegistrarStudents />;
      case 'instructors':        return <RegistrarInstructors />;
      case 'instructor-reviews': return <RegistrarInstructorReviews />;
      default:          return <HomePage onLogin={() => setShowLogin(true)} />;
    }
  };

  return (
    <div className="app-shell">
      <Sidebar page={page} setPage={handleSetPage} />

      <div className="main-area">
        <TopBar
          phaseLabel={phase.label}
          semester={phase.semester}
          semesterLabel={phase.semesterLabel}
          onLoginClick={() => setShowLogin(true)}
          user={user}
        />
        <main className="page-content">
          {renderPage()}
        </main>
      </div>

      {/* Login modal — overlays on top, home page stays visible behind it */}
      {showLogin && (
        <LoginModal
          onSuccess={handleLoginSuccess}
          onClose={() => setShowLogin(false)}
        />
      )}

      {/* First-login / on-demand tutorial overlay */}
      {showTutorial && user && (
        <TutorialModal
          role={user.role}
          onClose={() => setShowTutorial(false)}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
