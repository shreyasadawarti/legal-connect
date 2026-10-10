import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import ConfirmDialog from '@/components/ConfirmDialog'

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    render(<ConfirmDialog open={false} title="Delete chat" onConfirm={vi.fn()} onClose={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows the title and invokes onConfirm', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog open title="Delete chat" confirmLabel="Delete" onConfirm={onConfirm} onClose={vi.fn()} />,
    )
    expect(screen.getByRole('dialog', { name: 'Delete chat' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('invokes onClose from the cancel button and Escape', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ConfirmDialog open title="Clear history" onConfirm={vi.fn()} onClose={onClose} />)
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('disables actions while pending', () => {
    render(
      <ConfirmDialog open isPending title="Delete account" confirmLabel="Delete" onConfirm={vi.fn()} onClose={vi.fn()} />,
    )
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  })
})
