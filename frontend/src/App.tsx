import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom';
import Layout from './components/Layout';
import ImageGen from './pages/ImageGen';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import ApiProxy from './pages/ApiProxy';
import Settings from './pages/Settings';
import Statistics from './pages/Statistics';
import Login from './pages/Login';
import { useAuthStore } from './stores/useAuthStore';
import './App.css';

// Auth Guard Component
function AuthGuard() {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: <AuthGuard />,
    children: [
      {
        element: <Layout />,
        children: [
          {
            index: true,
            element: <Dashboard />,
          },
          {
            path: 'accounts',
            element: <Accounts />,
          },
          {
            path: 'proxy',
            element: <ApiProxy />,
          },
          {
            path: 'image-gen',
            element: <ImageGen />,
          },
          {
            path: 'settings',
            element: <Settings />,
          },
          {
            path: 'statistics',
            element: <Statistics />,
          },
        ],
      },
    ],
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;

