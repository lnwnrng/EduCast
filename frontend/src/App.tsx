import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/Layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import UploadPage from './pages/Upload';
import ScriptEditor from './pages/ScriptEditor';
import Workspace from './pages/Workspace';
import Preview from './pages/Preview';
import Resources from './pages/Resources';
import Monitoring from './pages/Monitoring';

const App: React.FC = () => {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<Workspace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/projects/:id/upload" element={<UploadPage />} />
        <Route path="/script" element={<ScriptEditor />} />
        <Route path="/projects/:id/script" element={<ScriptEditor />} />
        {/* 旧「视频生成」页已并入项目工作台，保留旧链接重定向 */}
        <Route path="/generate" element={<Navigate to="/projects" replace />} />
        <Route
          path="/projects/:id/generate"
          element={<Navigate to=".." relative="path" replace />}
        />
        <Route path="/preview" element={<Preview />} />
        <Route path="/projects/:id/preview" element={<Preview />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/monitoring" element={<Monitoring />} />
      </Route>
    </Routes>
  );
};

export default App;
