import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import App from '@/app/App'

describe('App smoke test', () => {
  it('renders the landing page', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Legal Assistance/i)).toBeInTheDocument()
  })

  it('renders the 404 page for unknown routes', () => {
    render(
      <MemoryRouter initialEntries={['/unknown-route']}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByText('404')).toBeInTheDocument()
  })
})
