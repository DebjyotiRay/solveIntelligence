import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button, Card, Input, Textarea, SectionTitle } from '../components/ui';
import { 
  FileText, 
  LogOut, 
  Plus, 
  FolderOpen, 
  Users, 
  Check, 
  X, 
  ArrowRight,
  Sparkles
} from 'lucide-react';

interface DashboardProps {
  backendUrl: string;
  onLogout: () => void;
  onOpenDocument: (documentId: number) => void;
}

interface DashboardDocument {
  project_id: number;
  document_id: number;
  document_title: string;
}

interface AccessRequestItem {
  id: number;
  project_id: number;
  user_id: number;
  role: string;
  status: string;
}

interface ProjectRead {
  id: number;
  name: string;
  owner_id: number;
  document_id?: number | null;
}

export default function Dashboard({ backendUrl, onLogout, onOpenDocument }: DashboardProps) {
  const [docs, setDocs] = useState<DashboardDocument[]>([]);
  const [myProjects, setMyProjects] = useState<ProjectRead[]>([]);
  const [projectIdInput, setProjectIdInput] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [manageProjectId, setManageProjectId] = useState<string>('');
  const [pending, setPending] = useState<AccessRequestItem[]>([]);
  const [ownerMessage, setOwnerMessage] = useState<string>('');
  const [creating, setCreating] = useState<boolean>(false);
  const [createName, setCreateName] = useState<string>('');
  const [createDocTitle, setCreateDocTitle] = useState<string>('');
  const [createContent, setCreateContent] = useState<string>('');
  const [createVersionName, setCreateVersionName] = useState<string>('');
  const [createMsg, setCreateMsg] = useState<string>('');

  const load = async () => {
    try {
      const resp = await axios.get(`${backendUrl}/dashboard/documents`);
      setDocs(resp.data);
    } catch {}
    try {
      const pr = await axios.get(`${backendUrl}/projects`);
      setMyProjects(pr.data || []);
    } catch {}
  };

  useEffect(() => {
    load();
  }, []);

  const requestAccess = async () => {
    setMessage('');
    const pid = Number(projectIdInput);
    if (!pid) return;
    try {
      const resp = await axios.post(`${backendUrl}/projects/${pid}/request-access`);
      setMessage(resp.data?.message || 'Requested');
    } catch (e: any) {
      setMessage(e?.response?.data?.detail || 'Failed to request');
    }
  };

  const loadRequests = async () => {
    setOwnerMessage('');
    setPending([]);
    const pid = Number(manageProjectId);
    if (!pid) return;
    try {
      const resp = await axios.get(`${backendUrl}/projects/${pid}/access-requests`);
      setPending(resp.data || []);
      if ((resp.data || []).length === 0) setOwnerMessage('No pending requests.');
    } catch (e: any) {
      setOwnerMessage(e?.response?.data?.detail || 'Failed to load requests');
    }
  };

  const approve = async (pid: number, userId: number) => {
    setOwnerMessage('');
    try {
      await axios.post(`${backendUrl}/projects/${pid}/approve/${userId}`);
      setPending(pending.filter(p => p.user_id !== userId));
    } catch (e: any) {
      setOwnerMessage(e?.response?.data?.detail || 'Approve failed');
    }
  };

  const reject = async (pid: number, userId: number) => {
    setOwnerMessage('');
    try {
      await axios.post(`${backendUrl}/projects/${pid}/reject/${userId}`);
      setPending(pending.filter(p => p.user_id !== userId));
    } catch (e: any) {
      setOwnerMessage(e?.response?.data?.detail || 'Reject failed');
    }
  };

  const createProject = async () => {
    setCreateMsg('');
    if (!createName || !createContent) {
      setCreateMsg('Name and content are required');
      return;
    }
    setCreating(true);
    try {
      const resp = await axios.post(`${backendUrl}/projects/create_with_document`, {
        name: createName,
        document_title: createDocTitle || undefined,
        content: createContent,
        version_name: createVersionName || undefined,
      });
      const proj = resp.data as ProjectRead;
      setCreateMsg(`Created project '${proj.name}' (ID ${proj.id}).`);
      setCreateName('');
      setCreateDocTitle('');
      setCreateContent('');
      setCreateVersionName('');
      await load();
    } catch (e: any) {
      setCreateMsg(e?.response?.data?.detail || 'Create failed');
    }
    setCreating(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-light via-background to-accent-light">
      {/* Decorative background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="relative">
        {/* Header */}
        <header className="sticky top-0 z-50 border-b border-border backdrop-blur-xl bg-card/80">
          <div className="mx-auto max-w-7xl flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-gradient-to-br from-primary to-accent shadow-lg">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-foreground">Patent Reviewer</h1>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Dashboard
                </p>
              </div>
            </div>
            <Button variant="ghost" onClick={onLogout} size="sm">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
          {/* Quick Actions Section */}
          <div className="fade-in">
            <SectionTitle>Quick Actions</SectionTitle>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mt-4">
              {/* Create Project Card */}
              <Card 
                title="Create New Project" 
                subtitle="Start a project with an initial document version"
                className="backdrop-blur-xl bg-card/80 hover-lift"
              >
                <div className="space-y-4">
                  <Input 
                    value={createName} 
                    onChange={e => setCreateName(e.target.value)} 
                    placeholder="Project name (required)" 
                  />
                  <Input 
                    value={createDocTitle} 
                    onChange={e => setCreateDocTitle(e.target.value)} 
                    placeholder="Document title (optional)" 
                  />
                  <Textarea 
                    value={createContent} 
                    onChange={e => setCreateContent(e.target.value)} 
                    placeholder="Initial document content (required)" 
                    className="h-28" 
                  />
                  <Input 
                    value={createVersionName} 
                    onChange={e => setCreateVersionName(e.target.value)} 
                    placeholder="Initial version name (optional)" 
                  />
                  <div className="flex items-center gap-3">
                    <Button onClick={createProject} disabled={creating}>
                      <Plus className="w-4 h-4 mr-2" />
                      {creating ? 'Creating...' : 'Create Project'}
                    </Button>
                  </div>
                  {createMsg && (
                    <div className="p-3 rounded-lg bg-success-light border border-success/20 text-sm text-foreground fade-in">
                      {createMsg}
                    </div>
                  )}
                </div>
              </Card>

              {/* Request Access Card */}
              <Card 
                title="Request Project Access" 
                subtitle="Enter a project ID to request access from the owner"
                className="backdrop-blur-xl bg-card/80 hover-lift"
              >
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <Input 
                      value={projectIdInput} 
                      onChange={e => setProjectIdInput(e.target.value)} 
                      placeholder="Project ID" 
                      className="flex-1"
                    />
                    <Button onClick={requestAccess}>
                      <ArrowRight className="w-4 h-4 mr-2" />
                      Request
                    </Button>
                  </div>
                  {message && (
                    <div className="p-3 rounded-lg bg-primary-light border border-primary/20 text-sm text-foreground fade-in">
                      {message}
                    </div>
                  )}
                </div>
              </Card>
            </div>
          </div>

          {/* Management Section */}
          <div className="fade-in">
            <SectionTitle>Project Management</SectionTitle>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 mt-4">
              {/* Manage Access Requests */}
              <Card 
                title="Manage Access Requests" 
                subtitle="For owners: load and review pending requests"
                className="backdrop-blur-xl bg-card/80"
              >
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <Input 
                      value={manageProjectId} 
                      onChange={e => setManageProjectId(e.target.value)} 
                      placeholder="Project ID" 
                      className="flex-1"
                    />
                    <Button variant="secondary" onClick={loadRequests}>
                      <Users className="w-4 h-4 mr-2" />
                      Load
                    </Button>
                  </div>
                  {ownerMessage && (
                    <div className="text-sm text-muted-foreground fade-in">{ownerMessage}</div>
                  )}
                  {pending.length > 0 && (
                    <ul className="space-y-3">
                      {pending.map(req => (
                        <li 
                          key={req.id} 
                          className="flex items-center justify-between p-4 rounded-xl border border-border bg-card/50 hover:bg-card/80 transition-colors"
                        >
                          <div>
                            <div className="font-medium text-foreground">User #{req.user_id}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              Status: <span className="font-mono">{req.status}</span> · Role: <span className="font-mono">{req.role}</span>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button 
                              variant="success" 
                              size="sm" 
                              onClick={() => approve(req.project_id, req.user_id)}
                            >
                              <Check className="w-4 h-4" />
                            </Button>
                            <Button 
                              variant="danger" 
                              size="sm" 
                              onClick={() => reject(req.project_id, req.user_id)}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </Card>

              {/* My Projects */}
              <Card 
                title="My Projects" 
                subtitle="Projects you own or belong to"
                className="backdrop-blur-xl bg-card/80"
              >
                {myProjects.length === 0 ? (
                  <div className="text-center py-8">
                    <FolderOpen className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
                    <p className="text-sm text-muted-foreground">
                      You don't own or belong to any projects yet.
                    </p>
                  </div>
                ) : (
                  <ul className="space-y-3">
                    {myProjects.map(p => (
                      <li 
                        key={p.id} 
                        className="p-4 rounded-xl border border-border bg-card/50 hover:bg-card/80 transition-colors group cursor-pointer"
                        onClick={() => p.document_id && onOpenDocument(p.document_id)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-medium text-foreground group-hover:text-primary transition-colors">
                            {p.name}
                          </div>
                          {p.document_id && (
                            <Button 
                              variant="primary" 
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenDocument(p.document_id!);
                              }}
                            >
                              <FileText className="w-3 h-3 mr-1" />
                              Open
                            </Button>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Project #<span className="font-mono">{p.id}</span> · 
                          Owner #<span className="font-mono">{p.owner_id}</span> · 
                          Document #<span className="font-mono">{p.document_id ?? 'none'}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>
          </div>

          {/* Documents Section */}
          <div className="fade-in">
            <SectionTitle>Available Documents</SectionTitle>
            <Card 
              title="My Accessible Documents" 
              subtitle="Documents you can open from your memberships"
              className="backdrop-blur-xl bg-card/80 mt-4"
            >
              {docs.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                  <p className="text-sm text-muted-foreground">
                    No documents available.
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Ask a project owner to approve your request.
                  </p>
                </div>
              ) : (
                <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {docs.map(d => (
                    <li 
                      key={`${d.project_id}-${d.document_id}`} 
                      className="group p-5 rounded-xl border border-border bg-gradient-to-br from-card to-card/50 hover:shadow-lg transition-all"
                    >
                      <div className="mb-4">
                        <div className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {d.document_title}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Project #<span className="font-mono">{d.project_id}</span> · 
                          Doc #<span className="font-mono">{d.document_id}</span>
                        </div>
                      </div>
                      <Button 
                        variant="primary" 
                        onClick={() => onOpenDocument(d.document_id)}
                        className="w-full"
                        size="sm"
                      >
                        <FileText className="w-4 h-4 mr-2" />
                        Open Document
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}
