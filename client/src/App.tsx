import { useEffect, useState, useCallback } from "react";
import axios from "axios";
import Document from "./Document";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";
import SuggestionsPanel from "./components/SuggestionsPanel";
import { useSocket } from "./hooks/useSocket";
import { PatentIssue, PanelSuggestion } from "./types/PatentTypes";

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

function App() {
  // Stateless frontend state management
  const [currentDocumentContent, setCurrentDocumentContent] = useState<string>("");
  const [currentDocumentId, setCurrentDocumentId] = useState<number>(0);
  const [currentDocumentInfo, setCurrentDocumentInfo] = useState<DocumentInfo | null>(null);
  const [selectedVersionNumber, setSelectedVersionNumber] = useState<number>(1);
  const [availableVersions, setAvailableVersions] = useState<DocumentVersion[]>([]);
  const [isDirty, setIsDirty] = useState<boolean>(false);  // Has content been modified?
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Panel suggestion state - simplified to just show location
  const [activePanelSuggestion, setActivePanelSuggestion] = useState<PanelSuggestion | null>(null);
  
  // Online users state
  const [onlineUsersCount, setOnlineUsersCount] = useState<number>(0);
  const [onlineUsers, setOnlineUsers] = useState<CollaborationUser[]>([]);
  const [currentUser, setCurrentUser] = useState<CollaborationUser | null>(null);

  // WebSocket integration for AI suggestions with multi-agent streaming
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
    clearPendingSuggestion
  } = useSocket();

  // Load the first patent on mount
  useEffect(() => {
    loadPatent(1);
  }, []);

  // Clear pending inline suggestions when document version changes (not on every edit!)
  useEffect(() => {
    clearPendingSuggestion();
  }, [selectedVersionNumber, currentDocumentId, clearPendingSuggestion]);

  const loadPatent = async (documentNumber: number) => {
    setIsLoading(true);
    try {
      // Load document metadata (stateless - no content in document)
      const docResponse = await axios.get(
        `${BACKEND_URL}/document/${documentNumber}`
      );

      // Load all versions
      const versionsResponse = await axios.get(
        `${BACKEND_URL}/document/${documentNumber}/versions`
      );

      const versions = versionsResponse.data.versions;
      setCurrentDocumentId(documentNumber);
      setCurrentDocumentInfo(docResponse.data);
      setAvailableVersions(versions);

      // Load the latest version as the starting content
      if (versions.length > 0) {
        const latestVersion = versions[versions.length - 1];
        setCurrentDocumentContent(latestVersion.content);
        setSelectedVersionNumber(latestVersion.version_number);
      }

      setIsDirty(false);
    } catch (error) {
      console.error("Error loading document:", error);
    }
    setIsLoading(false);
  };

  // Update current version with new content
  const saveCurrentVersion = async () => {
    if (!isDirty) return; // Nothing to save

    setIsLoading(true);
    try {
      const currentVersion = availableVersions.find(v => v.version_number === selectedVersionNumber);
      await axios.put(`${BACKEND_URL}/document/${currentDocumentId}/versions/${selectedVersionNumber}`, {
        content: currentDocumentContent,
        name: currentVersion?.name || `Version ${selectedVersionNumber}`
      });

      // Update the local state to reflect the saved content
      setAvailableVersions(prev =>
        prev.map(version =>
          version.version_number === selectedVersionNumber
            ? { ...version, content: currentDocumentContent }
            : version
        )
      );

      setIsDirty(false);
    } catch (error) {
      console.error("Error saving version:", error);
    }
    setIsLoading(false);
  };

  // Create a new version from current content
  const createNewVersion = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${BACKEND_URL}/document/${currentDocumentId}/versions`, {
        content: currentDocumentContent,
        name: `Version ${availableVersions.length + 1}`
      });
      const newVersion = response.data;

      // Update the available versions list and switch to new version
      setAvailableVersions(prev => [...prev, newVersion]);
      setSelectedVersionNumber(newVersion.version_number);
      setIsDirty(false);
    } catch (error) {
      console.error("Error creating new version:", error);
    }
    setIsLoading(false);
  };

  // Switch to a different version (Google Docs style)
  const switchToVersion = async (versionNumber: number) => {
    if (versionNumber === selectedVersionNumber) return; // No change needed

    // Warn if there are unsaved changes
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

  // Handle content changes (mark as dirty)
  const handleContentChange = (content: string) => {
    setCurrentDocumentContent(content);
    setIsDirty(true);
  };

  // Handle AI suggestion requests from Document component
  const handleRequestSuggestions = (content: string) => {
    if (isConnected) {
      requestAISuggestions(content);
    }
  };

  const handleShowSuggestionLocation = (issue: PatentIssue) => {
    // Simply pass the issue to the editor to highlight the location
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
    <div className="flex flex-col h-full w-full">
      {isLoading && <LoadingOverlay />}
      <header className="flex items-center justify-center top-0 w-full bg-black text-white text-center z-50 mb-[30px] h-[80px]">
        <img src={Logo} alt="Logo" style={{ height: "50px" }} />
      </header>
      <div className="flex w-full bg-white h-[calc(100%-100px)] gap-4 justify-center">
        {/* Left Sidebar - Document Selection & Controls */}
        <div className="flex flex-col h-full items-center gap-4 px-4 w-48 bg-gray-50 border-r">
          <div className="w-full space-y-2">
            <button 
              onClick={() => loadPatent(1)}
              className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
            >
              Patent 1
            </button>
            <button 
              onClick={() => loadPatent(2)}
              className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
            >
              Patent 2
            </button>
          </div>

          {/* Version Control */}
          <div className="w-full space-y-2">
            <button
              onClick={saveCurrentVersion}
              disabled={!isDirty || isLoading}
              className={`w-full px-4 py-2 rounded text-sm ${
                isDirty && !isLoading
                  ? "bg-green-500 hover:bg-green-600 text-white"
                  : "bg-gray-300 text-gray-500 cursor-not-allowed"
              }`}
            >
              {isDirty ? `Save v${selectedVersionNumber}` : `Saved`}
            </button>
            <button
              onClick={createNewVersion}
              disabled={isLoading}
              className="w-full px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:bg-gray-300 disabled:text-gray-500 text-sm"
            >
              New Version
            </button>
            {availableVersions.length > 1 && (
              <div className="text-xs text-gray-500 text-center">
                {availableVersions.length} versions available
              </div>
            )}
          </div>

          {/* AI Analysis Button - Professional */}
          <button
            onClick={() => handleRequestSuggestions(currentDocumentContent)}
            disabled={!isConnected || isLoading}
            className="w-full px-4 py-3 bg-slate-800 text-white rounded border hover:bg-slate-700 disabled:bg-gray-300 disabled:text-gray-500 text-sm font-medium transition-colors"
          >
            AI Document Analysis
          </button>

          {/* Connection Status */}
          <div className="flex items-center gap-2 text-sm">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-gray-600 font-medium">
              {isConnected ? 'AI Connected' : 'AI Offline'}
            </span>
          </div>
        </div>

        {/* Main Content Area - AI Analysis Takes Center Stage */}
        <div className="flex-1 flex flex-col h-full">
          {/* Top Header Bar */}
          <div className="flex items-center justify-between p-4 bg-white border-b border-gray-200">
            <div className="flex items-center gap-4">
              <h2 className="text-[#213547] text-xl font-bold">
                {currentDocumentInfo?.title || `Patent ${currentDocumentId}`}
                {isDirty && <span className="text-red-500 ml-2">*</span>}
              </h2>
              {availableVersions.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600 font-medium">Version:</span>
                  <select
                    value={selectedVersionNumber}
                    onChange={(e) => switchToVersion(Number(e.target.value))}
                    className="border border-gray-300 rounded px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    {availableVersions.map(version => (
                      <option key={version.version_number} value={version.version_number}>
                        {version.name || `v${version.version_number}`}
                      </option>
                    ))}
                  </select>
                  {isDirty && (
                    <span className="text-xs text-red-500 ml-2 font-medium">
                      (unsaved changes)
                    </span>
                  )}
                </div>
              )}
              
              {/* Online Users Indicator */}
              {(onlineUsersCount > 0 || currentUser) && (
                <div className="flex items-center gap-2 bg-white rounded-full px-3 py-1 shadow-sm border border-gray-200">
                  <div className="flex -space-x-2">
                    {/* Show current user first */}
                    {currentUser && (
                      <div
                        className="w-7 h-7 rounded-full border-2 border-white flex items-center justify-center text-white text-xs font-bold"
                        style={{ backgroundColor: currentUser.color }}
                        title={`${currentUser.name} (You)`}
                      >
                        {currentUser.name?.charAt(0).toUpperCase()}
                      </div>
                    )}
                    {/* Show other users */}
                    {onlineUsers.map((user, index) => (
                      <div
                        key={index}
                        className="w-7 h-7 rounded-full border-2 border-white flex items-center justify-center text-white text-xs font-bold"
                        style={{ backgroundColor: user.color }}
                        title={user.name}
                      >
                        {user.name?.charAt(0).toUpperCase()}
                      </div>
                    ))}
                  </div>
                  <span className="text-xs text-gray-600 font-medium">
                    {onlineUsersCount + 1} online
                  </span>
                </div>
              )}
            </div>
            
            {/* Large Prominent AI Analysis Button */}
            <button
              onClick={() => handleRequestSuggestions(currentDocumentContent)}
              disabled={!isConnected || isLoading}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 text-base font-semibold shadow-lg transition-all"
            >
              {isAnalyzing ? 'Analyzing...' : 'Run AI Analysis'}
            </button>
          </div>

          {/* Split Layout: Document + AI Analysis */}
          <div className="flex-1 flex overflow-hidden">
            {/* Document Editor - Left 60% */}
            <div className="w-3/5 h-full border-r border-gray-200">
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

            {/* AI Analysis - Right 40% - Fixed scrolling */}
            <div className="w-2/5 h-full flex flex-col">
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
        </div>
      </div>
    </div>
  );
}

export default App;
