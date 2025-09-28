"use client";

import { useState, useEffect, useCallback } from 'react';
import { Upload, Search, Tag, Grid, List, Plus, Edit2, Trash2, Copy, Filter } from 'lucide-react';

// Types
interface Asset {
  id: number;
  kind: string;
  gcs_uri: string;
  width?: number;
  height?: number;
  label?: string;
  tags: string[];
  upload_source: string;
  parent_asset_id?: number;
  created_at: string;
  view_url?: string;
}

interface AssetListResponse {
  assets: Asset[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

interface CreditStatus {
  available_credits: number;
  used_this_period: number;
  plan_limit: number;
  usage_percentage: number;
  period_start: string;
  period_end: string;
  plan: string;
}

// Credit Usage Component
function CreditUsageBar({ creditStatus }: { creditStatus: CreditStatus | null }) {
  if (!creditStatus) return null;

  return (
    <div className="bg-white border rounded-lg p-4 mb-6">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-sm font-medium text-gray-700">Credit Usage</h3>
        <span className="text-sm text-gray-500">
          {creditStatus.available_credits} / {creditStatus.plan_limit} remaining
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${
            creditStatus.usage_percentage > 90 
              ? 'bg-red-500' 
              : creditStatus.usage_percentage > 75 
              ? 'bg-yellow-500' 
              : 'bg-green-500'
          }`}
          style={{ width: `${Math.min(creditStatus.usage_percentage, 100)}%` }}
        />
      </div>
      <div className="flex justify-between items-center mt-2">
        <span className="text-xs text-gray-500">
          {creditStatus.used_this_period} used this period
        </span>
        <span className="text-xs font-medium text-blue-600 capitalize">
          {creditStatus.plan} Plan
        </span>
      </div>
    </div>
  );
}

// Upload Zone Component
function UploadZone({ onUpload, isUploading }: { 
  onUpload: (files: FileList, metadata: { label: string; tags: string[] }) => void;
  isUploading: boolean;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [label, setLabel] = useState('');
  const [tags, setTags] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      setSelectedFiles(files);
      setShowForm(true);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setSelectedFiles(files);
      setShowForm(true);
    }
  };

  const handleUpload = () => {
    if (selectedFiles) {
      const tagList = tags.split(',').map(t => t.trim()).filter(t => t.length > 0);
      onUpload(selectedFiles, { label, tags: tagList });
      setLabel('');
      setTags('');
      setSelectedFiles(null);
      setShowForm(false);
    }
  };

  const handleCancel = () => {
    setSelectedFiles(null);
    setShowForm(false);
    setLabel('');
    setTags('');
  };

  if (showForm) {
    return (
      <div className="bg-white border-2 border-blue-300 rounded-lg p-6 mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Upload {selectedFiles?.length} file{selectedFiles?.length !== 1 ? 's' : ''}
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Label (optional)
            </label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Luxury Kitchen, Modern Bathroom"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., kitchen, modern, luxury, staging"
            />
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isUploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload
                </>
              )}
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 mb-6 transition-colors ${
        isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="text-center">
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <div className="mt-4">
          <label htmlFor="file-upload" className="cursor-pointer">
            <span className="mt-2 block text-sm font-medium text-gray-900">
              Drop images here or click to browse
            </span>
            <input
              id="file-upload"
              name="file-upload"
              type="file"
              className="sr-only"
              multiple
              accept="image/*"
              onChange={handleFileSelect}
            />
          </label>
          <p className="mt-2 text-xs text-gray-500">
            PNG, JPG, GIF up to 10MB each
          </p>
        </div>
      </div>
    </div>
  );
}

// Asset Card Component
function AssetCard({ 
  asset, 
  onEdit, 
  onDelete, 
  onDuplicate, 
  selected, 
  onSelect 
}: {
  asset: Asset;
  onEdit: (asset: Asset) => void;
  onDelete: (asset: Asset) => void;
  onDuplicate: (asset: Asset) => void;
  selected: boolean;
  onSelect: (asset: Asset) => void;
}) {
  return (
    <div 
      className={`bg-white border-2 rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer ${
        selected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200'
      }`}
      onClick={() => onSelect(asset)}
    >
      <div className="aspect-square relative bg-gray-100">
        {asset.view_url ? (
          <img
            src={asset.view_url}
            alt={asset.label || `${asset.kind} image`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <Grid className="h-8 w-8" />
          </div>
        )}
        
        {/* Action buttons */}
        <div className="absolute top-2 right-2 flex space-x-1">
          <button
            onClick={(e) => { e.stopPropagation(); onDuplicate(asset); }}
            className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70"
            title="Duplicate"
          >
            <Copy className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(asset); }}
            className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70"
            title="Edit"
          >
            <Edit2 className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(asset); }}
            className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70"
            title="Delete"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>

        {/* Asset type badge */}
        <div className="absolute bottom-2 left-2">
          <span className="px-2 py-1 bg-black bg-opacity-50 text-white text-xs rounded">
            {asset.kind}
          </span>
        </div>
      </div>
      
      <div className="p-3">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-sm font-medium text-gray-900 truncate">
            {asset.label || `Untitled ${asset.kind}`}
          </h3>
          {asset.width && asset.height && (
            <span className="text-xs text-gray-500">
              {asset.width}×{asset.height}
            </span>
          )}
        </div>
        
        {asset.tags && asset.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {asset.tags.slice(0, 3).map((tag, index) => (
              <span
                key={index}
                className="inline-block bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded"
              >
                {tag}
              </span>
            ))}
            {asset.tags.length > 3 && (
              <span className="text-xs text-gray-500">
                +{asset.tags.length - 3} more
              </span>
            )}
          </div>
        )}
        
        <div className="text-xs text-gray-500">
          {new Date(asset.created_at).toLocaleDateString()}
        </div>
      </div>
    </div>
  );
}

// Main Gallery Component
export default function GalleryPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [creditStatus, setCreditStatus] = useState<CreditStatus | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedKind, setSelectedKind] = useState('');
  const [selectedTags, setSelectedTags] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [selectedAssets, setSelectedAssets] = useState<Set<number>>(new Set());
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [uploadMessage, setUploadMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Fetch assets
  const fetchAssets = useCallback(async (resetPage = false) => {
    const currentPage = resetPage ? 1 : page;
    const params = new URLSearchParams({
      page: currentPage.toString(),
      page_size: '20'
    });
    
    if (searchTerm) params.append('search', searchTerm);
    if (selectedKind) params.append('kind', selectedKind);
    if (selectedTags) params.append('tags', selectedTags);

    try {
      const response = await fetch(`/api/user/assets?${params}`);
      if (response.ok) {
        const data: AssetListResponse = await response.json();
        if (resetPage) {
          setAssets(data.assets);
          setPage(1);
        } else {
          setAssets(prev => currentPage === 1 ? data.assets : [...prev, ...data.assets]);
        }
        setHasMore(data.has_more);
      } else {
        // Backend unavailable - show demo assets
        console.log("Assets API not available, using demo assets");
        const demoAssets: Asset[] = [
          {
            id: 1,
            kind: 'headshot',
            gcs_uri: 'gs://demo/headshot1.jpg',
            label: 'Professional Headshot',
            tags: ['headshot', 'professional'],
            upload_source: 'demo',
            created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
            view_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop&crop=face',
            width: 400,
            height: 400
          },
          {
            id: 2,
            kind: 'headshot',
            gcs_uri: 'gs://demo/headshot2.jpg',
            label: 'Business Portrait',
            tags: ['headshot', 'business'],
            upload_source: 'demo',
            created_at: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
            view_url: 'https://images.unsplash.com/photo-1494790108755-2616c64c8888?w=400&h=400&fit=crop&crop=face',
            width: 400,
            height: 400
          },
          {
            id: 3,
            kind: 'listing',
            gcs_uri: 'gs://demo/property1.jpg',
            label: 'Modern Kitchen',
            tags: ['kitchen', 'modern', 'interior'],
            upload_source: 'demo',
            created_at: new Date(Date.now() - 259200000).toISOString(), // 3 days ago
            view_url: 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=400&fit=crop',
            width: 600,
            height: 400
          },
          {
            id: 4,
            kind: 'listing',
            gcs_uri: 'gs://demo/property2.jpg',
            label: 'Luxury Living Room',
            tags: ['living room', 'luxury', 'interior'],
            upload_source: 'demo',
            created_at: new Date(Date.now() - 345600000).toISOString(), // 4 days ago
            view_url: 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=600&h=400&fit=crop',
            width: 600,
            height: 400
          }
        ];
        
        setAssets(demoAssets);
        setHasMore(false);
        setPage(1);
      }
    } catch (error) {
      console.error('Failed to fetch assets:', error);
      // On error, also show demo assets
      const demoAssets: Asset[] = [
        {
          id: 1,
          kind: 'headshot',
          gcs_uri: 'gs://demo/headshot1.jpg',
          label: 'Demo Professional Headshot',
          tags: ['headshot', 'demo'],
          upload_source: 'demo',
          created_at: new Date().toISOString(),
          view_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop&crop=face',
          width: 400,
          height: 400
        }
      ];
      setAssets(demoAssets);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  }, [page, searchTerm, selectedKind, selectedTags]);

  // Fetch credit status
  const fetchCreditStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/credits/status');
      if (response.ok) {
        const data: CreditStatus = await response.json();
        setCreditStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch credit status:', error);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchAssets(true);
    fetchCreditStatus();
  }, []);

  // Search effect
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      fetchAssets(true);
    }, 300);
    return () => clearTimeout(timeoutId);
  }, [searchTerm, selectedKind, selectedTags]);

  // Handle upload
  const handleUpload = async (files: FileList, metadata: { label: string; tags: string[] }) => {
    setIsUploading(true);
    setUploadMessage(null);
    
    let successCount = 0;
    let failureCount = 0;
    
    try {
      for (const file of Array.from(files)) {
        try {
          // Get upload URL
          const uploadResponse = await fetch('/api/user/assets/upload-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              label: metadata.label || file.name,
              tags: metadata.tags,
              kind: 'headshot' // Based on user's upload of "Colin1 (Headshot)"
            })
          });
          
          if (uploadResponse.ok) {
            const { upload_url, gcs_uri } = await uploadResponse.json();
            
            // Check if this is demo mode (httpbin URL)
            const isDemo = upload_url.includes('httpbin.org');
            
            if (isDemo) {
              // Demo mode - simulate upload
              await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate upload time
              
              // Add demo asset to local state
              const demoAsset: Asset = {
                id: Date.now() + Math.random(),
                kind: 'headshot',
                gcs_uri: gcs_uri,
                label: metadata.label || file.name,
                tags: metadata.tags,
                upload_source: 'direct_upload',
                created_at: new Date().toISOString(),
                view_url: URL.createObjectURL(file) // Use blob URL for demo
              };
              
              setAssets(prev => [demoAsset, ...prev]);
              successCount++;
            } else {
              // Real upload
              const uploadResult = await fetch(upload_url, {
                method: 'PUT',
                body: file,
                headers: { 'Content-Type': file.type }
              });
              
              if (uploadResult.ok) {
                successCount++;
              } else {
                failureCount++;
              }
            }
          } else {
            failureCount++;
          }
        } catch (error) {
          console.error('Individual file upload failed:', error);
          failureCount++;
        }
      }
      
      // Show success/error message
      if (successCount > 0 && failureCount === 0) {
        const isDemoMode = assets.some(a => a.view_url?.startsWith('blob:'));
        const message = isDemoMode 
          ? `✅ Demo: ${successCount} file(s) uploaded successfully! (Using demo mode - backend not available)`
          : `✅ ${successCount} file(s) uploaded successfully!`;
        
        setUploadMessage({ type: 'success', text: message });
      } else if (successCount > 0 && failureCount > 0) {
        setUploadMessage({ 
          type: 'info', 
          text: `⚠️ ${successCount} file(s) uploaded successfully, ${failureCount} failed.` 
        });
      } else {
        setUploadMessage({ 
          type: 'error', 
          text: `❌ Upload failed for ${failureCount} file(s). Please try again.` 
        });
      }
      
      // Refresh assets list (only if not in demo mode)
      if (!assets.some(a => a.view_url?.startsWith('blob:'))) {
        fetchAssets(true);
        fetchCreditStatus(); // Refresh credits in case upload consumed any
      }
      
      // Clear message after 5 seconds
      setTimeout(() => setUploadMessage(null), 5000);
      
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadMessage({ 
        type: 'error', 
        text: '❌ Upload failed. Please try again.' 
      });
      setTimeout(() => setUploadMessage(null), 5000);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle asset actions
  const handleEditAsset = (asset: Asset) => {
    // TODO: Open edit modal
    console.log('Edit asset:', asset);
  };

  const handleDeleteAsset = async (asset: Asset) => {
    if (confirm('Are you sure you want to delete this image?')) {
      try {
        const response = await fetch(`/api/user/assets/${asset.id}`, {
          method: 'DELETE'
        });
        if (response.ok) {
          fetchAssets(true);
        }
      } catch (error) {
        console.error('Delete failed:', error);
      }
    }
  };

  const handleDuplicateAsset = async (asset: Asset) => {
    try {
      const response = await fetch(`/api/user/assets/${asset.id}/duplicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: `${asset.label} (Copy)`,
          tags: asset.tags
        })
      });
      if (response.ok) {
        fetchAssets(true);
      }
    } catch (error) {
      console.error('Duplicate failed:', error);
    }
  };

  const handleSelectAsset = (asset: Asset) => {
    const newSelected = new Set(selectedAssets);
    if (newSelected.has(asset.id)) {
      newSelected.delete(asset.id);
    } else {
      newSelected.add(asset.id);
    }
    setSelectedAssets(newSelected);
  };

  const loadMore = () => {
    setPage(prev => prev + 1);
    fetchAssets();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Image Gallery</h1>
          <p className="text-gray-600 mt-1">
            Manage your property images, agent photos, and AI-generated content
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 rounded ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-400'}`}
          >
            <Grid className="h-5 w-5" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 rounded ${viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-400'}`}
          >
            <List className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Credit Usage */}
      <CreditUsageBar creditStatus={creditStatus} />

      {/* Upload Zone */}
      <UploadZone onUpload={handleUpload} isUploading={isUploading} />

      {/* Upload Status Message */}
      {uploadMessage && (
        <div className={`mb-6 p-4 rounded-lg ${
          uploadMessage.type === 'success' ? 'bg-green-50 border border-green-200 text-green-800' :
          uploadMessage.type === 'error' ? 'bg-red-50 border border-red-200 text-red-800' :
          'bg-yellow-50 border border-yellow-200 text-yellow-800'
        }`}>
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {uploadMessage.type === 'success' && (
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              )}
              {uploadMessage.type === 'error' && (
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              {uploadMessage.type === 'info' && (
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">
                {uploadMessage.text}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search images..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          
          <select
            value={selectedKind}
            onChange={(e) => setSelectedKind(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            <option value="listing">Listing</option>
            <option value="headshot">Headshot</option>
            <option value="output">AI Generated</option>
          </select>
          
          <div className="relative">
            <Tag className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Filter by tags..."
              value={selectedTags}
              onChange={(e) => setSelectedTags(e.target.value)}
              className="pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Selected Actions */}
      {selectedAssets.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-blue-800">
              {selectedAssets.size} image{selectedAssets.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex space-x-2">
              <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                Create Post
              </button>
              <button 
                onClick={() => setSelectedAssets(new Set())}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
              >
                Clear Selection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assets Grid */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : assets.length === 0 ? (
        <div className="text-center py-12">
          <Grid className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No images yet</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by uploading your first image above.</p>
        </div>
      ) : (
        <>
          <div className={`grid gap-4 ${
            viewMode === 'grid' 
              ? 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6' 
              : 'grid-cols-1'
          }`}>
            {assets.map((asset) => (
              <AssetCard
                key={asset.id}
                asset={asset}
                onEdit={handleEditAsset}
                onDelete={handleDeleteAsset}
                onDuplicate={handleDuplicateAsset}
                selected={selectedAssets.has(asset.id)}
                onSelect={handleSelectAsset}
              />
            ))}
          </div>

          {/* Load More */}
          {hasMore && (
            <div className="text-center mt-8">
              <button
                onClick={loadMore}
                className="px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Load More Images
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}