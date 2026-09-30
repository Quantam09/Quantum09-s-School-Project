"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, CardBody, CardHeader, ErrorNotice, Spinner } from "@/components/ui";
import { ApiError, apiClient, getToken } from "@/lib/api";

export default function CertificatesPage() {
  const queryClient = useQueryClient();
  const certificates = useQuery({
    queryKey: ["certificates"],
    queryFn: () => apiClient.listCertificates(),
    enabled: Boolean(getToken()),
  });

  const courses = useQuery({ queryKey: ["courses"], queryFn: () => apiClient.listCourses(50) });

  const claim = useMutation({
    mutationFn: (courseId: string) => apiClient.claimCertificate(courseId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["certificates"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">My certificates</h1>
        <p className="mt-1 text-sm text-slate-600">
          Micro-certificates are issued when every lesson of a course is completed.
        </p>
      </div>

      {!getToken() ? (
        <ErrorNotice message="Please sign in to view your certificates." />
      ) : certificates.isLoading ? (
        <Spinner label="Loading certificates…" />
      ) : certificates.isError ? (
        <ErrorNotice message="Could not load certificates." />
      ) : certificates.data!.length === 0 ? (
        <Card>
          <CardBody className="text-sm text-slate-600">
            No certificates yet. Complete all lessons of a course — your progress is tracked on
            each course page.{" "}
            <Link href="/learn" className="text-indigo-600 hover:underline">
              Browse courses
            </Link>
            .
          </CardBody>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {certificates.data!.map((certificate) => (
            <Card key={certificate.id} className="border-indigo-200 bg-gradient-to-br from-indigo-50 to-white">
              <CardBody className="space-y-2">
                <div className="flex items-start justify-between">
                  <span className="text-2xl">🎓</span>
                  {certificate.revoked ? <Badge tone="amber">Revoked</Badge> : <Badge tone="green">Valid</Badge>}
                </div>
                <h3 className="font-semibold text-slate-900">{certificate.title}</h3>
                <p className="text-xs text-slate-500">
                  Issued {new Date(certificate.issued_at).toLocaleDateString("en-GB")}
                </p>
                <p className="font-mono text-sm text-indigo-800">{certificate.code}</p>
                <Link
                  href={`/certificates/verify?code=${certificate.code}`}
                  className="inline-block text-sm text-indigo-600 hover:underline"
                >
                  Open verification page
                </Link>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {claim.isError && claim.error instanceof ApiError ? (
        <ErrorNotice message={claim.error.message} />
      ) : null}

      <Card>
        <CardHeader
          title="Claim a certificate"
          subtitle="Claimable once your enrollment shows Completed on the course page."
        />
        <CardBody className="space-y-3">
          {courses.isLoading ? (
            <Spinner />
          ) : (
            <div className="space-y-2">
              {(courses.data?.items ?? []).map((course) => (
                <div key={course.id} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                  <span className="text-sm text-slate-800">{course.title}</span>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={claim.isPending}
                    onClick={() => claim.mutate(course.id)}
                  >
                    Claim
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
