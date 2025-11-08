import ReactDOM from 'react-dom/client';
import Root from './Root.tsx';
import './index.css';

// StrictMode disabled to prevent double-mounting which breaks Yjs collaboration
ReactDOM.createRoot(document.getElementById('root')!).render(
  // <React.StrictMode>
    <Root />
  // </React.StrictMode>,
);
