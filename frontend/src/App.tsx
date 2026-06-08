import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/Layout/AppLayout';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import UploadPage from './pages/Upload';
import ScriptEditor from './pages/ScriptEditor';
import Workspace from './pages/Workspace';
import Preview from './pages/Preview';
import Resources from './pages/Resources';
import Monitoring from './pages/Monitoring';
import AdminUserManagement from './pages/Admin/UserManagement';
import AdminAuditLog from './pages/Admin/AuditLog';
import ProtectedRoute from './components/Auth/ProtectedRoute';

const App: React.FC = () => {
  return (
    <Routes>
      {/* 登录/注册页面（全屏，无侧边栏） */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        {/* 工作台：侧边栏直达（无 id 时用记忆的当前项目或显示选择器） */}
        <Route path="/workspace" element={<Workspace />} />
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

        {/* 管理员页面 */}
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requireAdmin>
              <AdminUserManagement />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/logs"
          element={
            <ProtectedRoute requireAdmin>
              <AdminAuditLog />
            </ProtectedRoute>
          }
        />
      </Route>
    </Routes>
  );
};

export default App;
