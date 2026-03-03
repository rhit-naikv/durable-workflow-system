import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { DashboardPage } from './pages/DashboardPage';
import { SubmitPage } from './pages/SubmitPage';
import { RunDetailPage } from './pages/RunDetailPage';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="navbar">
          <div className="navbar__brand">
            <span className="navbar__logo">⬡</span>
            <span className="navbar__title">Workflow Engine</span>
          </div>
          <div className="navbar__links">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link nav-link--active' : 'nav-link'}>
              Dashboard
            </NavLink>
            <NavLink to="/submit" className={({ isActive }) => isActive ? 'nav-link nav-link--active' : 'nav-link'}>
              Submit Pipeline
            </NavLink>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/submit" element={<SubmitPage />} />
            <Route path="/runs/:id" element={<RunDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
