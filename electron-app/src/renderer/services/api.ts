import axios, { AxiosInstance } from "axios";

class ApiService {
  private client: AxiosInstance | null = null;
  private baseUrl: string = "";

  async initialize() {
    if (window.electronAPI) {
      this.baseUrl = await window.electronAPI.getApiUrl();
      this.client = axios.create({
        baseURL: this.baseUrl,
        timeout: 300000, // 5 minutes for long operations
      });

      // Verify connection
      try {
        await this.healthCheck();
        console.log("✅ API connected:", this.baseUrl);
      } catch (error) {
        console.error("❌ API connection failed:", error);
        throw new Error("Failed to connect to backend API");
      }
    }
  }

  getClient(): AxiosInstance {
    if (!this.client) {
      throw new Error("API service not initialized");
    }
    return this.client;
  }

  // Single Image API
  async colorizeImage(
    formData: FormData,
    onProgress?: (progress: number) => void
  ) {
    const response = await this.getClient().post("/api/colorize", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
    return response.data;
  }

  // Batch Processing API
  async createBatch(data: {
    items: any[];
    ink_threshold: number;
    max_side: number;
    output_format: string;
  }) {
    const response = await this.getClient().post("/api/batch/create", data);
    return response.data;
  }

  async startBatch(batchId: string) {
    const response = await this.getClient().post(`/api/batch/${batchId}/start`);
    return response.data;
  }

  async getBatchStatus(batchId: string) {
    const response = await this.getClient().get(`/api/batch/${batchId}/status`);
    return response.data;
  }

  async getBatchResults(batchId: string) {
    const response = await this.getClient().get(
      `/api/batch/${batchId}/results`
    );
    return response.data;
  }

  async cancelBatch(batchId: string) {
    const response = await this.getClient().post(
      `/api/batch/${batchId}/cancel`
    );
    return response.data;
  }

  async listBatches() {
    const response = await this.getClient().get("/api/batch/");
    return response.data;
  }

  // Manga Browser API
  async searchManga(query: string, page: number = 1, limit: number = 20) {
    const response = await this.getClient().get("/api/manga/search", {
      params: { q: query, page, limit },
    });
    return response.data;
  }

  async getMangaDetails(mangaId: string) {
    const response = await this.getClient().get("/api/manga/details", {
      params: { manga_id: mangaId },
    });
    return response.data;
  }

  async getMangaChapters(mangaId: string) {
    const response = await this.getClient().get("/api/manga/chapters", {
      params: { manga_id: mangaId },
    });
    return response.data;
  }

  async downloadChapters(data: {
    manga_id: string;
    manga_title: string;
    chapters: string[];
  }) {
    const response = await this.getClient().post("/api/manga/download", data);
    return response.data;
  }

  async getDownloadStatus(downloadId: string) {
    const response = await this.getClient().get(
      `/api/manga/downloads/${downloadId}/status`
    );
    return response.data;
  }

  async cancelDownload(downloadId: string) {
    const response = await this.getClient().post(
      `/api/manga/downloads/${downloadId}/cancel`
    );
    return response.data;
  }

  async listDownloads() {
    const response = await this.getClient().get("/api/manga/downloads");
    return response.data;
  }

  // Manga Reader/Library API
  async getLibrary() {
    const response = await this.getClient().get("/api/library/manga");
    return response.data;
  }

  async getMangaChaptersList(mangaTitle: string) {
    const response = await this.getClient().get(
      `/api/library/manga/${encodeURIComponent(mangaTitle)}/chapters`
    );
    return response.data;
  }

  async getChapterPages(
    mangaTitle: string,
    chapterId: string,
    colored: boolean = false
  ) {
    const response = await this.getClient().get(
      `/api/library/manga/${encodeURIComponent(
        mangaTitle
      )}/chapter/${encodeURIComponent(chapterId)}/pages`,
      { params: { colored } }
    );
    return response.data;
  }

  async saveProgress(
    manga: string,
    chapter: string,
    page: number,
    totalPages: number = 0
  ) {
    const response = await this.getClient().post("/api/library/progress", {
      manga,
      chapter,
      page,
      total_pages: totalPages,
    });
    return response.data;
  }

  async getProgress(mangaTitle: string) {
    const response = await this.getClient().get(
      `/api/library/progress/${encodeURIComponent(mangaTitle)}`
    );
    return response.data;
  }

  async toggleBookmark(manga: string, chapter: string, page: number) {
    const response = await this.getClient().post("/api/library/bookmark", {
      manga,
      chapter,
      page,
    });
    return response.data;
  }

  async getBookmarks(mangaTitle: string, chapter?: string) {
    const url = `/api/library/bookmarks/${encodeURIComponent(mangaTitle)}`;
    const response = await this.getClient().get(url, {
      params: chapter ? { chapter } : {},
    });
    return response.data;
  }

  async getHistory(limit: number = 20) {
    const response = await this.getClient().get("/api/library/history", {
      params: { limit },
    });
    return response.data;
  }

  async getLibraryStats() {
    const response = await this.getClient().get("/api/library/stats");
    return response.data;
  }

  // Health check
  async healthCheck() {
    const response = await this.getClient().get("/health");
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
