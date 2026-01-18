import React, { useState, useEffect, useRef, useCallback } from "react";
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

interface LoadedChapter {
  chapterId: string;
  chapterName: string;
  pages: Page[];
  hasColored: boolean;
}

const MangaReader: React.FC = () => {
  const [view, setView] = useState<"library" | "reader">("library");
  const [library, setLibrary] = useState<Manga[]>([]);
  const [loadingLibrary, setLoadingLibrary] = useState(false);

  // Reader state
  const [currentManga, setCurrentManga] = useState<string | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loadedChapters, setLoadedChapters] = useState<LoadedChapter[]>([]);
  const [loadingChapters, setLoadingChapters] = useState<Set<string>>(
    new Set()
  );
  const [currentVisibleChapter, setCurrentVisibleChapter] = useState<
    string | null
  >(null);
  const [useColored, setUseColored] = useState(false);
  const [fitMode, setFitMode] = useState<"width" | "height" | "actual">(
    "width"
  );
  const [colorizing, setColorizing] = useState(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const chapterRefsMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const observerRef = useRef<IntersectionObserver | null>(null);

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

  // Setup Intersection Observer for visible chapter detection
  useEffect(() => {
    if (view !== "reader") return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const chapterId = entry.target.getAttribute("data-chapter-id");
            if (chapterId) {
              setCurrentVisibleChapter(chapterId);

              // Find the first visible page in this chapter
              const chapterElement = entry.target as HTMLElement;
              const pageElements =
                chapterElement.querySelectorAll(".page-container");

              if (pageElements.length > 0) {
                // Save progress for the visible chapter
                const chapter = loadedChapters.find(
                  (ch) => ch.chapterId === chapterId
                );
                if (chapter && currentManga) {
                  // Use first page as current page for progress tracking
                  api
                    .saveProgress(
                      currentManga,
                      chapterId,
                      0,
                      chapter.pages.length
                    )
                    .catch(console.error);
                }
              }
            }
          }
        });
      },
      {
        threshold: 0.3,
        rootMargin: "0px",
      }
    );

    // Observe all chapter sections
    chapterRefsMap.current.forEach((element) => {
      if (observerRef.current) {
        observerRef.current.observe(element);
      }
    });

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [view, loadedChapters, currentManga]);

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

      const startChapterIndex = lastReadChapter
        ? response.chapters.findIndex(
            (ch: Chapter) => ch.id === lastReadChapter.id
          )
        : 0;

      // Preload first 3 chapters starting from last read position
      await preloadChapters(startChapterIndex, 3);

      setView("reader");

      // Scroll to the starting chapter after a short delay
      setTimeout(() => {
        const startChapterId = lastReadChapter?.id || response.chapters[0]?.id;
        scrollToChapter(startChapterId);
      }, 100);
    } catch (error: any) {
      console.error("Failed to open manga:", error);
      alert(`Failed to open manga: ${error.message}`);
    }
  };

  const preloadChapters = async (startIndex: number, count: number = 3) => {
    const chaptersToLoad = chapters.slice(startIndex, startIndex + count);

    for (const chapter of chaptersToLoad) {
      if (
        loadingChapters.has(chapter.id) ||
        loadedChapters.some((lc) => lc.chapterId === chapter.id)
      ) {
        continue;
      }

      await loadChapter(chapter.id);
    }
  };

  const loadChapter = async (chapterId: string) => {
    // Mark as loading
    setLoadingChapters((prev) => {
      const next = new Set(prev);
      next.add(chapterId);
      return next;
    });

    try {
      const chapter = chapters.find((ch) => ch.id === chapterId);
      if (!chapter) return;

      const colored = chapter.has_colored && useColored;
      const response = await api.getChapterPages(
        currentManga!,
        chapterId,
        colored
      );

      const newChapter: LoadedChapter = {
        chapterId,
        chapterName: chapter.name,
        pages: response.pages || [],
        hasColored: response.has_colored,
      };

      setLoadedChapters((prev) => {
        // Check if already loaded
        if (prev.some((ch) => ch.chapterId === chapterId)) {
          return prev;
        }

        // Add and sort by chapter order
        const updated = [...prev, newChapter];
        return updated.sort(
          (a, b) =>
            chapters.findIndex((c) => c.id === a.chapterId) -
            chapters.findIndex((c) => c.id === b.chapterId)
        );
      });
    } catch (error: any) {
      console.error(`Failed to load chapter ${chapterId}:`, error);
    } finally {
      setLoadingChapters((prev) => {
        const next = new Set(prev);
        next.delete(chapterId);
        return next;
      });
    }
  };

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const container = e.currentTarget;
      const { scrollTop, scrollHeight, clientHeight } = container;

      // Load more at bottom (within 2000px)
      if (scrollHeight - scrollTop - clientHeight < 2000) {
        const lastLoadedChapter = loadedChapters[loadedChapters.length - 1];
        if (lastLoadedChapter) {
          const lastLoadedIndex = chapters.findIndex(
            (c) => c.id === lastLoadedChapter.chapterId
          );
          if (lastLoadedIndex >= 0 && lastLoadedIndex < chapters.length - 1) {
            const nextChapter = chapters[lastLoadedIndex + 1];
            if (
              !loadingChapters.has(nextChapter.id) &&
              !loadedChapters.some((ch) => ch.chapterId === nextChapter.id)
            ) {
              loadChapter(nextChapter.id);
            }
          }
        }
      }

      // Load more at top (within 2000px)
      if (scrollTop < 2000) {
        const firstLoadedChapter = loadedChapters[0];
        if (firstLoadedChapter) {
          const firstLoadedIndex = chapters.findIndex(
            (c) => c.id === firstLoadedChapter.chapterId
          );
          if (firstLoadedIndex > 0) {
            const prevChapter = chapters[firstLoadedIndex - 1];
            if (
              !loadingChapters.has(prevChapter.id) &&
              !loadedChapters.some((ch) => ch.chapterId === prevChapter.id)
            ) {
              loadChapter(prevChapter.id);
            }
          }
        }
      }
    },
    [loadedChapters, chapters, loadingChapters]
  );

  const scrollToChapter = (chapterId: string) => {
    const element = chapterRefsMap.current.get(chapterId);
    if (element && scrollContainerRef.current) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const colorizeLoadedChapters = async () => {
    if (loadedChapters.length === 0) return;

    const totalPages = loadedChapters.reduce(
      (sum, ch) => sum + ch.pages.length,
      0
    );

    const confirmed = confirm(
      `Colorize all loaded chapters (${loadedChapters.length} chapters)? ` +
        `This will process ${totalPages} pages and may take a while.`
    );

    if (!confirmed) return;

    setColorizing(true);

    try {
      // Create batch items for all loaded chapters with proper path extraction
      const allItems = loadedChapters.flatMap((chapter) =>
        chapter.pages.map((page) => {
          // Extract path from URL query parameter properly
          const params = new URLSearchParams(page.url.split("?")[1]);
          return {
            id: `${chapter.chapterId}_page_${page.index}`,
            name: page.filename,
            path: params.get("path") || "",
            type: "file",
            manga_title: currentManga,
            chapter_id: chapter.chapterId,
          };
        })
      );

      const batchResponse = await api.createBatch({
        items: allItems,
        ink_threshold: 80,
        max_side: 1024,
        output_format: "png",
      });

      const batchId = batchResponse.batch_id;

      // Start batch processing
      await api.startBatch(batchId);

      // Poll for completion
      const checkProgress = async () => {
        try {
          const status = await api.getBatchStatus(batchId);

          if (status.status === "completed") {
            alert("Colorization complete! Reloading chapters...");
            // Reload all loaded chapters with colored version
            setUseColored(true);
            setLoadedChapters([]);
            const firstChapterId = loadedChapters[0].chapterId;
            const startIndex = chapters.findIndex(
              (ch) => ch.id === firstChapterId
            );
            await preloadChapters(startIndex, loadedChapters.length);
            setColorizing(false);
          } else if (status.status === "failed") {
            alert(`Colorization failed: ${status.error || "Unknown error"}`);
            setColorizing(false);
          } else {
            // Continue polling
            setTimeout(checkProgress, 3000);
          }
        } catch (error: any) {
          console.error("Failed to check colorization progress:", error);
          setColorizing(false);
        }
      };

      checkProgress();
    } catch (error: any) {
      console.error("Failed to colorize chapters:", error);
      alert(`Failed to start colorization: ${error.message}`);
      setColorizing(false);
    }
  };

  const toggleVersion = async () => {
    const newColored = !useColored;
    setUseColored(newColored);

    // Reload all loaded chapters with new version
    const chaptersToReload = [...loadedChapters];
    setLoadedChapters([]);

    for (const chapter of chaptersToReload) {
      try {
        const response = await api.getChapterPages(
          currentManga!,
          chapter.chapterId,
          newColored
        );

        setLoadedChapters((prev) => {
          const updated = [
            ...prev,
            {
              ...chapter,
              pages: response.pages || [],
            },
          ];
          return updated.sort(
            (a, b) =>
              chapters.findIndex((c) => c.id === a.chapterId) -
              chapters.findIndex((c) => c.id === b.chapterId)
          );
        });
      } catch (error: any) {
        console.error(`Failed to reload chapter ${chapter.chapterId}:`, error);
      }
    }
  };

  const closeReader = () => {
    setView("library");
    setCurrentManga(null);
    setChapters([]);
    setLoadedChapters([]);
    setLoadingChapters(new Set());
    setCurrentVisibleChapter(null);
    chapterRefsMap.current.clear();
    loadLibrary();
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (view !== "reader") return;

      if (e.key === "Escape") {
        closeReader();
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [view]);

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

  // Infinite Scroll Reader View
  return (
    <div className="manga-reader reader-mode">
      <div className="reader-toolbar">
        <button onClick={closeReader} className="btn-back">
          ← Back to Library
        </button>

        <div className="reader-info">
          <span className="manga-title-small">{currentManga}</span>
          {currentVisibleChapter && (
            <span className="chapter-indicator">
              📖{" "}
              {chapters.find((ch) => ch.id === currentVisibleChapter)?.name ||
                currentVisibleChapter}
            </span>
          )}
        </div>

        <div className="reader-controls">
          <select
            value={currentVisibleChapter || ""}
            onChange={(e) => scrollToChapter(e.target.value)}
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
            disabled={!loadedChapters.some((ch) => ch.hasColored)}
            title={
              loadedChapters.some((ch) => ch.hasColored)
                ? "Toggle between colored and original"
                : "No colored version available"
            }
          >
            {useColored ? "🎨 Colored" : "📄 Original"}
          </button>

          <button
            onClick={colorizeLoadedChapters}
            className="btn-colorize"
            disabled={colorizing || loadedChapters.length === 0}
            title="Colorize all loaded chapters using AI"
          >
            {colorizing ? "⏳ Colorizing..." : "🎨 Colorize Loaded Chapters"}
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
        </div>
      </div>

      <div
        className="reader-infinite-scroll"
        onScroll={handleScroll}
        ref={scrollContainerRef}
      >
        {loadedChapters.map((chapter) => (
          <div
            key={chapter.chapterId}
            className="chapter-section"
            data-chapter-id={chapter.chapterId}
            ref={(el) => {
              if (el) {
                chapterRefsMap.current.set(chapter.chapterId, el);
              }
            }}
          >
            {/* Subtle chapter marker */}
            <div className="chapter-marker">
              <span className="chapter-name">{chapter.chapterName}</span>
              <span className="chapter-page-count">
                {chapter.pages.length} pages
              </span>
            </div>

            {/* Chapter pages */}
            <div className="chapter-pages">
              {chapter.pages.map((page) => (
                <div key={page.index} className="page-container">
                  <img
                    src={`${api.getClient().defaults.baseURL}${page.url}`}
                    alt={`${chapter.chapterName} - Page ${page.index + 1}`}
                    className={`page-image fit-${fitMode}`}
                    loading="lazy"
                  />
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Loading indicator for next chapters */}
        {loadingChapters.size > 0 && (
          <div className="loading-chapters">
            <div className="spinner"></div>
            <p>Loading more chapters...</p>
          </div>
        )}

        {/* End of manga indicator */}
        {loadedChapters.length > 0 &&
          loadedChapters.length === chapters.length &&
          loadingChapters.size === 0 && (
            <div className="end-of-manga">
              <p>📚 End of manga</p>
            </div>
          )}
      </div>
    </div>
  );
};

export default MangaReader;
