import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import logo from '../assets/logo.svg';

const LINKS = [
  { to: '/plan', label: 'Plan journey', cta: true },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/delays', label: 'Delays' },
  { to: '/stations', label: 'Stations' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/pipeline', label: 'Data Pipeline' },
  { to: '/lab-outputs', label: 'Lab Outputs' },
  { to: '/about', label: 'About' },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => {
    setOpen(false);
  }, [pathname]);
  return (
    <nav className="navbar" aria-label="Main">
      <Link to="/" className="brand">
        <img src={logo} alt="" />
        <span>RailPulse</span>
      </Link>
      <button type="button" className="nav-toggle" aria-label="Menu" aria-expanded={open} aria-controls="nav-links" onClick={() => setOpen((o) => !o)}>
        <span />
      </button>
      <ul id="nav-links" className={`nav-links${open ? ' open' : ''}`}>
        {LINKS.map((l) => (
          <li key={l.to}>
            <NavLink to={l.to} className={({ isActive }) => [isActive ? 'active' : '', l.cta ? 'nav-cta' : ''].join(' ').trim()}>
              {l.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div>
        <strong>RailPulse</strong> · Indian Railways Train Delay Analysis &amp; Forecasting · Academic DAV mini-project
      </div>
      <div>Data is simulated for academic purposes</div>
    </footer>
  );
}

export default function Layout({ children }) {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return (
    <div className="page">
      <a href="#main" className="skip-link">Skip to content</a>
      <div className="sheet">
        <Navbar />
        <main id="main">{children}</main>
        <Footer />
      </div>
    </div>
  );
}
