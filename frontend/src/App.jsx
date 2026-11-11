import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");

  useEffect(() => {
    let active = true;

    fetch(`${API_URL}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error("Health check failed");
        if (active) setBackendStatus("connected");
      })
      .catch(() => {
        if (active) setBackendStatus("disconnected");
      });

    return () => { active = false; };
  }, []);

  return (
    <main className="page-shell">
      <nav className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">S</span>
          <span>SellerPulse<span className="brand-accent"> AI</span></span>
        </a>
        <span className="prototype-label">EARLY PROTOTYPE</span>
      </nav>

      <section className="hero">
        <div className="eyebrow"><span className="eyebrow-dot" /> YOUR VIRTUAL KEY ACCOUNT MANAGER</div>
        <h1>Understand your business.<br /><span>Find your next move.</span></h1>
        <p className="hero-copy">
          A voice-first business companion that helps marketplace sellers
          understand performance changes and decide what to do next.
        </p>

        <div className="setup-card">
          <div className="setup-card-heading">
            <div>
              <p className="card-kicker">DEVELOPMENT STATUS</p>
              <h2>Project foundation</h2>
            </div>
            <span className={`status-pill ${backendStatus}`}>
              <span className="status-dot" />
              {backendStatus === "checking" ? "Checking backend" :
               backendStatus === "connected" ? "Backend connected" : "Backend unavailable"}
            </span>
          </div>
          <p className="setup-description">
            The frontend and backend are running. Seller data, agent orchestration
            and voice capabilities will be added in upcoming milestones.
          </p>
          <div className="milestone-row"><span className="milestone-check">✓</span>React frontend initialised</div>
          <div className="milestone-row"><span className="milestone-check">✓</span>FastAPI backend initialised</div>
          <div className="milestone-row pending"><span className="milestone-pending" />Agentic KAM workflow — upcoming</div>
        </div>
      </section>

      <footer className="footer">
        <span>SellerPulse AI</span>
        <span>Built for the Snapdeal AI First assignment</span>
      </footer>
    </main>
  );
}
