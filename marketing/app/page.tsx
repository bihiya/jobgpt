/**
 * SSR marketing homepage (Next.js App Router).
 * Revalidate periodically for ISR-like freshness of static marketing copy.
 */
export const revalidate = 3600; // ISR: regenerate at most once/hour

const features = [
  { title: 'LLM ranking', body: 'Blend heuristic fit with model rationale before you apply.' },
  { title: 'Human-in-the-loop', body: 'Approve or reject matches from desktop or the PWA.' },
  { title: 'Smart answers', body: 'Question bank fills repetitive application forms.' },
  { title: 'Portal health', body: 'Auto-pause flaky portals and keep pipelines reliable.' },
];

export default function HomePage() {
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
  return (
    <main className="hero">
      <p style={{ color: 'var(--accent)', fontWeight: 700, marginBottom: 8, letterSpacing: '0.04em' }}>Job automation platform</p>
      <h1 className="brand">JobPilot AI</h1>
      <p className="lead">
        Configure your resume and portals once. JobPilot scans continuously, explains match scores,
        and applies with your approval — not blind automation.
      </p>
      <div className="cta">
        <a className="btn btn-primary" href={`${appUrl}/register`}>
          Start free
        </a>
        <a className="btn btn-ghost" href={`${appUrl}/login`}>
          Sign in
        </a>
      </div>
      <section className="grid" aria-label="Features">
        {features.map((f) => (
          <article className="card" key={f.title}>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
