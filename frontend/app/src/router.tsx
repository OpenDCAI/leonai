import { createBrowserRouter } from 'react-router-dom';
import AppLayout from './pages/AppLayout';
import ChatPage from './pages/ChatPage';
import NewChatPage from './pages/NewChatPage';

export const router = createBrowserRouter([
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
]);
