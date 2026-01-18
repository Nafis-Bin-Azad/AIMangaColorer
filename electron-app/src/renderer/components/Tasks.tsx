import React from "react";
import "./Tasks.css";
import { useTaskContext, Task } from "../contexts/TaskContext";

const TaskCard: React.FC<{ task: Task }> = ({ task }) => {
  return (
    <div className={`task-card task-${task.status}`}>
      <div className="task-header">
        <span className="task-type-icon">
          {task.type === "colorization" ? "🎨" : "📥"}
        </span>
        <h3>{task.title}</h3>
        <span className={`task-status-badge status-${task.status}`}>
          {task.status}
        </span>
      </div>

      <div className="task-body">
        <div className="task-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${task.progress}%` }}
            />
          </div>
          <span className="progress-text">
            {task.current}/{task.total} ({task.progress}%)
          </span>
        </div>

        <p className="task-message">{task.message}</p>

        {task.metadata && (
          <div className="task-metadata">
            {task.metadata.manga_title && (
              <span className="metadata-item">
                📚 {task.metadata.manga_title}
              </span>
            )}
            {task.metadata.chapters && (
              <span className="metadata-item">
                📖 {task.metadata.chapters.length} chapters
              </span>
            )}
          </div>
        )}

        {task.error && (
          <div className="task-error">
            <span className="error-icon">⚠️</span>
            <span>{task.error}</span>
          </div>
        )}
      </div>
    </div>
  );
};

const TaskHistoryItem: React.FC<{ task: Task }> = ({ task }) => {
  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div className={`history-item status-${task.status}`}>
      <div className="history-icon">
        {task.type === "colorization" ? "🎨" : "📥"}
      </div>

      <div className="history-content">
        <div className="history-header">
          <h4>{task.title}</h4>
          <span className={`history-status status-${task.status}`}>
            {task.status === "completed" ? "✓ Completed" : "✗ Failed"}
          </span>
        </div>

        {task.metadata && (
          <div className="history-metadata">
            {task.metadata.manga_title && (
              <span>📚 {task.metadata.manga_title}</span>
            )}
            {task.metadata.chapters && (
              <span>📖 {task.metadata.chapters.length} chapters</span>
            )}
            <span>
              {task.current}/{task.total} pages
            </span>
          </div>
        )}

        <div className="history-timestamps">
          <span>Started: {formatDate(task.createdAt)}</span>
          {task.completedAt && (
            <span>Finished: {formatDate(task.completedAt)}</span>
          )}
        </div>

        {task.error && (
          <div className="history-error">
            <span className="error-icon">⚠️</span>
            <span>{task.error}</span>
          </div>
        )}
      </div>
    </div>
  );
};

const Tasks: React.FC = () => {
  const { tasks, completedTasks } = useTaskContext();

  const activeTasks = tasks.filter(
    (t) => t.status === "pending" || t.status === "processing"
  );
  const recentlyCompleted = tasks.filter(
    (t) => t.status === "completed" || t.status === "failed"
  );

  return (
    <div className="tasks-container">
      <div className="tasks-header">
        <h1>Tasks & History</h1>
        <p className="tasks-subtitle">
          Monitor active tasks and view completed history
        </p>
      </div>

      {/* Active Tasks */}
      <section className="tasks-section">
        <div className="section-header">
          <h2>Active Tasks</h2>
          <span className="section-count">{activeTasks.length}</span>
        </div>

        {activeTasks.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⏳</div>
            <h3>No active tasks</h3>
            <p>Tasks will appear here when processing</p>
          </div>
        ) : (
          <div className="tasks-grid">
            {activeTasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        )}
      </section>

      {/* Recently Completed (still in active list but completed) */}
      {recentlyCompleted.length > 0 && (
        <section className="tasks-section">
          <div className="section-header">
            <h2>Recently Completed</h2>
            <span className="section-count">{recentlyCompleted.length}</span>
          </div>

          <div className="tasks-grid">
            {recentlyCompleted.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        </section>
      )}

      {/* History */}
      <section className="tasks-section">
        <div className="section-header">
          <h2>History</h2>
          <span className="section-count">{completedTasks.length}</span>
        </div>

        {completedTasks.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📚</div>
            <h3>No history yet</h3>
            <p>Completed tasks will be archived here</p>
          </div>
        ) : (
          <div className="history-list">
            {completedTasks.map((task) => (
              <TaskHistoryItem key={task.id} task={task} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default Tasks;
