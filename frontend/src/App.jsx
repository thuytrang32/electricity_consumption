import { useCallback, useEffect, useState } from 'react'
import { createPrediction, getHealth, getModelInfo, getPredictions } from './api'
import PredictionForm from './components/PredictionForm'
import PredictionHistory from './components/PredictionHistory'
import './styles.css'

export default function App() {
  const [predictions, setPredictions] = useState([])
  const [latest, setLatest] = useState(null)
  const [modelInfo, setModelInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [health, setHealth] = useState('checking')

  const refreshHistory = useCallback(async () => {
    const data = await getPredictions(20)
    setPredictions(data)
  }, [])

  useEffect(() => {
    Promise.all([getHealth(), getPredictions(20), getModelInfo()])
      .then(([healthData, history, info]) => {
        setHealth(healthData.status)
        setPredictions(history)
        setModelInfo(info)
      })
      .catch((err) => {
        setHealth('unavailable')
        setError(err.message)
      })
  }, [])

  async function handlePrediction(payload) {
    setLoading(true)
    setError('')
    try {
      const result = await createPrediction(payload)
      setLatest(result)
      await refreshHistory()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="container">
      <header>
        <div>
          <p className="eyebrow">RTE Eco2mix full-stack project</p>
          <h1>Electricity Consumption Predictor</h1>
          <p>React → FastAPI → trained ML model → PostgreSQL</p>
        </div>
        <span className={`status status-${health}`}>API: {health}</span>
      </header>

      {error && <div className="error">{error}</div>}

      {modelInfo && (
        <section className="card model-info">
          <div><small>Training data</small><strong>{modelInfo.data_source}</strong></div>
          <div><small>Period</small><strong>{modelInfo.period_start?.slice(0, 10)} → {modelInfo.period_end?.slice(0, 10)}</strong></div>
          <div><small>Best model</small><strong>{modelInfo.best_model}</strong></div>
          <div><small>Rows</small><strong>{modelInfo.raw_rows_after_cleaning?.toLocaleString()} raw</strong></div>
        </section>
      )}

      <div className="grid">
        <PredictionForm onSubmit={handlePrediction} loading={loading} />
        <section className="card result">
          <h2>Latest result</h2>
          {latest ? (
            <>
              <strong>{latest.prediction_mw.toLocaleString()} MW</strong>
              <p>{latest.model_used}</p>
              <small>{latest.latency_ms.toFixed(2)} ms inference</small>
            </>
          ) : (
            <p>Submit a prediction to see the result.</p>
          )}
        </section>
      </div>

      <PredictionHistory predictions={predictions} />
    </main>
  )
}
