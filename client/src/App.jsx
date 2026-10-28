import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import { EmptyState, Loading } from './components/ui.jsx';
import Home from './pages/Home.jsx';

// Chart-heavy pages load on demand so the landing page stays fast.
const Planner = lazy(() => import('./pages/Planner.jsx'));
const Dashboard = lazy(() => import('./pages/Dashboard.jsx'));
const Delays = lazy(() => import('./pages/Delays.jsx'));
const Stations = lazy(() => import('./pages/Stations.jsx'));
const Forecast = lazy(() => import('./pages/Forecast.jsx'));
const Pipeline = lazy(() => import('./pages/Pipeline.jsx'));
const LabOutputs = lazy(() => import('./pages/LabOutputs.jsx'));
const About = lazy(() => import('./pages/About.jsx'));

export default function App() {
  return (
    <Layout>
      <Suspense fallback={<div className="mt-32"><Loading rows={3} /></div>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/plan" element={<Planner />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/delays" element={<Delays />} />
          <Route path="/stations" element={<Stations />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/lab-outputs" element={<LabOutputs />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<div className="mt-32"><EmptyState title="Page not found">That page does not exist. Use the menu above.</EmptyState></div>} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
