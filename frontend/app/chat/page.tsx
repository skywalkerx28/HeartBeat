'use client'

import { BasePage } from '../../components/layout/BasePage'
import { MilitaryChatInterface } from '../../components/hockey-specific/MilitaryChatInterface'

export default function ChatPage() {
  return (
    <BasePage loadingMessage="INITIALIZING HEARTBEAT AI...">
      <MilitaryChatInterface />
    </BasePage>
  )
}
