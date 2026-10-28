import { Card, DataTable, FeatureCard, PageHead } from '../components/ui.jsx';

const LABS = [
  { lab: 'Lab 1', topic: 'Data collection: structured & unstructured', module: 'src/data_generation, src/ingestion (CSV, JSON, XML, TXT regex)' },
  { lab: 'Lab 2', topic: 'Data cleaning & preprocessing', module: 'src/cleaning/cleaner.py, cleaning_report.py' },
  { lab: 'Lab 3', topic: 'Relationships & cardinality', module: 'src/database/schema.py (ER model, PK/FK)' },
  { lab: 'Lab 4', topic: 'Loading data into SQL', module: 'src/database/db_loader.py (SQLAlchemy, to_sql)' },
  { lab: 'Lab 5', topic: 'SQL queries from Python', module: 'src/database/queries.py' },
  { lab: 'Lab 6', topic: 'Visualisation & Excel outputs', module: 'src/visualization, outputs/excel' },
  { lab: 'Lab 7', topic: 'Time-series analysis & forecasting', module: 'src/timeseries (decomposition, smoothing, ARIMA)' },
  { lab: 'Extra', topic: 'Journey planner & web UI', module: 'src/planner.py, src/api.py, server/ (Express), client/ (React)' },
];

const STACK = ['Python 3', 'pandas', 'NumPy', 'SQLAlchemy', 'SQLite', 'statsmodels', 'scikit-learn', 'Matplotlib', 'Seaborn', 'openpyxl',
  'pytest', 'Node.js', 'Express', 'React', 'Vite', 'Plotly.js', 'Mermaid'];

export default function About() {
  return (
    <div className="page-enter">
      <PageHead eyebrow="About the project" title="Indian Railways Train Delay Analysis & Forecasting">
        An academic Data Analytics &amp; Visualisation (DAV) mini-project.
      </PageHead>

      <div className="grid grid-2">
        <Card title="Problem statement">
          <div className="prose mt-8">
            <p>Indian Railways runs thousands of passenger trains every day and delays are frequent. Delay information is scattered
              across many sources and rarely stored in one place, so it is hard to see patterns or plan around them.</p>
            <p>This project reads delay data in several formats, cleans it, models the relationships, loads it into a SQL database,
              analyses and visualises it, forecasts the next three months, and helps a traveller pick the train that will really get
              them there first.</p>
          </div>
        </Card>
        <Card title="Objectives">
          <ol className="prose mt-8" style={{ paddingLeft: 20, margin: 0 }}>
            <li>Collect and extract structured and unstructured railway data</li>
            <li>Clean and preprocess it (missing values, duplicates, outliers)</li>
            <li>Define relational tables with keys and cardinality</li>
            <li>Load the cleaned data into a SQL database with SQLAlchemy</li>
            <li>Run analytical SQL queries from Python</li>
            <li>Produce visualisations and Excel-ready outputs</li>
            <li>Analyse the time series and forecast average delay for the next 3 months</li>
          </ol>
        </Card>
      </div>

      <section className="section" style={{ marginTop: 64 }}>
        <h2>Tech stack</h2>
        <div className="tech-chips mt-16">{STACK.map((s) => <span key={s} className="chip indigo">{s}</span>)}</div>
      </section>

      <section className="section" style={{ marginTop: 64 }}>
        <h2 style={{ marginBottom: 16 }}>Lab-to-module mapping</h2>
        <DataTable rows={LABS} columns={[{ key: 'lab', label: 'Lab', render: (v) => <strong>{v}</strong> }, { key: 'topic', label: 'Topic' }, { key: 'module', label: 'Where in the code', render: (v) => <code>{v}</code> }]} />
      </section>

      <section className="section" style={{ marginTop: 64 }}>
        <h2 style={{ marginBottom: 8 }}>Future scope</h2>
        <div className="feature-grid">
          <FeatureCard icon="signal" title="Live running status">Plug in real NTES / running-status data in place of the simulated records.</FeatureCard>
          <FeatureCard icon="forecast" title="Better models">Add weather and holiday features, try SARIMA, Prophet or gradient boosting per route.</FeatureCard>
          <FeatureCard icon="route" title="Connections">Suggest journeys with a change of train, not only direct trains.</FeatureCard>
        </div>
      </section>

      <section className="section" style={{ marginTop: 64 }}>
        <Card title="Team">
          <p className="mt-8">Student name(s): ______________________ · Roll no.: __________ · Guide: ______________________</p>
          <p className="small muted mt-8">Data is simulated for academic purposes. No live scraping of NTES, IRCTC, eRail or RailYatri.</p>
        </Card>
      </section>
    </div>
  );
}
