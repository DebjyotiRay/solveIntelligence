// Configuration for API and WebSocket endpoints
const config = {
  // Backend API URL
  BACKEND_URL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000',
  
  // WebSocket URL - defaults to localhost for development
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
};

export default config;
