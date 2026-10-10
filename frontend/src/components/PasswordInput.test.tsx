import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import PasswordInput from '@/components/PasswordInput'

describe('PasswordInput', () => {
  it('masks the value by default', () => {
    render(<PasswordInput placeholder="Password" />)
    expect(screen.getByPlaceholderText('Password')).toHaveAttribute('type', 'password')
  })

  it('reveals the value when the eye toggle is pressed', async () => {
    const user = userEvent.setup()
    render(<PasswordInput placeholder="Password" />)
    await user.click(screen.getByRole('button', { name: 'Show password' }))
    expect(screen.getByPlaceholderText('Password')).toHaveAttribute('type', 'text')
  })

  it('hides the value again when toggled back', async () => {
    const user = userEvent.setup()
    render(<PasswordInput placeholder="Password" />)
    await user.click(screen.getByRole('button', { name: 'Show password' }))
    await user.click(screen.getByRole('button', { name: 'Hide password' }))
    expect(screen.getByPlaceholderText('Password')).toHaveAttribute('type', 'password')
  })

  it('accepts typed input and reports it through onChange', async () => {
    const user = userEvent.setup()
    render(<PasswordInput placeholder="Password" />)
    const input = screen.getByPlaceholderText('Password')
    await user.type(input, 'Secret123')
    expect(input).toHaveValue('Secret123')
  })
})
