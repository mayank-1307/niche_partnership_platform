import { Link } from "react-router-dom";
import { FixedHeader } from "../components/FixedHeader";

export default function HomePage() {
  return (
    <>
      <FixedHeader />
      <div className="mx-auto flex min-h-screen max-w-5xl items-center px-4 py-10 pt-24 md:px-8">
        <div className="glass w-full rounded-3xl p-8 md:p-12">
          <h1 className="text-3xl font-bold md:text-5xl">Niche Partnerships Intelligence Platform</h1>
          <p className="mt-3 max-w-2xl text-slate-300">Choose a workspace to continue.</p>

          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
            <Link to="/analysis" className="rounded-xl border border-white/20 bg-black/30 px-6 py-4 text-center font-semibold text-white/90 transition hover:bg-indigo">
              Partner Analysis
            </Link>
            <Link to="/decision-intelligence" className="rounded-xl border border-white/20 bg-black/30 px-6 py-4 text-center font-semibold text-white/90 transition hover:bg-indigo">
              Decision Intelligence
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}


// bg-gradient-to-r from-cyan to-indigo
