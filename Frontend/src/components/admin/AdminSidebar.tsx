import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Activity,
  Server,
  MessageSquare,
  Users,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import SidebarLink from "./SidebarLink";
import { Button } from "@/components/ui/button";

interface AdminSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { to: "/admin/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/admin/metrics", icon: Activity, label: "Métriques" },
  { to: "/admin/api-requests", icon: Server, label: "Requêtes API" },
  { to: "/admin/answer-quality", icon: MessageSquare, label: "Qualité" },
  { to: "/admin/users", icon: Users, label: "Utilisateurs" },
  { to: "/admin/settings", icon: Settings, label: "Paramètres" },
];

const AdminSidebar = ({ collapsed, onToggle }: AdminSidebarProps) => {
  const { logout, user } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-screen bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-300 z-50",
        collapsed ? "w-[72px]" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 p-4 border-b border-sidebar-border h-16">
        <div className="w-9 h-9 rounded-lg bg-foreground flex items-center justify-center shrink-0 overflow-hidden">
          <img 
            src="/logo_RAG_System.png" 
            alt="RAG System Logo" 
            className="w-full h-full object-contain p-1"
          />
        </div>
        {!collapsed && (
          <div className="flex flex-col overflow-hidden">
            <span className="font-oswald text-lg font-medium tracking-tight truncate">
              RAG<span className="text-primary">SYSTEM</span>
            </span>
            <span className="text-[0.6rem] font-space uppercase tracking-widest text-muted-foreground">
              Admin Panel
            </span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <SidebarLink
            key={item.to}
            to={item.to}
            icon={item.icon}
            label={item.label}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {/* User section */}
      <div className="p-3 border-t border-sidebar-border">
        {!collapsed && user && (
          <div className="flex items-center gap-3 px-3 py-2 mb-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-sm font-medium text-primary">
                {user.name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          className={cn(
            "w-full justify-start text-muted-foreground hover:text-destructive hover:bg-destructive/10",
            collapsed && "px-3"
          )}
          onClick={handleLogout}
        >
          <LogOut className="w-5 h-5 shrink-0" />
          {!collapsed && <span className="ml-3">Déconnexion</span>}
        </Button>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-card border border-border flex items-center justify-center hover:bg-accent transition-colors shadow-xs"
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3" />
        ) : (
          <ChevronLeft className="w-3 h-3" />
        )}
      </button>
    </aside>
  );
};

export default AdminSidebar;
