// Real-Time Recommendation System - Main Application Component
/**
 * React application entry point with routing and global providers.
 *
 * This component sets up:
 * - React Router for navigation
 * - TanStack Query for data fetching
 * - Global layout with navigation
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import RecommendationsPage from './pages/RecommendationsPage';
import DashboardPage from './pages/DashboardPage';
import ABTestingPage from './pages/ABTestingPage';
import MonitoringPage from './pages/MonitoringPage';
import HealthPage from './pages/HealthPage';

// Create query client with default options
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      refetchInterval: 60000, // Refresh every minute
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

// Navigation component
const Navigation: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string): string => {
    return location.pathname === path ? 'nav-link active' : 'nav-link';
  };

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <h1>Recommendation System</h1>
      </div>
      <div className="nav-links">
        <Link to="/" className={isActive('/')}>
          Recommendations
        </Link>
        <Link to="/dashboard" className={isActive('/dashboard')}>
          📊 Dashboard
        </Link>
        <Link to="/ab-testing" className={isActive('/ab-testing')}>
          🧪 A/B Testing
        </Link>
        <Link to="/monitoring" className={isActive('/monitoring')}>
          Monitoring
        </Link>
        <Link to="/health" className={isActive('/health')}>
          Health
        </Link>
      </div>
    </nav>
  );
};

// Main App component
const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <div className="app">
          <Navigation />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<RecommendationsPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/ab-testing" element={<ABTestingPage />} />
              <Route path="/monitoring" element={<MonitoringPage />} />
              <Route path="/health" element={<HealthPage />} />
            </Routes>
          </main>
          <footer className="app-footer">
            <p>Real-Time Recommendation System v1.0.0</p>
          </footer>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
