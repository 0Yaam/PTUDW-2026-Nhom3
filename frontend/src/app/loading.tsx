export default function Loading() {
  return (
    <main className="loading-shell" aria-busy="true" aria-label="Loading data">
      <div className="loading-line short" />
      <div className="loading-line title" />
      <div className="loading-line" />
      <div className="loading-cards">
        {[0, 1, 2, 3].map((item) => <div className="loading-card" key={item} />)}
      </div>
    </main>
  );
}
