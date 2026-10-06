import { render, screen } from '@testing-library/react'
import { fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import UserAvatar from '@/components/UserAvatar'

describe('UserAvatar', () => {
  it('falls back to initials when there is no picture', () => {
    render(<UserAvatar name="Anita Sharma" />)
    expect(screen.getByText('AS')).toBeInTheDocument()
  })

  it('uses the first and last word for initials', () => {
    render(<UserAvatar name="Pankaj Kumar Tripathi" />)
    expect(screen.getByText('PT')).toBeInTheDocument()
  })

  it('renders two letters for a single-word name', () => {
    render(<UserAvatar name="Meera" />)
    expect(screen.getByText('ME')).toBeInTheDocument()
  })

  it('shows a placeholder for a missing name', () => {
    render(<UserAvatar />)
    expect(screen.getByText('?')).toBeInTheDocument()
  })

  it('renders the image when a picture is set', () => {
    const { container } = render(
      <UserAvatar src="/lawyers/vikram-singh.svg" name="Vikram Singh" />,
    )
    const img = container.querySelector('img')
    expect(img).toHaveAttribute('src', '/lawyers/vikram-singh.svg')
  })

  // A stored Cloudinary URL can disappear, so a broken image has to degrade to
  // initials rather than leaving the browser's broken-image glyph on screen.
  it('falls back to initials when the image fails to load', () => {
    const { container } = render(<UserAvatar src="https://gone/missing.png" name="Rahul Verma" />)
    fireEvent.error(container.querySelector('img')!)
    expect(screen.getByText('RV')).toBeInTheDocument()
  })
})