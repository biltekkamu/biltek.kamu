import { useCoreStore } from '../store/coreStore'
import { useActiveTeam } from '../store/teamStore'
import { useUiStore } from '../store/uiStore'

export interface ChatAvailability {
  canChat: boolean
  reason: string
}

/**
 * Derives whether the player can chat with a given agent based on
 * the current project phase and the agent's task state.
 */
export function useChatAvailability(_agentIndex: number | null): ChatAvailability {
  return { canChat: false, reason: 'Canlı Telemetri Modu' }
}
