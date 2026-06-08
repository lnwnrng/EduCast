import React, { useEffect } from 'react';
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
import CategoryManagement from './pages/Admin/CategoryManagement';
import TagManagement from './pages/Admin/TagManagement';
import Requests from './pages/Admin/Requests';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import { useAuthStore } from './stores/authStore';

const App: React.FC = () => {
  const fetchMe = useAuthStore((s) => s.fetchMe);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* 受保护的主要页面 */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/projects/:id" element={<Workspace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/projects/:id/upload" element={<UploadPage />} />
        <Route path="/script" element={<ScriptEditor />} />
        <Route path="/projects/:id/script" element={<ScriptEditor />} />
        <Route path="/generate" element={<Navigate to="/projects" replace />} />
        <Route path="/projects/:id/generate" element={<Navigate to=".." relative="path" replace />} />
        <Route path="/preview" element={<Preview />} />
        <Route path="/projects/:id/preview" element={<Preview />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/monitoring" element={<Monitoring />} />
      </Route>

      {/* Admin 路由 */}
      <Route
        element={
          <ProtectedRoute requireAdmin>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/admin/users" element={<AdminUserManagement />} />
        <Route path="/admin/logs" element={<AdminAuditLog />} />
        <Route path="/admin/categories" element={<CategoryManagement />} />
        <Route path="/admin/tags" element={<TagManagement />} />
        <Route path="/admin/requests" element={<Requests />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;