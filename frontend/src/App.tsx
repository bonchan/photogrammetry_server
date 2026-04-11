// src/App.tsx
import Workspace from '@/components/workspace/Workspace';
import DetailPanel from '@/components/layout/DetailPanel';
import './App.css';

function App() {

  return (
    <div className="app-container">
      <Workspace />
      <DetailPanel />
    </div>
  );
}

export default App;