import Link from "next/link";

export default function HomePage() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">Learn Luxembourgish, earn rewards</h1>
      <p className="mx-auto mt-2 max-w-xl text-sm text-slate-600">
        A community-governed platform for lesser-taught languages: learn with AI-assisted
        practice, contribute corpus, and earn coins and micro-certificates.
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <Link
          href="/learn"
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Browse courses
        </Link>
        <Link
          href="/chat"
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          Chat with the AI
        </Link>
      </div>
    </div>
  );
}
