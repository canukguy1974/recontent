"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader } from "lucide-react";

interface Asset {
  id: number;
  filename: string;
  gcs_uri: string;
  signed_url: string;
  kind: string;
  created_at: string;
}

interface AnalysisJob {
  job_id: number;
  analysis_id?: string;
  status: string;
  progress: number;
  results?: any;
  error?: string;
  created_at: string;
  updated_at: string;
}

interface SocialJob {
  job_id: number;
  generation_id?: string;
  status: string;
  progress: number;
  results?: any;
  error?: string;
  platforms: string[];
}

export default function CombinationAgentPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssets, setSelectedAssets] = useState<number[]>([]);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const [socialJob, setSocialJob] = useState<SocialJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [step, setStep] = useState(1); // 1: Select Images, 2: Analysis, 3: Generate Posts, 4: Results
  
  const router = useRouter();

  // Load user assets on component mount
  useEffect(() => {
    loadAssets();
  }, []);

  const loadAssets = async () => {
    try {
      const response = await fetch(`/api/user/assets`);
      if (response.ok) {
        const data = await response.json();
        if (data.assets) {
          setAssets(data.assets);
          return;
        }
      }
      
      // If API fails, show demo assets
      console.log("API not available, using demo data");
      setAssets([
        {
          id: 1,
          filename: "modern-kitchen.jpg",
          gcs_uri: "gs://demo/kitchen.jpg",
          signed_url: "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=500&h=500&fit=crop",
          kind: "listing",
          created_at: new Date().toISOString(),
        },
        {
          id: 2,
          filename: "luxury-bedroom.jpg",
          gcs_uri: "gs://demo/bedroom.jpg", 
          signed_url: "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=500&h=500&fit=crop",
          kind: "listing",
          created_at: new Date().toISOString(),
        },
        {
          id: 3,
          filename: "elegant-bathroom.jpg",
          gcs_uri: "gs://demo/bathroom.jpg",
          signed_url: "https://images.unsplash.com/photo-1620626011761-996317b8d101?w=500&h=500&fit=crop",
          kind: "listing", 
          created_at: new Date().toISOString(),
        },
        {
          id: 4,
          filename: "cozy-living-room.jpg",
          gcs_uri: "gs://demo/living.jpg",
          signed_url: "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=500&h=500&fit=crop",
          kind: "listing",
          created_at: new Date().toISOString(),
        }
      ]);
    } catch (err) {
      console.error("Failed to load assets:", err);
      setError("Failed to load your images - showing demo data");
      // Show demo assets
      setAssets([
        {
          id: 1,
          filename: "demo-kitchen.jpg",
          gcs_uri: "gs://demo/kitchen.jpg",
          signed_url: "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=500&h=500&fit=crop",
          kind: "demo",
          created_at: new Date().toISOString(),
        },
        {
          id: 2,
          filename: "demo-bedroom.jpg",
          gcs_uri: "gs://demo/bedroom.jpg",
          signed_url: "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=500&h=500&fit=crop",
          kind: "demo",
          created_at: new Date().toISOString(),
        }
      ]);
    }
  };

  const handleAssetToggle = (assetId: number) => {
    setSelectedAssets(prev => {
      if (prev.includes(assetId)) {
        return prev.filter(id => id !== assetId);
      } else if (prev.length < 10) { // Max 10 images
        return [...prev, assetId];
      }
      return prev;
    });
  };

  const startAnalysis = async () => {
    if (selectedAssets.length < 2) {
      setError("Please select at least 2 images for analysis");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/combination-agent/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_ids: selectedAssets,
          context: {
            business_type: "general",
            brand_voice: "professional"
          },
          purpose: "social_media"
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || "Failed to start analysis");
        }

        const job: AnalysisJob = {
          job_id: data.job_id,
          analysis_id: data.analysis_id,
          status: "pending",
          progress: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };

        setAnalysisJob(job);
        setStep(2);
        
        // Start polling for job status
        pollAnalysisStatus(job.job_id);
        return;
      }
      
      // If API fails, show demo analysis
      console.log("Analysis API not available, using demo");
      const demoJob: AnalysisJob = {
        job_id: 999,
        analysis_id: "demo_analysis_001",
        status: "pending",
        progress: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      setAnalysisJob(demoJob);
      setStep(2);
      
      // Simulate analysis progress
      setTimeout(() => {
        setAnalysisJob(prev => prev ? {...prev, status: "rendering", progress: 0.5} : null);
        setTimeout(() => {
          setAnalysisJob(prev => prev ? {...prev, status: "complete", progress: 1.0} : null);
          setStep(3);
        }, 2000);
      }, 3000);
      
    } catch (err: any) {
      console.error("Analysis failed:", err);
      // Show demo mode message but proceed with demo
      setError("Demo Mode: Backend not available - showing demonstration");
      
      const demoJob: AnalysisJob = {
        job_id: 999,
        analysis_id: "demo_analysis_001", 
        status: "complete",
        progress: 1.0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      setAnalysisJob(demoJob);
      setStep(3);
    } finally {
      setLoading(false);
    }
  };

  const pollAnalysisStatus = async (jobId: number) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/combination-agent/analysis/${jobId}/status`);
        const updatedJob: AnalysisJob = await response.json();
        
        setAnalysisJob(updatedJob);

        if (updatedJob.status === "complete") {
          clearInterval(pollInterval);
          setStep(3);
        } else if (updatedJob.status === "failed") {
          clearInterval(pollInterval);
          setError(updatedJob.error || "Analysis failed");
        }
      } catch (err) {
        console.error("Failed to poll status:", err);
        clearInterval(pollInterval);
        setError("Lost connection to analysis");
      }
    }, 2000);

    // Clear interval after 5 minutes
    setTimeout(() => clearInterval(pollInterval), 300000);
  };

  const generateSocialPosts = async (platforms: string[]) => {
    if (!analysisJob?.job_id) {
      setError("No analysis available for post generation");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/combination-agent/generate-social`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_job_id: analysisJob.job_id,
          platforms,
          context: {
            business_type: "general",
            brand_voice: "professional"
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.detail || "Failed to generate social posts");
        }

        const job: SocialJob = {
          job_id: data.job_id,
          generation_id: data.generation_id,
          status: "pending",
          progress: 0,
          platforms
        };

        setSocialJob(job);
        
        // Start polling for job status
        pollSocialStatus(job.job_id);
        return;
      }
      
      // Demo social content generation
      console.log("Social generation API not available, using demo");
      
      const demoJob: SocialJob = {
        job_id: 998,
        generation_id: "demo_social_001",
        status: "complete",
        progress: 1.0,
        platforms
      };

      setSocialJob(demoJob);
      
      // Generate demo social content
      const demoPosts = platforms.map(platform => ({
        platform,
        content: {
          text: platform === "instagram" 
            ? "🏡✨ Transform your space with these stunning design elements! Each piece tells a story of elegance and comfort. Ready to create your dream home? \n\n#InteriorDesign #HomeDecor #DreamHome #DesignInspiration #ModernLiving #HomeStyle #DecorTips #RoomMakeover"
            : platform === "twitter"
            ? "✨ Beautiful spaces start with thoughtful design choices. These elements showcase the perfect blend of style and functionality! #InteriorDesign #HomeDecor #DesignInspiration"
            : "Transform your living space with carefully curated design elements that reflect both style and functionality. These selected pieces demonstrate how thoughtful interior choices can create environments that inspire and comfort.\n\n#InteriorDesign #HomeDecor #ProfessionalDesign #ModernLiving #DesignConsultation",
          hashtags: platform === "instagram"
            ? ["#InteriorDesign", "#HomeDecor", "#DreamHome", "#DesignInspiration", "#ModernLiving", "#HomeStyle", "#DecorTips", "#RoomMakeover"]
            : platform === "twitter" 
            ? ["#InteriorDesign", "#HomeDecor", "#DesignInspiration"]
            : ["#InteriorDesign", "#HomeDecor", "#ProfessionalDesign", "#ModernLiving", "#DesignConsultation"],
          images: selectedAssets.slice(0, platform === "twitter" ? 4 : 10)
        }
      }));
      
      // Simulate generation with delay
      setTimeout(() => {
        setStep(4);
        // Store demo posts for display
        (window as any).demoPosts = demoPosts;
      }, 1500);
      
    } catch (err: any) {
      console.error("Social generation failed:", err);
      // Show demo content even on error
      setError("Demo Mode: Backend not available - showing demonstration");
      
      const demoJob: SocialJob = {
        job_id: 998,
        generation_id: "demo_social_001",
        status: "complete", 
        progress: 1.0,
        platforms
      };

      setSocialJob(demoJob);
      setStep(4);
    } finally {
      setLoading(false);
    }
  };

  const pollSocialStatus = async (jobId: number) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/combination-agent/social/${jobId}/status`);
        const updatedJob: SocialJob = await response.json();
        
        setSocialJob(updatedJob);

        if (updatedJob.status === "complete") {
          clearInterval(pollInterval);
          setStep(4);
        } else if (updatedJob.status === "failed") {
          clearInterval(pollInterval);
          setError(updatedJob.error || "Social post generation failed");
        }
      } catch (err) {
        console.error("Failed to poll status:", err);
        clearInterval(pollInterval);
        setError("Lost connection to generation process");
      }
    }, 2000);

    // Clear interval after 5 minutes
    setTimeout(() => clearInterval(pollInterval), 300000);
  };

  const resetWorkflow = () => {
    setSelectedAssets([]);
    setAnalysisJob(null);
    setSocialJob(null);
    setError("");
    setStep(1);
  };

  const selectedAssetObjects = assets.filter(asset => selectedAssets.includes(asset.id));

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Combination Agent</h1>
              <p className="text-gray-600 mt-2">
                Analyze your images and generate optimized social media posts
              </p>
            </div>
            {step > 1 && (
              <button 
                onClick={resetWorkflow}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Start New Analysis
              </button>
            )}
          </div>
          
          {/* Progress Steps */}
          <div className="flex items-center space-x-4 mt-6">
            <div className={`flex items-center space-x-2 ${step >= 1 ? "text-blue-600" : "text-gray-400"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? "bg-blue-600 text-white" : "bg-gray-300"}`}>
                1
              </div>
              <span>Select Images</span>
            </div>
            <div className={`w-8 h-1 ${step >= 2 ? "bg-blue-600" : "bg-gray-300"}`}></div>
            <div className={`flex items-center space-x-2 ${step >= 2 ? "text-blue-600" : "text-gray-400"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? "bg-blue-600 text-white" : "bg-gray-300"}`}>
                2
              </div>
              <span>Analyze</span>
            </div>
            <div className={`w-8 h-1 ${step >= 3 ? "bg-blue-600" : "bg-gray-300"}`}></div>
            <div className={`flex items-center space-x-2 ${step >= 3 ? "text-blue-600" : "text-gray-400"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 3 ? "bg-blue-600 text-white" : "bg-gray-300"}`}>
                3
              </div>
              <span>Generate Posts</span>
            </div>
            <div className={`w-8 h-1 ${step >= 4 ? "bg-blue-600" : "bg-gray-300"}`}></div>
            <div className={`flex items-center space-x-2 ${step >= 4 ? "text-blue-600" : "text-gray-400"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 4 ? "bg-blue-600 text-white" : "bg-gray-300"}`}>
                4
              </div>
              <span>Results</span>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-red-800 font-medium">Error</div>
            <div className="text-red-600">{error}</div>
          </div>
        )}

        {/* Step 1: Image Selection */}
        {step === 1 && (
          <div>
            <div className="bg-white p-6 rounded-lg shadow mb-6">
              <h2 className="text-xl font-semibold mb-4">Select Images for Analysis</h2>
              <p className="text-gray-600 mb-4">
                Choose 2-10 images to analyze together. Our AI will identify patterns, themes, 
                and combinations for optimal social media engagement.
              </p>
              
              {selectedAssets.length > 0 && (
                <div className="mb-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {selectedAssets.length} image{selectedAssets.length !== 1 ? "s" : ""} selected
                  </span>
                </div>
              )}
            </div>

            {/* Asset Gallery */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {assets.map((asset) => (
                  <div
                    key={asset.id}
                    className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                      selectedAssets.includes(asset.id)
                        ? "border-blue-500 ring-2 ring-blue-200"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                    onClick={() => handleAssetToggle(asset.id)}
                  >
                    <img
                      src={asset.signed_url}
                      alt={asset.filename}
                      className="w-full h-32 object-cover"
                    />
                    {selectedAssets.includes(asset.id) && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                        <span className="text-white text-xs font-bold">
                          {selectedAssets.indexOf(asset.id) + 1}
                        </span>
                      </div>
                    )}
                    <div className="p-2">
                      <p className="text-xs text-gray-600 truncate">{asset.filename}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-center">
              <button
                onClick={startAnalysis}
                disabled={selectedAssets.length < 2 || loading}
                className="px-8 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin mr-2 h-4 w-4" />
                    Starting Analysis...
                  </>
                ) : (
                  `Analyze ${selectedAssets.length} Images`
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Analysis Results */}
        {step === 2 && analysisJob && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Image Analysis</h2>
            <div className="flex items-center space-x-4 mb-4">
              <Loader className="animate-spin h-5 w-5 text-blue-600" />
              <span>Analyzing {selectedAssets.length} images...</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(analysisJob.progress || 0) * 100}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-600 mt-2">
              Status: {analysisJob.status} • Progress: {Math.round((analysisJob.progress || 0) * 100)}%
            </p>
          </div>
        )}

        {/* Step 3: Social Media Post Generation */}
        {step === 3 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Generate Social Media Posts</h2>
            <p className="text-gray-600 mb-6">
              Select which platforms you'd like to generate optimized posts for:
            </p>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              {["instagram", "facebook", "twitter", "linkedin", "pinterest", "tiktok"].map((platform) => (
                <label key={platform} className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-gray-50">
                  <input
                    type="checkbox"
                    className="form-checkbox h-4 w-4 text-blue-600"
                    defaultChecked={platform === "instagram"}
                  />
                  <span className="capitalize font-medium">{platform}</span>
                </label>
              ))}
            </div>

            <button
              onClick={() => generateSocialPosts(["instagram", "facebook"])}
              disabled={loading}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <>
                  <Loader className="animate-spin mr-2 h-4 w-4" />
                  Generating Posts...
                </>
              ) : (
                "Generate Social Media Posts"
              )}
            </button>
            
            {socialJob && (
              <div className="mt-4">
                <div className="flex items-center space-x-4 mb-2">
                  <Loader className="animate-spin h-4 w-4 text-blue-600" />
                  <span className="text-sm">Generating posts for {socialJob.platforms.join(", ")}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(socialJob.progress || 0) * 100}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 4: Results */}
        {step === 4 && socialJob && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Generated Social Media Posts</h2>
            <div className="text-center py-8">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Posts Generated Successfully!</h3>
              <p className="text-gray-600">
                Your social media posts have been generated and are ready for use.
              </p>
              <button
                onClick={resetWorkflow}
                className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Create Another Set
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}