import { Link } from "react-router-dom";

type FixedHeaderProps = {
  pageTitle?: string;
};

export function FixedHeader({ pageTitle }: FixedHeaderProps) {
  return (
    <header className="fixed left-0 right-0 top-0 z-50 border-b border-white/10 bg-[#071425]/90 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 py-3 md:px-8">
        <h1 className="text-base font-semibold tracking-wide text-white md:text-lg">
          <Link to="/" className="transition hover:text-cyan">
            Niche Partnerships Intelligence Platform
          </Link>
          {pageTitle ? ` / ${pageTitle}` : ""}
        </h1>
      </div>
    </header>
  );
}
