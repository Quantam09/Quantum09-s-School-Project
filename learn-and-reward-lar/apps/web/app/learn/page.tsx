"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, CardBody, ErrorNotice, Spinner } from "@/components/ui";
import { ApiError, apiClient, getToken, type CourseSummary } from "@/lib/api";

const LEVEL_TONES = { beginner: "green", intermediate: "amber", advanced: "indigo" } as const;

export default function LearnPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const courses = useQuery({
    queryKey: ["courses"],
    queryFn: () => apiClient.listCourses(50),
  });

  const enroll = useMutation({
    mutationFn: (course: CourseSummary) => apiClient.enroll(course.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["courses"] });
    },
  });

  if (courses.isLoading) return <Spinner label="Loading courses…" />;
  if (courses.isError) return <ErrorNotice message="Could not load courses. Is the API running?" />;

  return (
    <div>
      <h1 className="text-xl font-bold text-slate-900">Courses</h1>
      <p className="mt-1 text-sm text-slate-600">
        Unlock a course with coins. Community contributors receive the largest share.
      </p>
      {enroll.isError && enroll.error instanceof ApiError ? (
        <div className="mt-4">
          <ErrorNotice
            message={
              enroll.error.code === "ALREADY_ENROLLED"
                ? "You are already enrolled in this course."
                : enroll.error.code === "UNAUTHORIZED"
                  ? "Please sign in to enroll."
                  : enroll.error.message
            }
          />
        </div>
      ) : null}
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {courses.data!.items.map((course) => (
          <Card key={course.id}>
            <CardBody className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-semibold text-slate-900">{course.title}</h2>
                <Badge tone={LEVEL_TONES[course.level]}>{course.level}</Badge>
              </div>
              <p className="text-sm text-slate-600">{course.description}</p>
              <div className="flex items-center justify-between text-sm text-slate-500">
                <span>
                  {course.lesson_count} lessons · {course.language.toUpperCase()}
                </span>
                <Badge>🪙 {course.price_coins} coins</Badge>
              </div>
              <div className="flex gap-2">
                <Link
                  href={`/learn/${course.id}`}
                  className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  View course
                </Link>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={enroll.isPending}
                  onClick={() => {
                    if (!getToken()) {
                      router.push("/login");
                      return;
                    }
                    enroll.mutate(course);
                  }}
                >
                  Enroll
                </Button>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
