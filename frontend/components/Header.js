export default function Header({ balance }) {
  const empty = balance === 0;
  return (
    <header className="header">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <ellipse cx="8" cy="8" rx="6.5" ry="4" />
            <circle cx="8" cy="8" r="1.8" fill="currentColor" />
          </svg>
        </span>
        Melooha
      </div>
      {typeof balance === "number" && (
        <span className={`balance${empty ? " is-empty" : ""}`} aria-live="polite">
          {balance === 1 ? "1 question left" : `${balance} questions left`}
        </span>
      )}
    </header>
  );
}
