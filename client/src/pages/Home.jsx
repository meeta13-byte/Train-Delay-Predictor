import { Link, useNavigate } from 'react-router-dom';
import { api, useApi } from '../api.js';
import heroSvg from '../assets/hero.svg?raw';
import { ErrorState, FeatureCard, IconBlob } from '../components/ui.jsx';
import { fmt } from '../theme.js';

const STEPS = [
  { icon: 'files', title: 'Collect', text: 'CSV, JSON, XML and TXT files' },
  { icon: 'broom', title: 'Clean', text: 'Missing values, duplicates, outliers' },
  { icon: 'database', title: 'Store', text: 'Relational tables in SQL' },
  { icon: 'chart', title: 'Analyse', text: 'SQL queries from Python' },
  { icon: 'pin', title: 'Visualise', text: 'Interactive charts and maps' },
  { icon: 'forecast', title: 'Forecast', text: 'ARIMA, next 3 months' },
];

export default function Home() {
  const navigate = useNavigate();
  const home = useApi('home', () => api.get('/api/home'));
  const d = home.data;

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <h1>
            Know when your train will run late, <span className="marker">before it does</span>
          </h1>
          <p>We collect, clean and analyse Indian Railways delay data from CSV, JSON, XML and text files, and forecast delays for the next 3 months.</p>
          <div className="hero-actions">
            <button type="button" className="btn btn-primary" onClick={() => navigate('/dashboard')}>Explore dashboard</button>
            <a className="btn btn-secondary" href="#how-it-works">See how it works</a>
          </div>
          <p className="small muted">
            Travelling soon? <Link to="/plan">Check your train and find a faster one →</Link>
          </p>
        </div>
        <div className="hero-art">
          <div dangerouslySetInnerHTML={{ __html: heroSvg }} />
          {d && (
            <div className="floating-card" style={{ left: '8%', top: '6%' }}>
              <div className="fc-dot"><img src="/favicon.svg" alt="" width="22" height="22" /></div>
              <div>
                <div className="fc-label">Typical delay in {d.month_name}</div>
                <div className="fc-value"><em>{fmt.min(d.month_avg_delay)}</em> min</div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="section" aria-labelledby="insights">
        <div className="section-head">
          <div>
            <div className="eyebrow">From {d ? `${fmt.int(d.total_records)} delay records` : 'the data'}</div>
            <h2 id="insights">Key insights</h2>
          </div>
          <Link to="/delays" className="btn btn-secondary btn-small">See all analysis</Link>
        </div>
        {home.error ? (
          <ErrorState error={home.error} onRetry={home.reload} />
        ) : (
          <div className="feature-grid">
            <FeatureCard icon="train" title="Most delayed train" stat={d ? `${fmt.min(d.most_delayed_train.avg_delay)} min` : '…'} accent>
              {d ? `${d.most_delayed_train.train_no} ${d.most_delayed_train.train_name} runs late the most on average.` : 'Loading…'}
            </FeatureCard>
            <FeatureCard icon="clock" title="Winter fog impact" stat={d ? `+${fmt.min(d.fog_impact_pct)}%` : '…'}>
              {d ? `Trains are ${fmt.min(d.fog_impact_pct)}% later in Dec–Jan than in Mar–Nov (${fmt.min(d.fog_avg)} vs ${fmt.min(d.rest_avg)} min).` : 'Loading…'}
            </FeatureCard>
            <FeatureCard icon="signal" title="On-time performance" stat={d ? fmt.pct(d.ontime_pct) : '…'}>
              {d ? `Share of station arrivals no more than 15 minutes late, across ${d.n_trains} trains and ${d.n_stations} stations.` : 'Loading…'}
            </FeatureCard>
          </div>
        )}
      </section>

      <section className="section" id="how-it-works" aria-labelledby="how">
        <div className="section-head">
          <div>
            <div className="eyebrow">The pipeline</div>
            <h2 id="how">How it works</h2>
          </div>
          <Link to="/pipeline" className="btn btn-secondary btn-small">Open the data pipeline</Link>
        </div>
        <ol className="flow">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <IconBlob icon={s.icon} />
              <span className="step-no">STEP {i + 1}</span>
              <strong>{s.title}</strong>
              <span>{s.text}</span>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
