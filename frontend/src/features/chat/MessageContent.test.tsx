import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import MessageContent from './MessageContent'

function LocationProbe() {
  const location = useLocation()
  return <span data-testid="location">{location.pathname}</span>
}

function renderContent(text: string, initialPath = '/chat') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <MessageContent text={text} />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('MessageContent', () => {
  it('renders plain text without URLs unchanged', () => {
    renderContent('Please review my case file today.')
    expect(screen.getByText('Please review my case file today.')).toBeTruthy()
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('renders external URLs as clickable links that open in a new tab', () => {
    renderContent('Docs: https://example.com/a.pdf and more text')
    const link = screen.getByRole('link', { name: 'https://example.com/a.pdf' })
    expect(link.getAttribute('href')).toBe('https://example.com/a.pdf')
    expect(link.getAttribute('target')).toBe('_blank')
  })

  it('navigates in-app for same-origin video-call links', async () => {
    const path = `/video-call/${'a'.repeat(24)}`
    const url = `${window.location.origin}${path}`
    renderContent(`Join here ${url}`)
    await userEvent.click(screen.getByRole('link', { name: url }))
    expect(screen.getByTestId('location').textContent).toBe(path)
  })
})
