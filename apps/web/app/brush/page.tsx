"use client";
import { useState, useRef, useEffect, useCallback } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";

interface BrushSettings {
  size: number;
  opacity: number;
}

interface SmartEditResult {
  imageUrl: string;
  caption: string;
  facts: string[];
  cta: string;
}

export default function BrushEditor() {
  // Image and canvas refs
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  
  // State management
  const [sourceImage, setSourceImage] = useState<string>("");
  const [isDrawing, setIsDrawing] = useState(false);
  const [brushSettings, setBrushSettings] = useState<BrushSettings>({ size: 20, opacity: 0.7 });
  const [editInstruction, setEditInstruction] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<SmartEditResult | null>(null);
  const [showMask, setShowMask] = useState(true);
  
  // Canvas dimensions
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 });

  // Initialize canvas when image loads
  const handleImageLoad = useCallback(() => {
    const img = imageRef.current;
    const canvas = canvasRef.current;
    const maskCanvas = maskCanvasRef.current;
    
    if (!img || !canvas || !maskCanvas) {
      console.log('Missing elements:', { img: !!img, canvas: !!canvas, maskCanvas: !!maskCanvas });
      return;
    }

    console.log('Image loaded:', img.naturalWidth, 'x', img.naturalHeight);

    // Set canvas size to match image
    const aspectRatio = img.naturalHeight / img.naturalWidth;
    const maxWidth = 800;
    const width = Math.min(maxWidth, img.naturalWidth);
    const height = width * aspectRatio;
    
    console.log('Canvas size:', width, 'x', height);
    
    setCanvasSize({ width, height });
    
    canvas.width = width;
    canvas.height = height;
    maskCanvas.width = width;
    maskCanvas.height = height;
    
    // Draw the source image
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.globalCompositeOperation = 'source-over';
      ctx.drawImage(img, 0, 0, width, height);
      console.log('Image drawn to canvas');
    }
    
    // Clear mask canvas (transparent background)
    const maskCtx = maskCanvas.getContext('2d');
    if (maskCtx) {
      maskCtx.clearRect(0, 0, width, height);
      console.log('Mask canvas cleared');
    }
  }, []);

  // Get mouse position relative to canvas
  const getMousePos = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  // Drawing functions
  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    const pos = getMousePos(e);
    drawBrushStroke(pos.x, pos.y);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const pos = getMousePos(e);
    drawBrushStroke(pos.x, pos.y);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const drawBrushStroke = (x: number, y: number) => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;
    
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;
    
    // Set up brush properties
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = `rgba(255, 255, 255, ${brushSettings.opacity})`;
    
    // Draw circular brush stroke
    ctx.beginPath();
    ctx.arc(x, y, brushSettings.size / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Immediately update the visual overlay to show the change
    updateVisualOverlay();
  };

  const updateVisualOverlay = () => {
    const canvas = canvasRef.current;
    const maskCanvas = maskCanvasRef.current;
    const img = imageRef.current;
    
    if (!canvas || !maskCanvas || !img) return;
    
    const ctx = canvas.getContext('2d');
    const maskCtx = maskCanvas.getContext('2d');
    
    if (!ctx || !maskCtx) return;
    
    // Redraw original image first
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    
    if (showMask) {
      // Overlay the mask with a colored tint
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = 'rgba(59, 130, 246, 0.3)'; // Blue overlay
      
      // Get mask data and apply overlay where mask exists
      const maskData = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
      const overlayCanvas = document.createElement('canvas');
      overlayCanvas.width = canvas.width;
      overlayCanvas.height = canvas.height;
      const overlayCtx = overlayCanvas.getContext('2d');
      
      if (overlayCtx) {
        const overlayImageData = overlayCtx.createImageData(canvas.width, canvas.height);
        
        // Convert white mask areas to blue overlay
        for (let i = 0; i < maskData.data.length; i += 4) {
          const alpha = maskData.data[i]; // Red channel represents mask strength
          if (alpha > 0) {
            overlayImageData.data[i] = 59;     // Blue R
            overlayImageData.data[i + 1] = 130; // Blue G
            overlayImageData.data[i + 2] = 246; // Blue B
            overlayImageData.data[i + 3] = alpha * 0.3; // Semi-transparent
          }
        }
        
        overlayCtx.putImageData(overlayImageData, 0, 0);
        ctx.drawImage(overlayCanvas, 0, 0);
      }
    }
  };

  // Clear the mask
  const clearMask = () => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;
    
    const ctx = maskCanvas.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
      updateVisualOverlay();
    }
  };

  // Convert mask to base64
  const getMaskBase64 = (): string => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return "";
    
    return maskCanvas.toDataURL('image/png').split(',')[1];
  };

  // Process the smart edit
  const processSmartEdit = async () => {
    if (!sourceImage || !editInstruction.trim()) {
      alert("Please provide both an image and editing instructions");
      return;
    }

    const maskData = getMaskBase64();
    if (!maskData) {
      alert("Please paint some areas to edit first");
      return;
    }

    setIsProcessing(true);
    setResult(null);

    try {
      const response = await fetch(`${apiBase}/nlp/compose`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: editInstruction,
          composition_type: "smart_edit",
          room_image_gcs: sourceImage,
          mask_data: maskData,
          edit_instruction: editInstruction,
          org_id: 1,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResult({
        imageUrl: data.image_url,
        caption: data.caption,
        facts: data.facts,
        cta: data.cta,
      });
    } catch (error) {
      console.error("Error processing smart edit:", error);
      alert("Failed to process smart edit. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Load sample image for testing
  const loadSampleImage = () => {
    setSourceImage("https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&h=600&fit=crop");
  };

  // Re-initialize when source image changes
  useEffect(() => {
    if (sourceImage && imageRef.current) {
      // Clear existing canvas
      const canvas = canvasRef.current;
      const maskCanvas = maskCanvasRef.current;
      
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
      
      if (maskCanvas) {
        const maskCtx = maskCanvas.getContext('2d');
        if (maskCtx) {
          maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
        }
      }
    }
  }, [sourceImage]);

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Smart Brush Editor</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Panel */}
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-3">Image Source</h2>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Enter image URL or GCS URI"
                value={sourceImage}
                onChange={(e) => setSourceImage(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
              />
              <button
                onClick={loadSampleImage}
                className="w-full px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
              >
                Load Sample Image
              </button>
            </div>
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-3">Brush Settings</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Size: {brushSettings.size}px
                </label>
                <input
                  type="range"
                  min="5"
                  max="100"
                  value={brushSettings.size}
                  onChange={(e) => setBrushSettings({...brushSettings, size: parseInt(e.target.value)})}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Opacity: {Math.round(brushSettings.opacity * 100)}%
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.1"
                  value={brushSettings.opacity}
                  onChange={(e) => setBrushSettings({...brushSettings, opacity: parseFloat(e.target.value)})}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-3">Tools</h2>
            <div className="space-y-2">
              <button
                onClick={clearMask}
                className="w-full px-3 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200"
              >
                Clear Mask
              </button>
              <button
                onClick={() => setShowMask(!showMask)}
                className="w-full px-3 py-2 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200"
              >
                {showMask ? "Hide Mask" : "Show Mask"}
              </button>
            </div>
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-3">Edit Instructions</h2>
            <textarea
              placeholder="Describe what you want to do with the selected areas. E.g., 'Remove the furniture', 'Make the lighting brighter', 'Change the wall color to blue'"
              value={editInstruction}
              onChange={(e) => setEditInstruction(e.target.value)}
              className="w-full h-24 px-3 py-2 border rounded-md resize-none"
            />
            <button
              onClick={processSmartEdit}
              disabled={isProcessing || !sourceImage || !editInstruction.trim()}
              className="w-full mt-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? "Processing..." : "Apply Smart Edit"}
            </button>
          </div>
        </div>

        {/* Canvas Area */}
        <div className="lg:col-span-2">
          <div className="relative bg-gray-100 rounded-lg overflow-hidden">
            {sourceImage && (
              <>
                <img
                  ref={imageRef}
                  src={sourceImage}
                  alt="Source"
                  onLoad={handleImageLoad}
                  onError={(e) => console.error('Image load error:', e)}
                  className="hidden"
                  crossOrigin="anonymous"
                />
                <canvas
                  ref={canvasRef}
                  width={canvasSize.width}
                  height={canvasSize.height}
                  onMouseDown={startDrawing}
                  onMouseMove={draw}
                  onMouseUp={stopDrawing}
                  onMouseLeave={stopDrawing}
                  className="block cursor-crosshair max-w-full h-auto"
                  style={{ maxHeight: '70vh' }}
                />
                <canvas
                  ref={maskCanvasRef}
                  width={canvasSize.width}
                  height={canvasSize.height}
                  className="hidden"
                />
              </>
            )}
            {!sourceImage && (
              <div className="flex items-center justify-center h-96 text-gray-500">
                Load an image to start editing
              </div>
            )}
          </div>

          {/* Instructions */}
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-medium text-blue-900 mb-2">How to use:</h3>
            <ol className="text-sm text-blue-800 space-y-1">
              <li>1. Load an image by entering a URL or clicking "Load Sample Image"</li>
              <li>2. Adjust brush size and opacity in the left panel</li>
              <li>3. Paint over the areas you want to edit (blue highlight shows selection)</li>
              <li>4. Enter your editing instructions (e.g., "remove furniture", "brighten lighting")</li>
              <li>5. Click "Apply Smart Edit" to process with AI</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="mt-8 border rounded-lg p-6 bg-gray-50">
          <h2 className="text-2xl font-semibold mb-4">Smart Edit Result</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <img src={result.imageUrl} alt="Edited Result" className="w-full rounded shadow" />
            </div>
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-lg">Caption:</h3>
                <p className="text-gray-800">{result.caption}</p>
              </div>
              <div>
                <h3 className="font-semibold text-lg">Key Facts:</h3>
                <ul className="list-disc ml-6 text-gray-800">
                  {result.facts.map((fact, i) => (
                    <li key={i}>{fact}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-lg">Call to Action:</h3>
                <p className="text-blue-700 font-medium">{result.cta}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}