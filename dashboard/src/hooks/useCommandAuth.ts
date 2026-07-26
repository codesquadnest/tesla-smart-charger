import { useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '@/lib/authStore'

/**
 * Whether command credentials are currently held in this tab.
 *
 * Backed by useSyncExternalStore so every card re-renders the moment the user
 * signs in or out, without threading the state through props.
 */
export function useCommandAuth(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot)
}
