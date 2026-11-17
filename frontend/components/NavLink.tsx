"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Icon, iconFor } from "@/components/Icon";

/** Navigation link that marks the current page for assistive technology and visually. */
export function NavLink({ href, children }: { href: string; children: ReactNode }) {
  const pathname = usePathname();
  const current = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link href={href} aria-current={current ? "page" : undefined} className="nav-link">
      <Icon name={iconFor(href)} />
      {children}
    </Link>
  );
}
