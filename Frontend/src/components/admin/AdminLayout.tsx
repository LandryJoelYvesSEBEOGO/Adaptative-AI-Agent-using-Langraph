import { useState } from "react";
import { Outlet } from "react-router-dom";
import AdminSidebar from "./AdminSidebar";
import ThemeToggle from "../ThemeToggle";
import { cn } from "@/lib/utils";

const AdminLayout = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background relative">
      <div className="absolute inset-0 pointer-events-none noise-overlay" />
      <div className="absolute top-0 right-0 w-[50rem] h-[50rem] bg-linear-to-b from-primary/10 to-transparent opacity-50 dark:opacity-30 blur-3xl pointer-events-none rounded-full translate-x-1/3 -translate-y-1/3" />
      
      <AdminSidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <main
        className={cn(
          "min-h-screen transition-all duration-300 relative z-10",
          sidebarCollapsed ? "ml-[72px]" : "ml-64"
        )}
      >
        {/* Header with theme toggle */}
        <header className="sticky top-0 z-20 flex items-center justify-between px-6 md:px-10 py-4 border-b border-border bg-background/80 backdrop-blur-xl">
          <div className="flex-1" />
          <ThemeToggle variant="compact" />
        </header>
        <div className="p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;
