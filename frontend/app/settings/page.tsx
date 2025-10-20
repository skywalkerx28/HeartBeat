'use client'

import { CogIcon } from '@heroicons/react/24/outline'
import { BasePage } from '../../components/layout/BasePage'
import { PlaceholderPage } from '../../components/layout/PlaceholderPage'

export default function SettingsPage() {
  return (
    <BasePage loadingMessage="LOADING SETTINGS...">
      <PlaceholderPage
        title="SYSTEM CONFIGURATION MODULE"
        description="User preferences, system configuration, API settings, and administrative controls for the HeartBeat Engine platform."
        icon={CogIcon}
      />
    </BasePage>
  )
}
