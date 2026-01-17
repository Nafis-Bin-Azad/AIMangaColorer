import React, { useState, useEffect } from 'react';
import './MangaBrowser.css';
import api from '../services/api';

interface MangaResult {
  id: string;
  title: string;
  url: string;
  cover_url: string;
  latest_chapter: string;
  status: string;
}

interface MangaDetails {
  id: string;
  title: string;
  description: string;
  cover_url: string;
  author: string;
  status: string;
  genres: string[];
  rating: number;
}

interface Chapter {
  id: string;
  number: string;
  title: string;
  date: string;
  url: string;
}

interface Download {
  id: string;
  manga_title: string;
  status: string;
  progress: number;
  message: string;
}

const MangaBrowser: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<MangaResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedManga, setSelectedManga] = useState<MangaDetails | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());
  const [downloads, setDownloads] = useState<Download[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [loadingChapters, setLoadingChapters] = useState(false);

  // Initialize API service
  useEffect(() => {
    api.initialize();
  }, []);

  // Poll for download updates
  useEffect(() => {
    const interval = setInterval(async () => {
      if (downloads.length > 0) {
        try {
          const updatedDownloads = await Promise.all(
            downloads.map(async (download) => {
              if (download.status === 'downloading' || download.status === 'queued') {
                const status = await api.getDownloadStatus(download.id);
                return status;
              }
              return download;
            })
          );
          setDownloads(updatedDownloads);
        } catch (error) {
          console.error('Failed to update downloads:', error);
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [downloads]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const response = await api.searchManga(searchQuery);
      setSearchResults(response.results || []);
    } catch (error: any) {
      console.error('Search failed:', error);
      alert(`Search failed: ${error.message}`);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const openMangaDetails = async (manga: MangaResult) => {
    setLoadingChapters(true);
    setShowModal(true);
    setSelectedChapters(new Set());

    try {
      // Get details
      const details = await api.getMangaDetails(manga.id);
      setSelectedManga(details);

      // Get chapters
      const chaptersResponse = await api.getMangaChapters(manga.id);
      setChapters(chaptersResponse.chapters || []);
    } catch (error: any) {
      console.error('Failed to load manga details:', error);
      alert(`Failed to load details: ${error.message}`);
      setShowModal(false);
    } finally {
      setLoadingChapters(false);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedManga(null);
    setChapters([]);
    setSelectedChapters(new Set());
  };

  const toggleChapter = (chapterId: string) => {
    const newSelected = new Set(selectedChapters);
    if (newSelected.has(chapterId)) {
      newSelected.delete(chapterId);
    } else {
      newSelected.add(chapterId);
    }
    setSelectedChapters(newSelected);
  };

  const selectAllChapters = () => {
    setSelectedChapters(new Set(chapters.map((ch) => ch.id)));
  };

  const deselectAllChapters = () => {
    setSelectedChapters(new Set());
  };

  const downloadSelected = async () => {
    if (selectedChapters.size === 0 || !selectedManga) {
      alert('Please select chapters to download');
      return;
    }

    try {
      const response = await api.downloadChapters({
        manga_id: selectedManga.id,
        manga_title: selectedManga.title,
        chapters: Array.from(selectedChapters),
      });

      const newDownload: Download = {
        id: response.download_id,
        manga_title: selectedManga.title,
        status: 'queued',
        progress: 0,
        message: 'Starting download...',
      };

      setDownloads([...downloads, newDownload]);
      closeModal();
      alert(`Download started! ${selectedChapters.size} chapters queued.`);
    } catch (error: any) {
      console.error('Download failed:', error);
      alert(`Download failed: ${error.message}`);
    }
  };

  const cancelDownload = async (downloadId: string) => {
    try {
      await api.cancelDownload(downloadId);
      setDownloads(downloads.filter((d) => d.id !== downloadId));
    } catch (error: any) {
      console.error('Failed to cancel download:', error);
    }
  };

  return (
    <div className="manga-browser">
      <div className="browser-header">
        <h2>📚 Manga Browser</h2>
        <p>Search and download manga from MangaFire</p>
      </div>

      <div className="search-section">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search manga..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="search-input"
          />
          <button
            onClick={handleSearch}
            disabled={isSearching || !searchQuery.trim()}
            className="btn-search"
          >
            {isSearching ? '⏳ Searching...' : '🔍 Search'}
          </button>
        </div>
      </div>

      {downloads.length > 0 && (
        <div className="downloads-section">
          <h3>📥 Active Downloads</h3>
          <div className="downloads-list">
            {downloads.map((download) => (
              <div key={download.id} className="download-item">
                <div className="download-info">
                  <h4>{download.manga_title}</h4>
                  <p>{download.message}</p>
                  <div className="download-progress-bar">
                    <div
                      className="download-progress-fill"
                      style={{ width: `${download.progress}%` }}
                    />
                  </div>
                  <span className="download-percentage">{download.progress}%</span>
                </div>
                {download.status === 'downloading' && (
                  <button
                    onClick={() => cancelDownload(download.id)}
                    className="btn-cancel-download"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="results-section">
          <h3>Search Results ({searchResults.length})</h3>
          <div className="manga-grid">
            {searchResults.map((manga) => (
              <div
                key={manga.id}
                className="manga-card"
                onClick={() => openMangaDetails(manga)}
              >
                <div className="manga-cover">
                  {manga.cover_url ? (
                    <img src={manga.cover_url} alt={manga.title} />
                  ) : (
                    <div className="manga-cover-placeholder">📖</div>
                  )}
                </div>
                <div className="manga-info">
                  <h4>{manga.title}</h4>
                  <p className="manga-status">{manga.status}</p>
                  {manga.latest_chapter && (
                    <p className="manga-chapter">Latest: {manga.latest_chapter}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showModal && selectedManga && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>
              ✕
            </button>

            <div className="modal-body">
              <div className="manga-details-header">
                <div className="manga-details-cover">
                  {selectedManga.cover_url ? (
                    <img src={selectedManga.cover_url} alt={selectedManga.title} />
                  ) : (
                    <div className="manga-cover-placeholder">📖</div>
                  )}
                </div>
                <div className="manga-details-info">
                  <h2>{selectedManga.title}</h2>
                  <p className="manga-author">
                    <strong>Author:</strong> {selectedManga.author}
                  </p>
                  <p className="manga-status-detail">
                    <strong>Status:</strong> {selectedManga.status}
                  </p>
                  {selectedManga.genres.length > 0 && (
                    <div className="manga-genres">
                      {selectedManga.genres.map((genre, idx) => (
                        <span key={idx} className="genre-tag">
                          {genre}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="manga-description">{selectedManga.description}</p>
                </div>
              </div>

              <div className="chapters-section">
                <div className="chapters-header">
                  <h3>Chapters ({chapters.length})</h3>
                  <div className="chapters-actions">
                    <button onClick={selectAllChapters} className="btn-select">
                      Select All
                    </button>
                    <button onClick={deselectAllChapters} className="btn-select">
                      Deselect All
                    </button>
                    <button
                      onClick={downloadSelected}
                      disabled={selectedChapters.size === 0}
                      className="btn-download"
                    >
                      📥 Download Selected ({selectedChapters.size})
                    </button>
                  </div>
                </div>

                {loadingChapters ? (
                  <div className="loading">Loading chapters...</div>
                ) : (
                  <div className="chapters-list">
                    {chapters.map((chapter) => (
                      <label key={chapter.id} className="chapter-item">
                        <input
                          type="checkbox"
                          checked={selectedChapters.has(chapter.id)}
                          onChange={() => toggleChapter(chapter.id)}
                        />
                        <span className="chapter-number">Ch. {chapter.number}</span>
                        <span className="chapter-title">{chapter.title}</span>
                        <span className="chapter-date">{chapter.date}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MangaBrowser;
