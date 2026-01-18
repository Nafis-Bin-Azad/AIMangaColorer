import React, { createContext, useState, useEffect, useContext } from "react";
import api from "../services/api";

export interface Task {
  id: string;
  type: "colorization" | "download";
  status: "pending" | "processing" | "completed" | "failed";
  title: string;
  progress: number;
  current: number;
  total: number;
  message: string;
  createdAt: string;
  completedAt?: string;
  error?: string;
  metadata?: {
    manga_title?: string;
    chapters?: string[];
    manga_id?: string;
  };
}

interface TaskContextType {
  tasks: Task[];
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  completedTasks: Task[];
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export const useTaskContext = () => {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error("useTaskContext must be used within a TaskProvider");
  }
  return context;
};

export const TaskProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [completedTasks, setCompletedTasks] = useState<Task[]>([]);

  const addTask = (task: Task) => {
    setTasks((prev) => [...prev, task]);
  };

  const updateTask = (id: string, updates: Partial<Task>) => {
    setTasks((prev) =>
      prev.map((task) => (task.id === id ? { ...task, ...updates } : task))
    );
  };

  const removeTask = (id: string) => {
    setTasks((prev) => prev.filter((task) => task.id !== id));
  };

  // Auto-polling for active tasks
  useEffect(() => {
    const interval = setInterval(async () => {
      const activeTasks = tasks.filter(
        (t) => t.status === "pending" || t.status === "processing"
      );

      for (const task of activeTasks) {
        try {
          if (task.type === "colorization") {
            const status = await api.getBatchStatus(task.id);
            updateTask(task.id, {
              status: status.status as Task["status"],
              progress: status.progress,
              current: status.current,
              total: status.total,
              message: status.message,
              error: status.status === "failed" ? status.message : undefined,
            });
          } else if (task.type === "download") {
            const status = await api.getDownloadStatus(task.id);
            updateTask(task.id, {
              status: status.status as Task["status"],
              progress: status.progress || 0,
              current: status.current || 0,
              total: status.total || 0,
              message: status.message || "",
              error: status.status === "failed" ? status.message : undefined,
            });
          }
        } catch (error) {
          console.error(`Failed to update task ${task.id}:`, error);
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [tasks]);

  // Move completed tasks to history
  useEffect(() => {
    tasks.forEach((task) => {
      if (task.status === "completed" || task.status === "failed") {
        const existingCompleted = completedTasks.find((t) => t.id === task.id);
        if (!existingCompleted) {
          setCompletedTasks((prev) => [
            { ...task, completedAt: new Date().toISOString() },
            ...prev,
          ]);
          // Remove from active after 5 seconds
          setTimeout(() => removeTask(task.id), 5000);
        }
      }
    });
  }, [tasks]);

  return (
    <TaskContext.Provider
      value={{ tasks, addTask, updateTask, removeTask, completedTasks }}
    >
      {children}
    </TaskContext.Provider>
  );
};
