'use client'

import { ClockIcon } from '@heroicons/react/24/outline'
import { BasePage } from '../../components/layout/BasePage'
import { PlaceholderPage } from '../../components/layout/PlaceholderPage'

export default function PredictionsPage() {
  return (
    <BasePage loadingMessage="LOADING PREDICTIONS...">
      <PlaceholderPage
        title="PREDICTIVE ANALYTICS MODULE"
        description="Advanced machine learning models for game outcome predictions, player performance forecasts, and injury risk assessments."
        icon={ClockIcon}
      />
    </BasePage>
  )
}
