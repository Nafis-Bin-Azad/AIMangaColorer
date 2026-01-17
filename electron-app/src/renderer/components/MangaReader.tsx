import React, { useState, useEffect } from "react";
import "./MangaReader.css";
import api from "../services/api";

interface Manga {
  title: string;
  path: string;
  chapters: string[];
  total_chapters: number;
  last_read: string | null;
  progress: number;
  has_cover: boolean;
}

interface Chapter {
  id: string;
  name: string;
  pages: number;
  has_colored: boolean;
  last_page: number;
  last_read: string | null;
}

interface Page {
  index: number;
  url: string;
  filename: string;
}

const MangaReader: React.FC = () => {
  const [view, setView] = useState<"library" | "reader">("library");
  const [library, setLibrary] = useState<Manga[]>([]);
  const [loadingLibrary, setLoadingLibrary] = useState(false);

  // Reader state
  const [currentManga, setCurrentManga] = useState<string | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentChapter, setCurrentChapter] = useState<string | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [useColored, setUseColored] = useState(false);
  const [loadingPages, setLoadingPages] = useState(false);
  const [fitMode, setFitMode] = useState<"width" | "height" | "actual">(
    "width"
  );
  const [showThumbnails, setShowThumbnails] = useState(false);
  const [bookmarks, setBookmarks] = useState<Set<number>>(new Set());
  const [colorizing, setColorizing] = useState(false);

  // Initialize API service
  useEffect(() => {
    api.initialize();
  }, []);

  // Load library
  useEffect(() => {
    if (view === "library") {
      loadLibrary();
    }
  }, [view]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (view !== "reader") return;

      switch (e.key) {
        case "ArrowLeft":
          previousPage();
          break;
        case "ArrowRight":
          nextPage();
          break;
        case "Escape":
          closeReader();
          break;
        case "t":
          setShowThumbnails(!showThumbnails);
          break;
        case "b":
          toggleBookmark();
          break;
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [view, currentPage, showThumbnails]);

  // Auto-save progress
  useEffect(() => {
    if (currentManga && currentChapter && view === "reader") {
      const timer = setTimeout(() => {
        api.saveProgress(
          currentManga,
          currentChapter,
          currentPage,
          pages.length
        );
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [currentPage, currentManga, currentChapter, pages.length, view]);

  const loadLibrary = async () => {
    setLoadingLibrary(true);
    try {
      const response = await api.getLibrary();
      setLibrary(response.manga || []);
    } catch (error: any) {
      console.error("Failed to load library:", error);
      alert(`Failed to load library: ${error.message}`);
    } finally {
      setLoadingLibrary(false);
    }
  };

  const openManga = async (manga: Manga) => {
    try {
      const response = await api.getMangaChaptersList(manga.title);
      setChapters(response.chapters || []);
      setCurrentManga(manga.title);

      // Find last read chapter or use first
      const lastReadChapter = response.chapters.find(
        (ch: Chapter) => ch.last_page > 0
      );
      if (lastReadChapter) {
        await openChapter(
          manga.title,
          lastReadChapter.id,
          lastReadChapter.has_colored,
          lastReadChapter.last_page
        );
      } else if (response.chapters.length > 0) {
        await openChapter(
          manga.title,
          response.chapters[0].id,
          response.chapters[0].has_colored,
          0
        );
      }

      setView("reader");
    } catch (error: any) {
      console.error("Failed to open manga:", error);
      alert(`Failed to open manga: ${error.message}`);
    }
  };

  const openChapter = async (
    mangaTitle: string,
    chapterId: string,
    hasColored: boolean,
    startPage: number = 0
  ) => {
    setLoadingPages(true);
    try {
      const colored = hasColored && useColored;
      const response = await api.getChapterPages(
        mangaTitle,
        chapterId,
        colored
      );
      setPages(response.pages || []);
      setCurrentChapter(chapterId);
      setCurrentPage(startPage);

      // Load bookmarks
      const bookmarksResponse = await api.getBookmarks(mangaTitle, chapterId);
      setBookmarks(new Set(bookmarksResponse.bookmarks || []));
    } catch (error: any) {
      console.error("Failed to load chapter:", error);
      alert(`Failed to load chapter: ${error.message}`);
    } finally {
      setLoadingPages(false);
    }
  };

  const changeChapter = async (direction: "prev" | "next") => {
    if (!currentManga || !currentChapter) return;

    const currentIndex = chapters.findIndex((ch) => ch.id === currentChapter);
    const newIndex = direction === "prev" ? currentIndex - 1 : currentIndex + 1;

    if (newIndex >= 0 && newIndex < chapters.length) {
      const nextChapter = chapters[newIndex];
      await openChapter(currentManga, nextChapter.id, nextChapter.has_colored);
    }
  };

  const nextPage = () => {
    if (currentPage < pages.length - 1) {
      setCurrentPage(currentPage + 1);
    } else {
      changeChapter("next");
    }
  };

  const previousPage = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1);
    } else {
      changeChapter("prev");
    }
  };

  const jumpToPage = (pageIndex: number) => {
    setCurrentPage(pageIndex);
    setShowThumbnails(false);
  };

  const toggleBookmark = async () => {
    if (!currentManga || !currentChapter) return;

    try {
      await api.toggleBookmark(currentManga, currentChapter, currentPage);
      const newBookmarks = new Set(bookmarks);
      if (bookmarks.has(currentPage)) {
        newBookmarks.delete(currentPage);
      } else {
        newBookmarks.add(currentPage);
      }
      setBookmarks(newBookmarks);
    } catch (error: any) {
      console.error("Failed to toggle bookmark:", error);
    }
  };

  const toggleVersion = async () => {
    if (!currentManga || !currentChapter) return;

    const newColored = !useColored;
    setUseColored(newColored);

    try {
      const response = await api.getChapterPages(
        currentManga,
        currentChapter,
        newColored
      );
      setPages(response.pages || []);
    } catch (error: any) {
      console.error("Failed to switch version:", error);
      alert(`Failed to switch version: ${error.message}`);
    }
  };

  const colorizeChapter = async () => {
    if (!currentManga || !currentChapter) return;

    const confirmed = confirm(
      `Colorize this chapter? This will process all ${pages.length} pages and may take several minutes.`
    );

    if (!confirmed) return;

    setColorizing(true);

    try {
      // Create batch job for colorization
      const items = pages.map((page) => ({
        id: `${currentChapter}_page_${page.index}`,
        name: page.filename,
        path: page.url.replace("/api/library/page?path=", ""),
        manga_title: currentManga,
        chapter_id: currentChapter,
      }));

      const batchResponse = await api.createBatch({
        items,
        ink_threshold: 80,
        max_side: 1024,
        output_format: "png",
      });

      const batchId = batchResponse.batch_id;

      // Start batch processing
      await api.startBatch(batchId);

      // Poll for completion
      const checkProgress = async () => {
        const status = await api.getBatchStatus(batchId);

        if (status.status === "completed") {
          alert("Chapter colorization complete! Reloading...");
          // Reload chapter to show colored version
          await openChapter(currentManga, currentChapter, true);
          setUseColored(true);
          setColorizing(false);
        } else if (status.status === "failed") {
          alert(`Colorization failed: ${status.error || "Unknown error"}`);
          setColorizing(false);
        } else {
          // Continue polling
          setTimeout(checkProgress, 3000);
        }
      };

      checkProgress();
    } catch (error: any) {
      console.error("Failed to colorize chapter:", error);
      alert(`Failed to start colorization: ${error.message}`);
      setColorizing(false);
    }
  };

  const closeReader = () => {
    setView("library");
    setCurrentManga(null);
    setCurrentChapter(null);
    setPages([]);
    setCurrentPage(0);
    setShowThumbnails(false);
    setBookmarks(new Set());
    loadLibrary();
  };

  if (view === "library") {
    return (
      <div className="manga-reader">
        <div className="library-header">
          <h2>📚 Manga Library</h2>
          <button onClick={loadLibrary} className="btn-refresh">
            🔄 Refresh
          </button>
        </div>

        {loadingLibrary ? (
          <div className="loading">Loading library...</div>
        ) : library.length === 0 ? (
          <div className="empty-library">
            <div className="empty-icon">📖</div>
            <h3>No manga in library</h3>
            <p>Download manga from the Manga Browser tab</p>
          </div>
        ) : (
          <div className="library-grid">
            {library.map((manga) => (
              <div
                key={manga.title}
                className="library-card"
                onClick={() => openManga(manga)}
              >
                <div className="library-cover">
                  {manga.has_cover ? (
                    <img
                      src={`${
                        api.getClient().defaults.baseURL
                      }/api/library/page?path=${manga.path}/cover_thumb.jpg`}
                      alt={manga.title}
                    />
                  ) : (
                    <div className="library-cover-placeholder">📖</div>
                  )}
                  {manga.progress > 0 && (
                    <div className="library-progress-badge">
                      {manga.progress}/{manga.total_chapters}
                    </div>
                  )}
                </div>
                <div className="library-info">
                  <h3>{manga.title}</h3>
                  <p>{manga.total_chapters} chapters</p>
                  {manga.progress > 0 && (
                    <div className="library-progress-bar">
                      <div
                        className="library-progress-fill"
                        style={{
                          width: `${
                            (manga.progress / manga.total_chapters) * 100
                          }%`,
                        }}
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Reader View
  return (
    <div className="manga-reader reader-mode">
      <div className="reader-toolbar">
        <button onClick={closeReader} className="btn-back">
          ← Back to Library
        </button>

        <div className="reader-info">
          <span className="manga-title-small">{currentManga}</span>
          <span className="chapter-indicator">
            {currentChapter} - Page {currentPage + 1}/{pages.length}
          </span>
        </div>

        <div className="reader-controls">
          <select
            value={currentChapter || ""}
            onChange={(e) =>
              openChapter(
                currentManga!,
                e.target.value,
                chapters.find((ch) => ch.id === e.target.value)?.has_colored ||
                  false
              )
            }
            className="chapter-select"
          >
            {chapters.map((ch) => (
              <option key={ch.id} value={ch.id}>
                {ch.name} ({ch.pages} pages)
              </option>
            ))}
          </select>

          <button
            onClick={toggleVersion}
            className={`btn-version ${useColored ? "colored" : ""}`}
            disabled={
              !chapters.find((ch) => ch.id === currentChapter)?.has_colored
            }
            title={
              chapters.find((ch) => ch.id === currentChapter)?.has_colored
                ? "Toggle between colored and original"
                : "No colored version available"
            }
          >
            {useColored ? "🎨 Colored" : "📄 Original"}
          </button>

          <button
            onClick={colorizeChapter}
            className="btn-colorize"
            disabled={colorizing || loadingPages}
            title="Colorize this chapter using AI"
          >
            {colorizing ? "⏳ Colorizing..." : "🎨 Colorize Chapter"}
          </button>

          <select
            value={fitMode}
            onChange={(e) => setFitMode(e.target.value as any)}
            className="fit-select"
          >
            <option value="width">Fit Width</option>
            <option value="height">Fit Height</option>
            <option value="actual">Actual Size</option>
          </select>

          <button
            onClick={() => setShowThumbnails(!showThumbnails)}
            className="btn-thumbnails"
          >
            {showThumbnails ? "✕" : "🖼️"}
          </button>

          <button
            onClick={toggleBookmark}
            className={`btn-bookmark ${
              bookmarks.has(currentPage) ? "bookmarked" : ""
            }`}
          >
            {bookmarks.has(currentPage) ? "🔖" : "📑"}
          </button>
        </div>
      </div>

      {loadingPages ? (
        <div className="reader-loading">Loading pages...</div>
      ) : (
        <>
          <div className={`reader-viewer fit-${fitMode}`}>
            <button onClick={previousPage} className="nav-button nav-prev">
              ‹
            </button>

            {pages[currentPage] && (
              <img
                src={`${api.getClient().defaults.baseURL}${
                  pages[currentPage].url
                }`}
                alt={`Page ${currentPage + 1}`}
                className="reader-page"
              />
            )}

            <button onClick={nextPage} className="nav-button nav-next">
              ›
            </button>
          </div>

          {showThumbnails && (
            <div className="thumbnails-sidebar">
              <div className="thumbnails-header">
                <h3>Pages</h3>
                <button onClick={() => setShowThumbnails(false)}>✕</button>
              </div>
              <div className="thumbnails-grid">
                {pages.map((page, idx) => (
                  <div
                    key={idx}
                    className={`thumbnail ${
                      idx === currentPage ? "active" : ""
                    } ${bookmarks.has(idx) ? "bookmarked" : ""}`}
                    onClick={() => jumpToPage(idx)}
                  >
                    <img
                      src={`${api.getClient().defaults.baseURL}${page.url}`}
                      alt={`Page ${idx + 1}`}
                    />
                    <span className="thumbnail-number">{idx + 1}</span>
                    {bookmarks.has(idx) && (
                      <span className="bookmark-icon">🔖</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default MangaReader;
