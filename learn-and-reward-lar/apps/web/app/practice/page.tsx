"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Badge, Button, Card, CardBody, CardHeader, ErrorNotice, Input, Spinner } from "@/components/ui";
import { ApiError, apiClient, getToken, type ExerciseFeedback, type SubmitResponse } from "@/lib/api";

function PracticeInner() {
  const searchParams = useSearchParams();
  const lessonId = searchParams.get("lesson");

  const lesson = useQuery({
    queryKey: ["lesson", lessonId],
    queryFn: () => apiClient.getLesson(lessonId!),
    enabled: Boolean(lessonId),
  });

  const session = useQuery({
    queryKey: ["session", lessonId],
    queryFn: () => apiClient.createSession("lesson_exercises", lessonId!),
    enabled: Boolean(lessonId),
    // A fresh session per visit keeps the exercise set in sync with the lesson.
    gcTime: 0,
    refetchOnMount: "always",
  });

  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [lastSubmit, setLastSubmit] = useState<SubmitResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIndex(0);
    setAnswer("");
    setLastSubmit(null);
  }, [lessonId]);

  const submit = useMutation({
    mutationFn: (payload: { exerciseId: string; answer: string | number }) =>
      apiClient.submitExercise(session.data!.id, payload.exerciseId, payload.answer),
    onSuccess: (data) => {
      setLastSubmit(data);
      setAnswer("");
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : "Submission failed. Try again."),
  });

  const exercises = useMemo(() => lesson.data?.exercises ?? [], [lesson.data]);

  if (!lessonId) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-slate-900">Practice</h1>
        <p className="text-sm text-slate-600">
          Pick a lesson from one of your courses to practice, or{" "}
          <Link href="/chat" className="text-indigo-600 hover:underline">
            start a free conversation with the AI
          </Link>
          .
        </p>
        <MyLessons />
      </div>
    );
  }

  if (lesson.isLoading) return <Spinner label="Loading lesson…" />;
  if (lesson.isError)
    return (
      <ErrorNotice
        message={
          lesson.error instanceof ApiError
            ? lesson.error.code === "UNAUTHORIZED"
              ? "Please sign in to practice."
              : lesson.error.message
            : "Could not load the lesson."
        }
      />
    );
  const lessonData = lesson.data!;

  if (session.isLoading) return <Spinner label="Starting practice session…" />;
  if (session.isError) return <ErrorNotice message="Could not start the practice session." />;

  const sessionData = session.data!;
  const exercise = exercises[index];
  const finished = sessionData.status === "completed" || lastSubmit?.session.status === "completed";

  function next() {
    setLastSubmit(null);
    setAnswer("");
    setIndex((i) => Math.min(i + 1, exercises.length - 1));
  }

  function submitAnswer() {
    if (!exercise) return;
    setError(null);
    if (exercise.type === "multiple_choice") {
      const parsed = Number.parseInt(answer, 10);
      submit.mutate({ exerciseId: exercise.id, answer: Number.isNaN(parsed) ? -1 : parsed });
    } else {
      submit.mutate({ exerciseId: exercise.id, answer });
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-900">{lessonData.title}</h1>
          <p className="text-sm text-slate-500">{lessonData.course_title}</p>
        </div>
        <Badge>
          {Math.min(index + 1, exercises.length)} / {exercises.length}
        </Badge>
      </div>

      <Card>
        <CardHeader
          title={exercise ? formatType(exercise.type) : "No exercises"}
          subtitle={exercise ? exercise.prompt : "This lesson has no exercises yet."}
        />
        <CardBody className="space-y-4">
          {exercise && exercise.type === "multiple_choice" ? (
            <div className="space-y-2">
              {(exercise.options ?? []).map((option, optionIndex) => (
                <button
                  key={optionIndex}
                  type="button"
                  onClick={() => setAnswer(String(optionIndex))}
                  className={`w-full rounded-md border px-4 py-2 text-left text-sm transition-colors ${
                    answer === String(optionIndex)
                      ? "border-indigo-500 bg-indigo-50 text-indigo-900"
                      : "border-slate-300 bg-white hover:bg-slate-50"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          ) : exercise ? (
            <Input
              placeholder="Type your answer…"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && answer.trim()) submitAnswer();
              }}
            />
          ) : null}

          {error ? <ErrorNotice message={error} /> : null}

          {lastSubmit?.feedback ? (
            <FeedbackPanel feedback={lastSubmit.feedback} coins={lastSubmit.coins_awarded} />
          ) : null}

          {finished ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              Session complete! You earned 🪙 {lastSubmit?.coins_awarded || sessionData.coins_awarded}{" "}
              coins.{" "}
              <Link href={`/learn/${lessonData.course_id}`} className="font-medium underline">
                Back to course
              </Link>{" "}
              or{" "}
              <Link href="/certificates" className="font-medium underline">
                check your certificates
              </Link>
              .
            </div>
          ) : (
            <div className="flex justify-end gap-2">
              {lastSubmit ? (
                <Button variant="secondary" onClick={next}>
                  Next exercise
                </Button>
              ) : (
                <Button disabled={!answer.trim() || submit.isPending} onClick={submitAnswer}>
                  {submit.isPending ? "Checking…" : "Check answer"}
                </Button>
              )}
            </div>
          )}
        </CardBody>
      </Card>

      <VocabularyCard vocabulary={lessonData.vocabulary} />
    </div>
  );
}

function MyLessons() {
  const courses = useQuery({ queryKey: ["courses"], queryFn: () => apiClient.listCourses(50) });
  if (courses.isLoading) return <Spinner />;
  if (courses.isError) return <ErrorNotice message="Could not load courses." />;
  return (
    <div className="space-y-3">
      {courses.data!.items.map((course) => (
        <Card key={course.id}>
          <CardHeader title={course.title} subtitle={`${course.lesson_count} lessons`} />
          <CardBody className="flex gap-2">
            <Link
              href={`/learn/${course.id}`}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Open course
            </Link>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function FeedbackPanel({ feedback, coins }: { feedback: ExerciseFeedback; coins: number }) {
  return (
    <div
      className={`rounded-md border px-4 py-3 text-sm ${
        feedback.correct
          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
          : "border-amber-200 bg-amber-50 text-amber-900"
      }`}
    >
      <p className="font-medium">{feedback.correct ? "Correct!" : "Not quite."}</p>
      {!feedback.correct && feedback.expected ? <p>Expected answer: {feedback.expected}</p> : null}
      {feedback.explanation ? <p className="mt-1 text-slate-700">{feedback.explanation}</p> : null}
      {feedback.ai_hint ? <p className="mt-1 italic">AI hint: {feedback.ai_hint}</p> : null}
      {coins > 0 ? <p className="mt-1 font-medium">+🪙 {coins} coins earned for this session!</p> : null}
    </div>
  );
}

function VocabularyCard({
  vocabulary,
}: {
  vocabulary: { term: string; translation: string; pronunciation: string | null }[];
}) {
  if (!vocabulary.length) return null;
  return (
    <Card>
      <CardHeader title="Vocabulary" />
      <CardBody>
        <ul className="grid gap-2 sm:grid-cols-2">
          {vocabulary.map((item) => (
            <li key={item.term} className="rounded-md bg-slate-50 px-3 py-2 text-sm">
              <span className="font-medium text-slate-900">{item.term}</span>
              <span className="text-slate-600"> — {item.translation}</span>
              {item.pronunciation ? (
                <span className="ml-1 text-xs text-slate-400">({item.pronunciation})</span>
              ) : null}
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

function formatType(type: string): string {
  switch (type) {
    case "multiple_choice":
      return "Multiple choice";
    case "fill_in_blank":
      return "Fill in the blank";
    case "translation":
      return "Translation";
    default:
      return "Exercise";
  }
}

export default function PracticePage() {
  return (
    <Suspense fallback={<Spinner label="Loading practice…" />}>
      <PracticeInner />
    </Suspense>
  );
}
