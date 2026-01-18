import React, { useState } from "react";
import "./ChapterSelectionDialog.css";

interface Chapter {
  id: string;
  name: string;
  pages: number;
  hasColored: boolean;
}

interface ChapterSelectionDialogProps {
  chapters: Chapter[];
  onConfirm: (selectedChapterIds: string[]) => void;
  onCancel: () => void;
}

const ChapterSelectionDialog: React.FC<ChapterSelectionDialogProps> = ({
  chapters,
  onConfirm,
  onCancel,
}) => {
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(
    new Set()
  );

  const toggleChapter = (chapterId: string) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(chapterId)) {
        next.delete(chapterId);
      } else {
        next.add(chapterId);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedChapters(new Set(chapters.map((ch) => ch.id)));
  };

  const deselectAll = () => {
    setSelectedChapters(new Set());
  };

  const totalPages = chapters
    .filter((ch) => selectedChapters.has(ch.id))
    .reduce((sum, ch) => sum + ch.pages, 0);

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div
        className="dialog-content chapter-selection-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header">
          <h2>Select Chapters to Colorize</h2>
          <button onClick={onCancel} className="dialog-close">
            ✕
          </button>
        </div>

        <div className="dialog-body">
          <div className="selection-controls">
            <button onClick={selectAll} className="btn-secondary">
              Select All
            </button>
            <button onClick={deselectAll} className="btn-secondary">
              Deselect All
            </button>
            <span className="selection-info">
              {selectedChapters.size} chapters selected ({totalPages} pages)
            </span>
          </div>

          <div className="chapter-list">
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                className={`chapter-item ${
                  selectedChapters.has(chapter.id) ? "selected" : ""
                }`}
                onClick={() => toggleChapter(chapter.id)}
              >
                <input
                  type="checkbox"
                  checked={selectedChapters.has(chapter.id)}
                  onChange={() => {}}
                />
                <div className="chapter-info">
                  <span className="chapter-name">{chapter.name}</span>
                  <span className="chapter-pages">{chapter.pages} pages</span>
                </div>
                {chapter.hasColored && (
                  <span className="chapter-badge colored">
                    Already Colored
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="dialog-footer">
          <button onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(Array.from(selectedChapters))}
            className="btn-primary"
            disabled={selectedChapters.size === 0}
          >
            Colorize {selectedChapters.size} Chapter
            {selectedChapters.size !== 1 ? "s" : ""}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChapterSelectionDialog;
