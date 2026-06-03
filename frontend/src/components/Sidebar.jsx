import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard, Users, CalendarDays, Clock, DollarSign,
  Target, Package, LogOut, ChevronRight, Settings, Bell
} from "lucide-react";

const NAV = [
  { to: "/",            icon: LayoutDashboard, label: "Tableau de bord" },
  { to: "/employees",   icon: Users,            label: "Employés" },
  { to: "/leave",       icon: CalendarDays,     label: "Congés" },
  { to: "/attendance",  icon: Clock,            label: "Présences" },
  { to: "/payroll",     icon: DollarSign,       label: "Paie" },
  { to: "/pms",         icon: Target,           label: "Performance" },
  { to: "/assets",      icon: Package,          label: "Actifs" },
];

export default function Sidebar({ collapsed, setCollapsed }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside
      className={`flex flex-col bg-sidebar-bg text-white transition-all duration-300 ${
        collapsed ? "w-[72px]" : "w-[240px]"
      } min-h-screen flex-shrink-0`}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/10">
        <div className="w-9 h-9 border-2 border-brand-orange rounded flex items-center justify-center font-black text-brand-orange flex-shrink-0">
          M
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <div className="font-bold text-sm leading-tight">M·AUTOMOTIV</div>
            <div className="text-white/40 text-xs">FlowRH</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-1 px-2">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group
              ${isActive
                ? "bg-brand-orange text-white shadow-brand"
                : "text-white/60 hover:text-white hover:bg-white/10"
              }`
            }
          >
            <Icon size={18} className="flex-shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
            {!collapsed && (
              <ChevronRight size={14} className="ml-auto opacity-0 group-hover:opacity-40 transition-opacity" />
            )}
          </NavLink>
        ))}
      </nav>

      {/* User + settings */}
      <div className="border-t border-white/10 px-2 py-3 space-y-1">
        <NavLink
          to="/settings"
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-white/60 hover:text-white hover:bg-white/10 transition-all"
        >
          <Settings size={18} className="flex-shrink-0" />
          {!collapsed && <span>Paramètres</span>}
        </NavLink>

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-white/60 hover:text-red-400 hover:bg-red-500/10 transition-all"
        >
          <LogOut size={18} className="flex-shrink-0" />
          {!collapsed && <span>Déconnexion</span>}
        </button>

        {/* User avatar */}
        {!collapsed && user && (
          <div className="flex items-center gap-3 px-3 py-3 mt-2 rounded-xl bg-white/5">
            <div className="w-8 h-8 rounded-full bg-brand-gradient flex items-center justify-center text-white font-bold text-xs flex-shrink-0">
              {(user.first_name?.[0] || user.username?.[0] || "U").toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <div className="text-xs font-semibold text-white truncate">
                {user.first_name || user.username}
              </div>
              <div className="text-xs text-white/40 truncate">{user.email}</div>
            </div>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(v => !v)}
        className="absolute top-1/2 -right-3 w-6 h-6 bg-brand-orange rounded-full flex items-center justify-center shadow-brand hover:opacity-90 transition-opacity z-10"
        style={{ transform: "translateY(-50%)" }}
      >
        <ChevronRight size={12} className={`text-white transition-transform ${collapsed ? "" : "rotate-180"}`} />
      </button>
    </aside>
  );
}
