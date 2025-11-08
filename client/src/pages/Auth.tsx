import { useState } from 'react';
import axios from 'axios';
import { Button, Card, Input } from '../components/ui';
import { FileText, Sparkles } from 'lucide-react';

interface AuthProps {
  backendUrl: string;
  onAuth: (token: string) => void;
}

export default function AuthPage({ backendUrl, onAuth }: AuthProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === 'signup') {
        await axios.post(`${backendUrl}/auth/signup`, { email, password, full_name: fullName });
        setMode('login');
        setError(null);
      } else {
        const resp = await axios.post(`${backendUrl}/auth/login_simple`, { email, password });
        onAuth(resp.data.access_token);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-light via-background to-accent-light">
      {/* Decorative blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="relative">
        <header className="px-6 py-8 text-center">
          <div className="mx-auto inline-flex items-center gap-3 fade-in">
            <div className="flex items-center justify-center h-12 w-12 rounded-2xl bg-gradient-to-br from-primary to-accent shadow-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div className="text-left">
              <h1 className="text-2xl font-bold text-foreground">Patent Reviewer</h1>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                AI-Powered Document Analysis
              </p>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-md px-6 pb-16 fade-in">
          <Card 
            title={mode === 'login' ? 'Welcome back' : 'Create your account'} 
            subtitle={mode === 'login' ? 'Log in to continue reviewing patents' : 'Sign up to get started with AI analysis'}
            className="backdrop-blur-xl bg-card/80"
          >
            <div className="mb-6 flex gap-2 p-1 bg-muted rounded-lg">
              <Button 
                variant={mode === 'login' ? 'primary' : 'ghost'} 
                onClick={() => setMode('login')}
                className="flex-1"
                size="sm"
              >
                Login
              </Button>
              <Button 
                variant={mode === 'signup' ? 'primary' : 'ghost'} 
                onClick={() => setMode('signup')}
                className="flex-1"
                size="sm"
              >
                Sign Up
              </Button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'signup' && (
                <div>
                  <label className="mb-2 block text-sm font-medium text-foreground">Full Name</label>
                  <Input 
                    value={fullName} 
                    onChange={e => setFullName(e.target.value)} 
                    placeholder="Your name" 
                  />
                </div>
              )}
              
              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">Email</label>
                <Input 
                  type="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)} 
                  placeholder="you@example.com" 
                  required 
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">Password</label>
                <Input 
                  type="password" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  placeholder="Enter a secure password" 
                  required 
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-destructive-light border border-destructive/20 text-sm text-destructive fade-in">
                  {error}
                </div>
              )}

              <Button 
                type="submit" 
                className="w-full" 
                size="lg"
                disabled={loading}
              >
                {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create Account'}
              </Button>
            </form>

            <div className="mt-6 pt-6 border-t border-border">
              <p className="text-center text-xs text-muted-foreground">
                Default credentials: <span className="font-mono text-foreground">master@example.com</span> / <span className="font-mono text-foreground">password123</span>
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
