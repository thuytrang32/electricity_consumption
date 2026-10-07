export default function PredictionHistory({ predictions }) {
  return (
    <section className="card history">
      <h2>Prediction history</h2>
      {predictions.length === 0 ? (
        <p>No predictions saved yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Forecast J</th>
                <th>Lag 1d</th>
                <th>Prediction</th>
                <th>Model</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.prediction_date}</td>
                  <td>{item.forecast_j.toLocaleString()} MW</td>
                  <td>{item.lag_1d.toLocaleString()} MW</td>
                  <td>{item.prediction_mw.toLocaleString()} MW</td>
                  <td>{item.model_used}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
