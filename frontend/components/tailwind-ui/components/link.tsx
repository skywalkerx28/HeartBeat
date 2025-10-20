import React, { forwardRef } from 'react'
import Link from 'next/link'

interface LinkProps extends React.ComponentPropsWithoutRef<typeof Link> {
  className?: string
}

export const CustomLink = forwardRef<HTMLAnchorElement, LinkProps>(
  function CustomLink({ className, ...props }, ref) {
    return <Link {...props} className={className} ref={ref} />
  }
)

// Export as both named and default for compatibility
export { CustomLink as Link }
export default CustomLink
