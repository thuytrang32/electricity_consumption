import { useState } from 'react'

const initialForm = {
  date: '2025-01-15',
  forecast_j_1: '55000',
  forecast_j: '55200',
  lag_1d: '54800',
  lag_7d: '56000',
  lag_14d: '55800',
  rolling_mean_7d: '55200',
  rolling_mean_30d: '55500',
  fioul: '100',
  coal: '50',
  gas: '3000',
  nuclear: '40000',
  wind: '5000',
  solar: '1000',
  hydraulic: '8000',
  pumping: '-1000',
  bioenergy: '1000',
  physical_exchanges: '0',
  co2_rate: '30',
}

const numericFields = Object.keys(initialForm).filter((key) => key !== 'date')

export default function PredictionForm({ onSubmit, loading }) {
  const [form, setForm] = useState(initialForm)

  function handleChange(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    const payload = { date: form.date }
    numericFields.forEach((field) => {
      payload[field] = Number(form[field])
    })
    onSubmit(payload)
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <h2>New daily prediction</h2>
      <p className="muted">The defaults are RTE-like values so the demo can run immediately.</p>

      <label>
        Prediction date
        <input name="date" type="date" value={form.date} onChange={handleChange} required />
      </label>

      <div className="form-grid">
        <label>
          RTE forecast J-1 (MW)
          <input name="forecast_j_1" type="number" step="1" value={form.forecast_j_1} onChange={handleChange} required />
        </label>
        <label>
          RTE forecast J (MW)
          <input name="forecast_j" type="number" step="1" value={form.forecast_j} onChange={handleChange} required />
        </label>
        <label>
          Consumption lag 1 day (MW)
          <input name="lag_1d" type="number" step="1" value={form.lag_1d} onChange={handleChange} required />
        </label>
        <label>
          Consumption lag 7 days (MW)
          <input name="lag_7d" type="number" step="1" value={form.lag_7d} onChange={handleChange} required />
        </label>
      </div>

      <details>
        <summary>Advanced RTE context</summary>
        <div className="form-grid advanced-grid">
          <label>Lag 14 days<input name="lag_14d" type="number" value={form.lag_14d} onChange={handleChange} /></label>
          <label>Rolling mean 7 days<input name="rolling_mean_7d" type="number" value={form.rolling_mean_7d} onChange={handleChange} /></label>
          <label>Rolling mean 30 days<input name="rolling_mean_30d" type="number" value={form.rolling_mean_30d} onChange={handleChange} /></label>
          <label>Nuclear<input name="nuclear" type="number" value={form.nuclear} onChange={handleChange} /></label>
          <label>Gas<input name="gas" type="number" value={form.gas} onChange={handleChange} /></label>
          <label>Wind<input name="wind" type="number" value={form.wind} onChange={handleChange} /></label>
          <label>Solar<input name="solar" type="number" value={form.solar} onChange={handleChange} /></label>
          <label>Hydraulic<input name="hydraulic" type="number" value={form.hydraulic} onChange={handleChange} /></label>
          <label>Fioul<input name="fioul" type="number" value={form.fioul} onChange={handleChange} /></label>
          <label>Coal<input name="coal" type="number" value={form.coal} onChange={handleChange} /></label>
          <label>Pumping<input name="pumping" type="number" value={form.pumping} onChange={handleChange} /></label>
          <label>Bioenergy<input name="bioenergy" type="number" value={form.bioenergy} onChange={handleChange} /></label>
          <label>Physical exchanges<input name="physical_exchanges" type="number" value={form.physical_exchanges} onChange={handleChange} /></label>
          <label>CO₂ rate<input name="co2_rate" type="number" value={form.co2_rate} onChange={handleChange} /></label>
        </div>
      </details>

      <button type="submit" disabled={loading}>{loading ? 'Predicting…' : 'Predict'}</button>
    </form>
  )
}
