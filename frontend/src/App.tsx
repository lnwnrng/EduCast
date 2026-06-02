import React from 'react';
import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/Layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import UploadPage from './pages/Upload';
import ScriptEditor from './pages/ScriptEditor';
import GeneratePage from './pages/Generate';
import Preview from './pages/Preview';
import Resources from './pages/Resources';

const App: React.FC = () => {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/projects/:id/upload" element={<UploadPage />} />
        <Route path="/script" element={<ScriptEditor />} />
        <Route path="/projects/:id/script" element={<ScriptEditor />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/projects/:id/generate" element={<GeneratePage />} />
        <Route path="/preview" element={<Preview />} />
        <Route path="/projects/:id/preview" element={<Preview />} />
        <Route path="/resources" element={<Resources />} />
      </Route>
    </Routes>
  );
};

export default App;
