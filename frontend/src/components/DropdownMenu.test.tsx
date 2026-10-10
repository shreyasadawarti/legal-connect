import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DropdownMenu from '@/components/DropdownMenu'

describe('DropdownMenu', () => {
  it('keeps the menu closed until the trigger is pressed', async () => {
    const user = userEvent.setup()
    render(<DropdownMenu items={[{ label: 'Delete Chat', onClick: vi.fn() }]} />)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'More options' }))
    expect(screen.getByRole('menu')).toBeInTheDocument()
  })

  it('invokes the item action and closes the menu', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(<DropdownMenu items={[{ label: 'Block User', onClick }]} />)
    await user.click(screen.getByRole('button', { name: 'More options' }))
    await user.click(screen.getByRole('menuitem', { name: 'Block User' }))
    expect(onClick).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('closes on Escape', async () => {
    const user = userEvent.setup()
    render(<DropdownMenu items={[{ label: 'Report User', onClick: vi.fn() }]} />)
    await user.click(screen.getByRole('button', { name: 'More options' }))
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })
})
