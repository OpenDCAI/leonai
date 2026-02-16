import { createBrowserRouter, Navigate } from 'react-router-dom';
import AppLayout from './pages/AppLayout';
import ChatPage from './pages/ChatPage';
import NewChatPage from './pages/NewChatPage';
import SettingsPage from './pages/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/app" replace />,
  },
  {
    path: '/app',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <NewChatPage />,
      },
      {
        path: ':threadId',
        element: <ChatPage />,
      },
    ],
  },
  {
    path: '/settings',
    element: <SettingsPage />,
  },
]);
