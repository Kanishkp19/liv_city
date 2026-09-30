import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import AppShell from './components/AppShell'
import LiveCity from './pages/LiveCity'
import AgentInspector from './pages/AgentInspector'
import Economy from './pages/Economy'
import Jobs from './pages/Jobs'
import Replay from './pages/Replay'
import SystemHealth from './pages/SystemHealth'

const queryClient = new QueryClient()

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <LiveCity /> },
      { path: '/agents/:id', element: <AgentInspector /> },
      { path: '/jobs', element: <Jobs /> },
      { path: '/economy', element: <Economy /> },
      { path: '/replay/:worldId?', element: <Replay /> },
      { path: '/system', element: <SystemHealth /> },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
)
