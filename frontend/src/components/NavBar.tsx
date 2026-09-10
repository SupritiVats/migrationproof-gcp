import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function NavBar() {
  const { logout } = useAuth();
  const location = useLocation();

  function linkStyle(path: string): React.CSSProperties {
    return {
      color: location.pathname === path ? "#e6edf3" : "#8b98a5",
      fontWeight: location.pathname === path ? 700 : 500,
      textDecoration: "none",
      marginRight: 20,
    };
  }

  return (
    <div className="top-nav">
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>🔒 MigrationProof</h1>
        <nav>
          <Link to="/project" style={linkStyle("/project")}>
            Project
          </Link>
          <Link to="/about" style={linkStyle("/about")}>
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
