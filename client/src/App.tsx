import { useEffect, useState, useCallback } from "react";
import axios from "axios";
import Document from "./Document";
import LoadingOverlay from "./internal/LoadingOverlay";
import SuggestionsPanel from "./components/SuggestionsPanel";
import { ChatPanel } from "./components/ChatPanel";
import { useSocket } from "./hooks/useSocket";
import { PatentIssue, PanelSuggestion } from "./types/PatentTypes";
import { Button } from "./components/UI";
import { 
  FileText, 
  Save, 
  Plus, 
  Sparkles, 
  Users,
  AlertCircle,
  CheckCircle
} from "lucide-react";

const BACKEND_URL = "http://localhost:8000";

interface DocumentVersion {
  id: number;
  document_id: number;
  version_number: number;
  content: string;
  created_at: string;
  name: string;
}

interface DocumentInfo {
  id: number;
  title: string;
}

interface CollaborationUser {
  name: string;
  color: string;
}

interface AppProps {
  initialDocumentId?: number;
}

function App({ initialDocumentId }: AppProps) {
  // Stateless frontend state management
  const [currentDocumentContent, setCurrentDocumentContent] = useState<string>("");
  const [currentDocumentId, setCurrentDocumentId] = useState<number>(0);
  const [currentDocumentInfo, setCurrentDocumentInfo] = useState<DocumentInfo | null>(null);
  const [selectedVersionNumber, setSelectedVersionNumber] = useState<number>(1);
  const [availableVersions, setAvailableVersions] = useState<DocumentVersion[]>([]);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Panel suggestion state
  const [activePanelSuggestion, setActivePanelSuggestion] = useState<PanelSuggestion | null>(null);
  
  // Online users state
  const [onlineUsersCount, setOnlineUsersCount] = useState<number>(0);
  const [onlineUsers, setOnlineUsers] = useState<CollaborationUser[]>([]);
  const [currentUser, setCurrentUser] = useState<CollaborationUser | null>(null);

  // WebSocket integration for AI suggestions
  const {
    isConnected,
    isAnalyzing,
    analysisResult,
    requestAISuggestions,
    currentPhase,
    streamUpdates,
    requestInlineSuggestion,
    pendingSuggestion,
    acceptInlineSuggestion,
    rejectInlineSuggestion,
  } = useSocket();

  // Load initial document on mount
  useEffect(() => {
    if (initialDocumentId) {
      loadPatent(initialDocumentId);
    } else {
      loadPatent(1);
    }
  }, []);

  const loadPatent = async (documentId: number) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const base = token ? `${BACKEND_URL}/secure` : `${BACKEND_URL}`;
      
      const infoResponse = await axios.get(`${base}/document/${documentId}`);
      setCurrentDocumentInfo(infoResponse.data);

      const versionsResponse = await axios.get(`${base}/document/${documentId}/versions`);
      const versions = versionsResponse.data;
      setAvailableVersions(versions);

      if (versions.length > 0) {
        const latest = versions[versions.length - 1];
        setCurrentDocumentContent(latest.content);
        setSelectedVersionNumber(latest.version_number);
      }

      setCurrentDocumentId(documentId);
      setIsDirty(false);
    } catch (error) {
      console.error("Error loading patent:", error);
    }
    setIsLoading(false);
  };

  const saveCurrentVersion = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const base = token ? `${BACKEND_URL}/secure` : `${BACKEND_URL}`;
      
      await axios.put(`${base}/document/${currentDocumentId}/versions/${selectedVersionNumber}`, {
        content: currentDocumentContent
      });
      
      setIsDirty(false);
      
      const updatedVersionsResponse = await axios.get(`${base}/document/${currentDocumentId}/versions`);
      setAvailableVersions(updatedVersionsResponse.data);
    } catch (error) {
      console.error("Error saving version:", error);
    }
    setIsLoading(false);
  };

  const createNewVersion = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const base = token ? `${BACKEND_URL}/secure` : `${BACKEND_URL}`;
      
      const response = await axios.post(`${base}/document/${currentDocumentId}/versions`, {
        content: currentDocumentContent,
        name: `Version ${availableVersions.length + 1}`
      });
      const newVersion = response.data;

      setAvailableVersions(prev => [...prev, newVersion]);
      setSelectedVersionNumber(newVersion.version_number);
      setIsDirty(false);
    } catch (error) {
      console.error("Error creating new version:", error);
    }
    setIsLoading(false);
  };

  const switchToVersion = async (versionNumber: number) => {
    if (versionNumber === selectedVersionNumber) return;

    if (isDirty) {
      const confirmSwitch = window.confirm(
        "You have unsaved changes. Do you want to switch versions without saving? Your changes will be lost."
      );
      if (!confirmSwitch) return;
    }

    const version = availableVersions.find(v => v.version_number === versionNumber);
    if (version) {
      setSelectedVersionNumber(versionNumber);
      setCurrentDocumentContent(version.content);
      setIsDirty(false);
    }
  };

  const handleContentChange = (content: string) => {
    console.log('📝 Content changed, new length:', content.length);
    console.log('📝 Content preview:', content.substring(0, 200));
    setCurrentDocumentContent(content);
    setIsDirty(true);
  };

  const handleRequestSuggestions = (content: string) => {
    console.log('🔍 Analysis requested with content length:', content.length);
    console.log('🔍 Content preview:', content.substring(0, 200));
    console.log('🔍 Current state content length:', currentDocumentContent.length);
    console.log('🔍 Are they the same?', content === currentDocumentContent);

    if (isConnected) {
      requestAISuggestions(content);
    }
  };

  const handleShowSuggestionLocation = (issue: PatentIssue) => {
    const panelSuggestion: PanelSuggestion = {
      issue
    };
    setActivePanelSuggestion(panelSuggestion);
  };

  const handleDismissPanelSuggestion = () => {
    setActivePanelSuggestion(null);
  };

  const handleOnlineUsersChange = useCallback((count: number, users: CollaborationUser[], selfUser?: CollaborationUser) => {
    setOnlineUsersCount(count);
    setOnlineUsers(users);
    if (selfUser) {
      setCurrentUser(prevUser => prevUser || selfUser);
    }
  }, []);

  return (
    <div className="flex flex-col h-screen w-full bg-background">
      {isLoading && <LoadingOverlay />}
      
      {/* Header */}
      <header className="flex-shrink-0 border-b border-border bg-card/80 backdrop-blur-xl">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-gradient-to-br from-primary to-accent shadow-lg">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-foreground">
                  {currentDocumentInfo?.title || `Patent ${currentDocumentId}`}
                  {isDirty && <span className="text-destructive ml-2">*</span>}
                </h1>
                {availableVersions.length > 0 && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>Version:</span>
                    <select
                      value={selectedVersionNumber}
                      onChange={(e) => switchToVersion(Number(e.target.value))}
                      className="border border-input rounded-md px-2 py-1 bg-card text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                      {availableVersions.map(version => (
                        <option key={version.version_number} value={version.version_number}>
                          {version.name || `v${version.version_number}`}
                        </option>
                      ))}
                    </select>
                    {isDirty && (
                      <span className="text-destructive font-medium ml-1">
                        (unsaved)
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Online Users Indicator */}
            {(onlineUsersCount > 0 || currentUser) && (
              <div className="flex items-center gap-2 bg-muted rounded-full px-3 py-1.5">
                <Users className="w-4 h-4 text-muted-foreground" />
                <div className="flex -space-x-2">
                  {currentUser && (
                    <div
                      className="w-7 h-7 rounded-full border-2 border-card flex items-center justify-center text-white text-xs font-bold"
                      style={{ backgroundColor: currentUser.color }}
                      title={`${currentUser.name} (You)`}
                    >
                      {currentUser.name?.charAt(0).toUpperCase()}
                    </div>
                  )}
                  {onlineUsers.map((user, index) => (
                    <div
                      key={index}
                      className="w-7 h-7 rounded-full border-2 border-card flex items-center justify-center text-white text-xs font-bold"
                      style={{ backgroundColor: user.color }}
                      title={user.name}
                    >
                      {user.name?.charAt(0).toUpperCase()}
                    </div>
                  ))}
                </div>
                <span className="text-xs text-muted-foreground font-medium ml-1">
                  {onlineUsersCount + 1} online
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Connection Status */}
            <div className="flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg bg-muted">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success' : 'bg-destructive'}`}></div>
              <span className="text-xs text-muted-foreground font-medium">
                {isConnected ? 'AI Connected' : 'AI Offline'}
              </span>
            </div>

            {/* Quick Switch Documents */}
            <div className="flex gap-2">
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => loadPatent(1)}
              >
                Patent 1
              </Button>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => loadPatent(2)}
              >
                Patent 2
              </Button>
            </div>
          </div>
        </div>

        {/* Action Bar */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-muted/30">
          <div className="flex items-center gap-3">
            <Button
              onClick={saveCurrentVersion}
              disabled={!isDirty || isLoading}
              variant={isDirty ? "success" : "secondary"}
              size="sm"
            >
              {isDirty ? (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save v{selectedVersionNumber}
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Saved
                </>
              )}
            </Button>
            <Button
              onClick={createNewVersion}
              disabled={isLoading}
              variant="secondary"
              size="sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Version
            </Button>
            {availableVersions.length > 1 && (
              <span className="text-xs text-muted-foreground">
                {availableVersions.length} versions
              </span>
            )}
          </div>

          <Button
            onClick={() => handleRequestSuggestions(currentDocumentContent)}
            disabled={!isConnected || isLoading}
            variant="primary"
            size="md"
            className="px-6"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            {isAnalyzing ? 'Analyzing...' : 'Run AI Analysis'}
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Document Editor - Left 60% */}
        <div className="w-3/5 h-full border-r border-border bg-background">
          <Document
            onContentChange={handleContentChange}
            content={currentDocumentContent}
            documentId={currentDocumentId}
            versionNumber={selectedVersionNumber}
            onInlineSuggestionRequest={requestInlineSuggestion}
            pendingSuggestion={pendingSuggestion}
            onAcceptSuggestion={acceptInlineSuggestion}
            onRejectSuggestion={rejectInlineSuggestion}
            activePanelSuggestion={activePanelSuggestion}
            onDismissPanelSuggestion={handleDismissPanelSuggestion}
            onOnlineUsersChange={handleOnlineUsersChange}
          />
        </div>

        {/* AI Analysis - Right 40% */}
        <div className="w-2/5 h-full flex flex-col bg-muted/10">
          <SuggestionsPanel
            currentDocumentId={currentDocumentId}
            selectedVersionNumber={selectedVersionNumber}
            isConnected={isConnected}
            isAnalyzing={isAnalyzing}
            analysisResult={analysisResult}
            currentPhase={currentPhase}
            streamUpdates={streamUpdates}
            onShowSuggestionLocation={handleShowSuggestionLocation}
            activeSuggestion={activePanelSuggestion?.issue || null}
          />
        </div>
      </div>

      {/* Grounded Chatbot - Floating */}
      <ChatPanel
        documentId={currentDocumentId}
        clientId={`client_${currentDocumentId}`}
        documentContent={currentDocumentContent}
        analysisResult={analysisResult}
      />
    </div>
  );
}

export default App;
