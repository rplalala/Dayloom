import { createContext, useContext } from 'react';
import type { PlanningTask } from './taskClient';

export type TaskObservation = { tasks: PlanningTask[]; error: string; refresh: () => Promise<void> };
export const TaskContext = createContext<TaskObservation | null>(null);
export function useTasks() { const context = useContext(TaskContext); if (!context) throw new Error('TaskProvider is required'); return context; }
