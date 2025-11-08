import { useEffect, useState } from 'react';
import axios from 'axios';
import AuthPage from './pages/Auth';
import Dashboard from './pages/Dashboard';
import App from './App';

const BACKEND_URL = "http://localhost:8000";

type View = 'auth' | 'dashboard' | 'editor';

export default function Root() {
  const [view, setView] = useState<View>('auth');
  const [token, setToken] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    if (t) {
      setToken(t);
      axios.defaults.headers.common['Authorization'] = `Bearer ${t}`;
      setView('dashboard');
    }
  }, []);

  const handleLogin = (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    setView('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    delete axios.defaults.headers.common['Authorization'];
    setView('auth');
  };

  const handleOpenDocument = (documentId: number) => {
    setSelectedDocumentId(documentId);
    setView('editor');
  };

  if (view === 'auth') {
    return <AuthPage backendUrl={BACKEND_URL} onAuth={handleLogin} />;
  }

  if (view === 'dashboard') {
    return <Dashboard backendUrl={BACKEND_URL} onLogout={handleLogout} onOpenDocument={handleOpenDocument} />;
  }

  if (view === 'editor' && selectedDocumentId) {
    return <App initialDocumentId={selectedDocumentId} />;
  }

  return null;
}
