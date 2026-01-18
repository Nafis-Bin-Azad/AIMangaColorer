import React, { useState, useEffect } from "react";
import "./ToastNotification.css";
import { useTaskContext } from "../contexts/TaskContext";

interface ToastProps {
  message: string;
  type: "success" | "error" | "info";
  onDismiss: () => void;
  onClick?: () => void;
}

const ToastNotification: React.FC<ToastProps> = ({
  message,
  type,
  onDismiss,
  onClick,
}) => {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      className={`toast toast-${type}`}
      onClick={onClick}
      style={{ cursor: onClick ? "pointer" : "default" }}
    >
      <div className="toast-content">
        <span className="toast-icon">
          {type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️"}
        </span>
        <span className="toast-message">{message}</span>
      </div>
      <button
        className="toast-close"
        onClick={(e) => {
          e.stopPropagation();
          onDismiss();
        }}
      >
        ✕
      </button>
    </div>
  );
};

interface ToastData {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface ToastContainerProps {
  onNavigateToTasks: () => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({
  onNavigateToTasks,
}) => {
  const { tasks, completedTasks } = useTaskContext();
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const [shownTaskIds, setShownTaskIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    // Watch for completed/failed tasks and show toasts
    const allTasks = [...tasks, ...completedTasks];

    allTasks.forEach((task) => {
      if (shownTaskIds.has(task.id)) return;

      if (task.status === "completed") {
        setToasts((prev) => [
          ...prev,
          {
            id: task.id,
            message: `${task.title} completed!`,
            type: "success",
          },
        ]);
        setShownTaskIds((prev) => new Set(prev).add(task.id));
      } else if (task.status === "failed") {
        setToasts((prev) => [
          ...prev,
          {
            id: task.id,
            message: `${task.title} failed: ${task.error || "Unknown error"}`,
            type: "error",
          },
        ]);
        setShownTaskIds((prev) => new Set(prev).add(task.id));
      }
    });
  }, [tasks, completedTasks, shownTaskIds]);

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleToastClick = (id: string) => {
    onNavigateToTasks();
    dismissToast(id);
  };

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <ToastNotification
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onDismiss={() => dismissToast(toast.id)}
          onClick={() => handleToastClick(toast.id)}
        />
      ))}
    </div>
  );
};

export default ToastNotification;
