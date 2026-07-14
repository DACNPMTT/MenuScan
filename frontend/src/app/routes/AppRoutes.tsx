import { AnimatedRoutes } from '@/app/routes/AnimatedRoutes'

/** Public route surface — delegates to the animated route tree. The route→page
 * map lives in <AnimatedRoutes> so transitions (AnimatePresence + scroll reset)
 * are wired in one place. */
export function AppRoutes() {
  return <AnimatedRoutes />
}
