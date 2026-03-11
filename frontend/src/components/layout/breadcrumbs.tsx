"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";

export function Breadcrumbs() {
  const breadcrumbs = useBreadcrumbs();

  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex items-center gap-1.5 text-sm">
        {breadcrumbs.map((item, index) => {
          const isLast = index === breadcrumbs.length - 1;
          return (
            <li key={item.href} className="flex items-center gap-1.5">
              {index > 0 && (
                <ChevronRight
                  size={14}
                  className="text-muted-foreground"
                  aria-hidden
                />
              )}
              {isLast ? (
                <span className="font-medium text-foreground">
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.href}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
