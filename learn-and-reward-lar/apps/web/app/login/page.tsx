"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, CardBody, CardHeader, ErrorNotice, Input } from "@/components/ui";
import { ApiError, apiClient, setToken } from "@/lib/api";

/**
 * Placeholder sign-in page. The real auth shell belongs to Developer C's scope;
 * this exists so Mission B's routes are usable end-to-end.
 */
export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "register") {
        await apiClient.register({ email, password, display_name: displayName || email });
      }
      const result = await apiClient.login({ email, password });
      setToken(result.access_token);
      router.push("/learn");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <Card>
        <CardHeader
          title={mode === "login" ? "Sign in" : "Create an account"}
          subtitle="Placeholder auth — will be replaced by the platform core module."
        />
        <CardBody>
          <form onSubmit={submit} className="space-y-3">
            {mode === "register" ? (
              <Input
                placeholder="Display name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            ) : null}
            <Input
              type="email"
              required
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Input
              type="password"
              required
              minLength={8}
              placeholder="Password (min 8 characters)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error ? <ErrorNotice message={error} /> : null}
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}
            </Button>
          </form>
          <button
            className="mt-4 w-full text-center text-sm text-indigo-600 hover:underline"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            type="button"
          >
            {mode === "login" ? "No account yet? Register" : "Already registered? Sign in"}
          </button>
        </CardBody>
      </Card>
    </div>
  );
}
