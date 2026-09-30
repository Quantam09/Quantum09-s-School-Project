"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Badge, Button, Card, CardBody, CardHeader, ErrorNotice, Spinner } from "@/components/ui";
import { ApiError, apiClient } from "@/lib/api";

export default function CourseDetailPage() {
  const params = useParams<{ courseId: string }>();
  const courseId = params.courseId;

  const course = useQuery({
    queryKey: ["course", courseId],
    queryFn: () => apiClient.getCourse(courseId),
  });

  const claim = useMutation({
    mutationFn: () => apiClient.claimCertificate(courseId),
    onSuccess: () => {
      window.location.href = "/certificates";
    },
  });

  if (course.isLoading) return <Spinner label="Loading course…" />;
  if (course.isError)
    return (
      <ErrorNotice
        message={
          course.error instanceof ApiError ? course.error.message : "Could not load the course."
        }
      />
    );

  const data = course.data!;
  const enrollment = data.enrollment;
  const progress = enrollment ? Math.round((enrollment.lessons_completed / data.lesson_count) * 100) : 0;
  const completed = enrollment?.status === "completed";

  return (
    <div className="space-y-6">
      <Card>
        <CardBody className="space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h1 className="text-xl font-bold text-slate-900">{data.title}</h1>
              <p className="mt-1 text-sm text-slate-600">{data.description}</p>
            </div>
            <Badge tone="indigo">{data.level}</Badge>
          </div>
          {enrollment ? (
            <div>
              <div className="flex items-center justify-between text-sm text-slate-600">
                <span>
                  Progress: {enrollment.lessons_completed}/{data.lesson_count} lessons
                </span>
                {completed ? <Badge tone="green">Completed</Badge> : <Badge>{progress}%</Badge>}
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${progress}%` }} />
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              Not enrolled yet — unlock this course for 🪙 {data.price_coins} coins from the{" "}
              <Link href="/learn" className="text-indigo-600 hover:underline">
                catalog
              </Link>
              .
            </p>
          )}
          {completed ? (
            <div>
              <Button size="sm" disabled={claim.isPending} onClick={() => claim.mutate()}>
                🎓 Claim micro-certificate
              </Button>
              {claim.isError && claim.error instanceof ApiError ? (
                <div className="mt-2">
                  <ErrorNotice
                    message={
                      claim.error.code === "CERTIFICATE_ALREADY_CLAIMED"
                        ? "You already claimed this certificate — see Certificates."
                        : claim.error.message
                    }
                  />
                </div>
              ) : null}
            </div>
          ) : null}
        </CardBody>
      </Card>

      <div className="space-y-3">
        {data.lessons.map((lesson, index) => (
          <Card key={lesson.id}>
            <CardBody className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-700">
                  {index + 1}
                </span>
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">{lesson.title}</h3>
                  <p className="text-xs text-slate-500">Lesson {lesson.order_index + 1}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {lesson.completed ? <Badge tone="green">Done</Badge> : null}
                {enrollment ? (
                  <Link
                    href={`/practice?lesson=${lesson.id}`}
                    className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
                  >
                    {lesson.completed ? "Practice again" : "Start lesson"}
                  </Link>
                ) : null}
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
