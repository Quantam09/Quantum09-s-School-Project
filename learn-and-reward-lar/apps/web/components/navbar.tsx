"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";
import { Button } from "@/components/ui";
import { useAuthState } from "@/lib/auth";

const links = [
  { href: "/learn", label: "Learn" },
  { href: "/practice", label: "Practice" },
  { href: "/chat", label: "Chat" },
  { href: "/certificates", label: "Certificates" },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuthState();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
        <Link href="/learn" className="text-sm font-bold tracking-tight text-indigo-700">
          Learn &amp; Reward
        </Link>
        <nav className="flex flex-1 items-center gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={clsx(
                "rounded-md px-3 py-1.5 text-sm",
                pathname.startsWith(link.href)
                  ? "bg-indigo-50 font-medium text-indigo-700"
                  : "text-slate-600 hover:bg-slate-100",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        {loading ? null : user ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-600">{user.display_name || user.email}</span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                logout();
                router.push("/login");
              }}
            >
              Log out
            </Button>
          </div>
        ) : (
          <Button size="sm" onClick={() => router.push("/login")}>
            Sign in
          </Button>
        )}
      </div>
    </header>
  );
}
