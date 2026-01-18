import { useState } from "react";
import "./styles/App.css";
import SingleImage from "./components/SingleImage";
import BatchProcessing from "./components/BatchProcessing";
import MangaBrowser from "./components/MangaBrowser";
import MangaReader from "./components/MangaReader";
import Tasks from "./components/Tasks";
import { TaskProvider } from "./contexts/TaskContext";
import { ToastContainer } from "./components/ToastNotification";

function App() {
  const [activeTab, setActiveTab] = useState<string>("single");

  return (
    <TaskProvider>
      <div className="app">
        <header className="app-header">
          <h1>🎨 Manga Colorizer</h1>
          <p>AI-powered manga colorization with MCV2 engine</p>
        </header>

        <div className="tabs">
          <button
            className={activeTab === "single" ? "tab active" : "tab"}
            onClick={() => setActiveTab("single")}
          >
            Single Image
          </button>
          <button
            className={activeTab === "batch" ? "tab active" : "tab"}
            onClick={() => setActiveTab("batch")}
          >
            Batch Processing
          </button>
          <button
            className={activeTab === "browser" ? "tab active" : "tab"}
            onClick={() => setActiveTab("browser")}
          >
            Manga Browser
          </button>
          <button
            className={activeTab === "reader" ? "tab active" : "tab"}
            onClick={() => setActiveTab("reader")}
          >
            Manga Reader
          </button>
          <button
            className={activeTab === "tasks" ? "tab active" : "tab"}
            onClick={() => setActiveTab("tasks")}
          >
            Tasks
          </button>
        </div>

        <main className="main-content">
          {activeTab === "single" && <SingleImage />}
          {activeTab === "batch" && <BatchProcessing />}
          {activeTab === "browser" && <MangaBrowser />}
          {activeTab === "reader" && <MangaReader />}
          {activeTab === "tasks" && <Tasks />}
        </main>

        <ToastContainer onNavigateToTasks={() => setActiveTab("tasks")} />
      </div>
    </TaskProvider>
  );
}

export default App;
