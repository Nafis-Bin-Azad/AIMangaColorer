import { useState, useEffect } from 'react'
import { apiService } from '../services/api'
import './SingleImage.css'

export default function SingleImage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')
  const [resultImage, setResultImage] = useState<string | null>(null)
  const [inkThreshold, setInkThreshold] = useState(80)
  const [maxSide, setMaxSide] = useState(1024)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Initialize API service
    apiService.initialize()
  }, [])

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setResultImage(null)
      setError(null)
      
      // Create preview
      const reader = new FileReader()
      reader.onload = (e) => {
        setPreviewUrl(e.target?.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleColorize = async () => {
    if (!selectedFile) return

    setIsProcessing(true)
    setProgress(0)
    setStatus('Uploading image...')
    setError(null)

    try {
      // Create form data
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('ink_threshold', inkThreshold.toString())
      formData.append('max_side', maxSide.toString())

      // Call API
      setStatus('Processing with MCV2 engine...')
      const result = await apiService.colorizeImage(formData, (uploadProgress) => {
        setProgress(uploadProgress)
        setStatus(`Uploading... ${uploadProgress}%`)
      })

      if (result.success) {
        setResultImage(result.image)
        setStatus('Colorization complete!')
        setProgress(100)
      } else {
        throw new Error('Colorization failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred')
      setStatus('Failed')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleDownload = () => {
    if (!resultImage) return

    // Create download link
    const link = document.createElement('a')
    link.href = resultImage
    link.download = `${selectedFile?.name.replace(/\.[^/.]+$/, '')}_colored.png`
    link.click()
  }

  return (
    <div className="single-image-container">
      <div className="card">
        <div className="header-section">
          <h2>Single Image Colorization</h2>
          <p className="status-text">
            Upload a manga page to colorize it using the Manga Colorization v2 engine
          </p>
        </div>

        <div className="controls-section">
          <div className="file-input-wrapper">
            <input
              type="file"
              id="file-input"
              accept="image/*"
              onChange={handleFileSelect}
              disabled={isProcessing}
            />
            <label htmlFor="file-input" className="button button-secondary">
              📁 Choose Image
            </label>
            {selectedFile && <span className="file-name">{selectedFile.name}</span>}
          </div>

          {selectedFile && !isProcessing && (
            <div className="settings-section">
              <h3>Settings</h3>
              <div className="setting-row">
                <label>
                  Ink Threshold: {inkThreshold}
                  <span className="setting-desc">
                    (Lower = preserve more dark pixels)
                  </span>
                </label>
                <input
                  type="range"
                  min="40"
                  max="120"
                  value={inkThreshold}
                  onChange={(e) => setInkThreshold(parseInt(e.target.value))}
                  className="slider"
                />
              </div>
              <div className="setting-row">
                <label>
                  Max Side: {maxSide}px
                  <span className="setting-desc">
                    (Processing resolution)
                  </span>
                </label>
                <input
                  type="range"
                  min="512"
                  max="1536"
                  step="128"
                  value={maxSide}
                  onChange={(e) => setMaxSide(parseInt(e.target.value))}
                  className="slider"
                />
              </div>
            </div>
          )}

          {selectedFile && !isProcessing && (
            <button
              className="button"
              onClick={handleColorize}
              style={{ marginTop: '1rem', width: '100%' }}
            >
              🎨 Colorize
            </button>
          )}
        </div>

        {isProcessing && (
          <div className="progress-section">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="status-text">{status}</p>
          </div>
        )}

        {error && (
          <div className="error-section">
            <p className="status-text error">❌ {error}</p>
          </div>
        )}

        {(previewUrl || resultImage) && (
          <div className="images-section">
            <div className="image-comparison">
              {previewUrl && (
                <div className="image-box">
                  <h3>Original</h3>
                  <img src={previewUrl} alt="Original" />
                </div>
              )}
              {resultImage && (
                <div className="image-box">
                  <h3>Colorized</h3>
                  <img src={resultImage} alt="Colorized" />
                  <button
                    className="button"
                    onClick={handleDownload}
                    style={{ marginTop: '1rem' }}
                  >
                    💾 Download
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
