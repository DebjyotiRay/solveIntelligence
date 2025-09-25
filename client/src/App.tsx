import Document from "./Document";
import { useEffect, useState } from "react";
import axios from "axios";
import LoadingOverlay from "./internal/LoadingOverlay";
import Logo from "./assets/logo.png";
import { useMutation, useQuery } from "@tanstack/react-query";


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

function App() {
  // Stateless frontend state management
  const [currentDocumentContent, setCurrentDocumentContent] = useState<string>("");
  const [currentDocumentId, setCurrentDocumentId] = useState<number>(0);
  const [currentDocumentInfo, setCurrentDocumentInfo] = useState<DocumentInfo | null>(null);
  const [selectedVersionNumber, setSelectedVersionNumber] = useState<number>(1);
  const [availableVersions, setAvailableVersions] = useState<DocumentVersion[]>([]);
  const [isDirty, setIsDirty] = useState<boolean>(false);  // Has content been modified?
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Load the first patent on mount
  useEffect(() => {
    loadPatent(1);
  }, []);

  // Load a document with stateless architecture
  const loadPatent = async (documentNumber: number) => {
    setIsLoading(true);
    console.log("Loading patent:", documentNumber);
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
      console.log(`Saved to version ${selectedVersionNumber}`);
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
      console.log(`Created version ${newVersion.version_number}`);
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
      console.log(`Switched to version ${versionNumber}`);
    }
  };

  // Handle content changes (mark as dirty)
  const handleContentChange = (content: string) => {
    setCurrentDocumentContent(content);
    setIsDirty(true);
  };

  return (
    <div className="flex flex-col h-full w-full">
      {isLoading && <LoadingOverlay />}
      <header className="flex items-center justify-center top-0 w-full bg-black text-white text-center z-50 mb-[30px] h-[80px]">
        <img src={Logo} alt="Logo" style={{ height: "50px" }} />
      </header>
      <div className="flex w-full bg-white h=[calc(100%-100px) gap-4 justify-center box-shadow">
        <div className="flex flex-col h-full items-center gap-2 px-4">
          <button onClick={() => loadPatent(1)}>Patent 1</button>
          <button onClick={() => loadPatent(2)}>Patent 2</button>
        </div>
        <div className="flex flex-col h-full items-center gap-2 px-4 flex-1">
          <div className="self-start flex items-center gap-4">
            <h2 className="text-[#213547] opacity-60 text-2xl font-semibold">
              {currentDocumentInfo?.title || `Patent ${currentDocumentId}`}
              {isDirty && <span className="text-red-500 ml-2">*</span>}
            </h2>
            {availableVersions.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Version:</span>
                <select
                  value={selectedVersionNumber}
                  onChange={(e) => switchToVersion(Number(e.target.value))}
                  className="border rounded px-2 py-1 text-sm"
                >
                  {availableVersions.map(version => (
                    <option key={version.version_number} value={version.version_number}>
                      {version.name || `v${version.version_number}`}
                    </option>
                  ))}
                </select>
                {isDirty && (
                  <span className="text-xs text-red-500 ml-2">
                    (unsaved changes)
                  </span>
                )}
              </div>
            )}
          </div>
          <Document
            onContentChange={handleContentChange}
            content={currentDocumentContent}
          />
        </div>
        <div className="flex flex-col h-full items-center gap-2 px-4">
          <button
            onClick={saveCurrentVersion}
            disabled={!isDirty || isLoading}
            className={`px-4 py-2 rounded ${
              isDirty && !isLoading
                ? "bg-blue-500 hover:bg-blue-600 text-white"
                : "bg-gray-300 text-gray-500 cursor-not-allowed"
            }`}
          >
            {isDirty ? `Save v${selectedVersionNumber}` : `Saved`}
          </button>
          <button
            onClick={createNewVersion}
            disabled={isLoading}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-300 disabled:text-gray-500"
          >
            New Version
          </button>
          {availableVersions.length > 1 && (
            <div className="text-xs text-gray-500 mt-2 text-center">
              {availableVersions.length} versions available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
