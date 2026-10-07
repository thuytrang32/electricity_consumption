async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const body = await response.json()
      message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body)
    } catch {
      // Keep HTTP status when the response is not JSON.
    }
    throw new Error(message)
  }

  return response.json()
}

export function createPrediction(payload) {
  return request('/api/predictions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getPredictions(limit = 20) {
  return request(`/api/predictions?limit=${limit}`)
}

export function getHealth() {
  return request('/health')
}

export function getModelInfo() {
  return request('/api/model-info')
}
