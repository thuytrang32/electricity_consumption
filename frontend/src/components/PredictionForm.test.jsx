import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import PredictionForm from './PredictionForm'

test('submits the date and numeric RTE features', () => {
  const onSubmit = vi.fn()
  render(<PredictionForm onSubmit={onSubmit} loading={false} />)

  fireEvent.change(screen.getByLabelText(/RTE forecast J \(MW\)/i), {
    target: { value: '57000' },
  })
  fireEvent.click(screen.getByRole('button', { name: /^predict$/i }))

  expect(onSubmit).toHaveBeenCalledTimes(1)
  expect(onSubmit.mock.calls[0][0].date).toBe('2025-01-15')
  expect(onSubmit.mock.calls[0][0].forecast_j).toBe(57000)
  expect(onSubmit.mock.calls[0][0].lag_1d).toBeTypeOf('number')
})
