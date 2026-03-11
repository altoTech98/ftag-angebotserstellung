"use client";

import { useState, useEffect, createContext, useContext } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderOpen,
  PlusCircle,
  BookOpen,
  Settings,
  ChevronsLeft,
  ChevronsRight,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Context for sharing mobile sidebar state between Sidebar and Header
interface SidebarContextValue {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
}

const SidebarContext = createContext<SidebarContextValue>({
  mobileOpen: false,
  setMobileOpen: () => {},
});

export function useSidebarMobile() {
  return useContext(SidebarContext);
}

interface SidebarProviderProps {
  children: React.ReactNode;
}

export function SidebarProvider({ children }: SidebarProviderProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <SidebarContext.Provider value={{ mobileOpen, setMobileOpen }}>
      {children}
    </SidebarContext.Provider>
  );
}

interface SidebarProps {
  user: {
    name: string;
    email: string;
    role: string;
  };
}

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Projekte", href: "/projekte", icon: FolderOpen },
  { label: "Neue Analyse", href: "/neue-analyse", icon: PlusCircle },
  { label: "Katalog", href: "/katalog", icon: BookOpen },
  { label: "Admin", href: "/admin", icon: Settings },
];

const STORAGE_KEY = "ftag-sidebar-collapsed";

export function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const { mobileOpen, setMobileOpen } = useSidebarMobile();
  const [collapsed, setCollapsed] = useState(false);

  // Load collapsed state from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      setCollapsed(stored === "true");
    } else {
      // Default: collapsed on tablet (md), expanded on desktop (lg+)
      const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;
      setCollapsed(isTablet);
    }
  }, []);

  function toggleCollapsed() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  function closeMobile() {
    setMobileOpen(false);
  }

  function isActive(href: string) {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname.startsWith(href);
  }

  const sidebarContent = (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div
        className={cn(
          "flex h-14 items-center border-b border-sidebar-border px-4",
          collapsed && "justify-center px-2"
        )}
      >
        <span className="text-xl font-bold text-white">FTAG</span>
        {!collapsed && (
          <span className="ml-2 text-xs text-sidebar-text/60">
            Angebotserstellung
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={closeMobile}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                collapsed && "justify-center px-2",
                active
                  ? "border-l-[3px] border-sidebar-active bg-sidebar-active/10 text-white"
                  : "border-l-[3px] border-transparent text-sidebar-text/80 hover:bg-sidebar-hover hover:text-white"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={20} className="shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle (desktop only) */}
      <div className="hidden border-t border-sidebar-border p-2 md:block">
        <button
          onClick={toggleCollapsed}
          className="flex w-full items-center justify-center rounded-md p-2 text-sidebar-text/60 transition-colors hover:bg-sidebar-hover hover:text-white"
          aria-label={collapsed ? "Sidebar ausklappen" : "Sidebar einklappen"}
        >
          {collapsed ? (
            <ChevronsRight size={18} />
          ) : (
            <ChevronsLeft size={18} />
          )}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile overlay drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={closeMobile}
            aria-hidden
          />
          {/* Drawer */}
          <aside className="absolute inset-y-0 left-0 w-64 bg-sidebar-bg shadow-xl">
            <div className="absolute right-2 top-3 z-10">
              <button
                onClick={closeMobile}
                className="rounded-md p-1 text-sidebar-text/60 hover:text-white"
                aria-label="Menue schliessen"
              >
                <X size={20} />
              </button>
            </div>
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Desktop/tablet sidebar */}
      <aside
        className={cn(
          "hidden h-screen flex-col bg-sidebar-bg transition-[width] duration-200 ease-in-out md:flex",
          collapsed ? "w-16" : "w-60"
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
