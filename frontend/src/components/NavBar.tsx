import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function NavBar() {
  const { logout } = useAuth();
  const location = useLocation();

  function linkStyle(path: string): React.CSSProperties {
    const active = location.pathname === path;
    return {
      color: active ? "#e6edf3" : "#8b98a5",
      fontWeight: active ? 700 : 500,
      borderBottomColor: active ? "#4a90ff" : "transparent",
      marginRight: 24,
    };
  }

  return (
    <div className="top-nav">
      <div className="top-nav-brand">
        <h1>🔒 MigrationProof</h1>
        <nav>
          <Link to="/project" className="nav-link" style={linkStyle("/project")}>
            Project
          </Link>
          <Link to="/about" className="nav-link" style={linkStyle("/about")}>
            How to use / About
          </Link>
        </nav>
      </div>
      <button className="secondary" onClick={logout}>
        Sign out
      </button>
    </div>
  );
}
