export function LoadingView({ waking }) {
  return (
    <div className="fullscreen" role="status">
      <div className="spinner" aria-hidden="true" />
      <h2>{waking ? "Waking up the server" : "Getting things ready"}</h2>
      <p className="muted">
        {waking
          ? "This can take up to a minute the first time. Thank you for waiting."
          : "Just a moment."}
      </p>
    </div>
  );
}

export function ErrorView({ message, onRetry }) {
  return (
    <div className="fullscreen" role="alert">
      <h2>We could not load Melooha</h2>
      <p className="muted">{message}</p>
      <button className="btn btn-primary" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
