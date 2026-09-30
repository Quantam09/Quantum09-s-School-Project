"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Card, CardBody, CardHeader, ErrorNotice, Input, Spinner } from "@/components/ui";
import { ApiError, apiClient, type CertificateVerifyResponse } from "@/lib/api";

function VerifyInner() {
  const searchParams = useSearchParams();
  const initialCode = searchParams.get("code") ?? "";
  const [code, setCode] = useState(initialCode);
  const [submittedCode, setSubmittedCode] = useState(initialCode);

  const verification = useQuery({
    queryKey: ["verify", submittedCode],
    queryFn: () => apiClient.verifyCertificate(submittedCode),
    enabled: Boolean(submittedCode),
    retry: false,
  });

  return (
    <div className="mx-auto max-w-md space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Verify a certificate</h1>
        <p className="mt-1 text-sm text-slate-600">
          Anyone can verify a Learn &amp; Reward micro-certificate by its code — no account needed.
        </p>
      </div>

      <Card>
        <CardHeader title="Certificate code" subtitle="Format: LAR-XXXXXXXXXX" />
        <CardBody>
          <div className="flex gap-2">
            <Input
              placeholder="LAR-…"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === "Enter" && code.trim()) setSubmittedCode(code.trim());
              }}
            />
            <Button disabled={!code.trim()} onClick={() => setSubmittedCode(code.trim())}>
              Verify
            </Button>
          </div>
        </CardBody>
      </Card>

      {submittedCode ? (
        verification.isLoading ? (
          <Spinner label="Checking…" />
        ) : verification.isError ? (
          <ErrorNotice
            message={
              verification.error instanceof ApiError
                ? verification.error.code === "CERTIFICATE_NOT_FOUND"
                  ? "No certificate found for this code."
                  : verification.error.message
                : "Verification failed."
            }
          />
        ) : (
          <ResultCard result={verification.data!} />
        )
      ) : null}
    </div>
  );
}

function ResultCard({ result }: { result: CertificateVerifyResponse }) {
  return (
    <Card className={result.valid && !result.revoked ? "border-emerald-300" : "border-amber-300"}>
      <CardBody className="space-y-1">
        <div className="flex items-center gap-2">
          {result.valid && !result.revoked ? (
            <Badge tone="green">Valid certificate</Badge>
          ) : (
            <Badge tone="amber">Revoked</Badge>
          )}
        </div>
        <p className="text-sm font-semibold text-slate-900">{result.title}</p>
        <p className="font-mono text-sm text-slate-600">{result.code}</p>
        <p className="text-xs text-slate-500">
          Issued {new Date(result.issued_at).toLocaleDateString("en-GB")}
        </p>
      </CardBody>
    </Card>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<Spinner label="Loading…" />}>
      <VerifyInner />
    </Suspense>
  );
}
