import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import './index.css'
import './App.css'
import { router } from './router.tsx'

// Intercept console.log and send to backend
const originalLog = console.log;
console.log = (...args: any[]) => {
  originalLog(...args);
  // Send to backend for logging
  const message = args.map(arg =>
    typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
  ).join(' ');

  fetch('http://127.0.0.1:8001/api/debug/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, timestamp: new Date().toISOString() }),
  }).catch(() => {}); // Ignore errors
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
