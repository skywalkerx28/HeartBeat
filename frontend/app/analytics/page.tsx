'use client'

import { BasePage } from '../../components/layout/BasePage'
import { MilitaryAnalyticsDashboard } from '../../components/analytics/MilitaryAnalyticsDashboard'

export default function AnalyticsPage() {
  return (
    <BasePage loadingMessage="LOADING ANALYTICS...">
      <MilitaryAnalyticsDashboard />
    </BasePage>
  )
}
