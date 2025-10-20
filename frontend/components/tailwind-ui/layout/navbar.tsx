'use client'

import * as Headless from '@headlessui/react'
import clsx from 'clsx'
import React, { forwardRef } from 'react'
import { TouchTarget } from './button'
import { Link } from './link'

export function Navbar({ className, ...props }: React.ComponentPropsWithoutRef<'nav'>) {
  return <nav {...props} className={clsx(className, 'flex items-center justify-between')} />
}

export const NavbarItem = forwardRef(function NavbarItem(
  {
    current,
    className,
    children,
    ...props
  }: { current?: boolean; className?: string; children: React.ReactNode } & (
    | ({ href?: never } & Omit<Headless.ButtonProps, 'as' | 'className'>)
    | ({ href: string } & Omit<React.ComponentPropsWithoutRef<typeof Link>, 'className'>)
  ),
  ref: React.ForwardedRef<HTMLAnchorElement | HTMLButtonElement>
) {
  let classes = clsx(
    // Base
    'flex items-center gap-3 rounded-lg px-3 py-2 text-left text-base/6 font-medium',
    // Leading icon/icon-only
    '*:data-[slot=icon]:size-6 *:data-[slot=icon]:shrink-0 sm:*:data-[slot=icon]:size-5',
    // Trailing icon (down chevron or similar)
    '*:last:data-[slot=icon]:ml-auto *:last:data-[slot=icon]:size-5 sm:*:last:data-[slot=icon]:size-4',
    // Avatar
    '*:data-[slot=avatar]:-m-0.5 *:data-[slot=avatar]:size-7 sm:*:data-[slot=avatar]:size-6',
    // Hover
    'data-hover:bg-zinc-950/5',
    // Active
    'data-active:bg-zinc-950/5',
    // Dark mode
    'dark:text-white',
    'dark:data-hover:bg-white/5',
    'dark:data-active:bg-white/5'
  )

  return typeof props.href === 'string' ? (
    <Link
      {...props}
      className={clsx(className, classes)}
      data-current={current ? 'true' : undefined}
      ref={ref as React.ForwardedRef<HTMLAnchorElement>}
    >
      <TouchTarget>{children}</TouchTarget>
    </Link>
  ) : (
    <Headless.Button
      {...props}
      className={clsx(className, 'cursor-default', classes)}
      data-current={current ? 'true' : undefined}
      ref={ref as React.ForwardedRef<HTMLButtonElement>}
    >
      <TouchTarget>{children}</TouchTarget>
    </Headless.Button>
  )
})
