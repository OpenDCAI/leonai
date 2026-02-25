import { createBrowserRouter, Navigate } from 'react-router-dom';
import RootLayout from './pages/RootLayout';
import AppLayout from './pages/AppLayout';
import ChatPage from './pages/ChatPage';
import NewChatPage from './pages/NewChatPage';
import SettingsPage from './pages/SettingsPage';
import StaffPage from './pages/StaffPage';
import AgentDetailPage from './pages/AgentDetailPage';
import TasksPage from './pages/TasksPage';
import LibraryPage from './pages/LibraryPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/staff" replace />,
  },
  {
    path: '/',
    element: <RootLayout />,
    children: [
      {
        path: 'chat',
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
        path: 'staff',
        element: <StaffPage />,
      },
      {
        path: 'staff/:id',
        element: <AgentDetailPage />,
      },
      {
        path: 'tasks',
        element: <TasksPage />,
      },
      {
        path: 'library',
        element: <LibraryPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },
]);
