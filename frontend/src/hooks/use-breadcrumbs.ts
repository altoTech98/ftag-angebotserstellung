"use client";

import { usePathname } from "next/navigation";

export interface BreadcrumbItem {
  label: string;
  href: string;
}

const segmentLabels: Record<string, string> = {
  dashboard: "Dashboard",
  projekte: "Projekte",
  "neue-analyse": "Neue Analyse",
  katalog: "Katalog",
  admin: "Admin",
};

export function useBreadcrumbs(): BreadcrumbItem[] {
  const pathname = usePathname();

  const segments = pathname
    .split("/")
    .filter((segment) => segment.length > 0);

  const breadcrumbs: BreadcrumbItem[] = [
    { label: "Start", href: "/" },
  ];

  let currentPath = "";
  for (const segment of segments) {
    currentPath += `/${segment}`;
    const label = segmentLabels[segment] || segment;
    breadcrumbs.push({ label, href: currentPath });
  }

  return breadcrumbs;
}
