"use client";

import { useState, useEffect } from 'react';
import { TrendingUp, Calendar, BarChart3, Info, CreditCard, Clock } from 'lucide-react';

// Types
interface CreditStatus {
  available_credits: number;
  used_this_period: number;
  plan_limit: number;
  usage_percentage: number;
  period_start: string;
  period_end: string;
  plan: string;
  usage_breakdown: Record<string, number>;
  costs: Record<string, number>;
}

interface UsageEntry {
  timestamp: string;
  action_type: string;
  credits_used: number;
  job_id?: number;
  asset_id?: number;
  metadata: Record<string, any>;
}

interface UsageHistory {
  entries: UsageEntry[];
  total_entries: number;
}

interface CreditPricing {
  action_costs: Record<string, number>;
  plan_limits: Record<string, number>;
}

// Credit Usage Chart Component
function UsageChart({ usageBreakdown, costs }: { 
  usageBreakdown: Record<string, number>;
  costs: Record<string, number>;
}) {
  const totalUsed = Object.values(usageBreakdown).reduce((sum, val) => sum + val, 0);
  
  if (totalUsed === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center">
        <BarChart3 className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">No usage data for this period</p>
      </div>
    );
  }

  const actionLabels: Record<string, string> = {
    'image_generation': 'Image Generation',
    'image_editing': 'Image Editing', 
    'content_generation': 'Content Generation',
    'post_combination': 'Post Combination',
    'social_posts': 'Social Posts'
  };

  const colors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
    'bg-yellow-500',
    'bg-red-500'
  ];

  return (
    <div className="space-y-4">
      {Object.entries(usageBreakdown).map(([actionType, credits], index) => {
        const percentage = (credits / totalUsed) * 100;
        const cost = costs[actionType] || 1;
        const operations = Math.floor(credits / cost);
        
        return (
          <div key={actionType} className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${colors[index % colors.length]}`} />
              <span className="text-sm font-medium text-gray-900">
                {actionLabels[actionType] || actionType}
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">{credits} credits</div>
                <div className="text-xs text-gray-500">{operations} operations</div>
              </div>
              <div className="w-20 bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${colors[index % colors.length]}`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Recent Activity Component
function RecentActivity({ entries }: { entries: UsageEntry[] }) {
  const actionLabels: Record<string, string> = {
    'image_generation': 'Generated image',
    'image_editing': 'Edited image',
    'content_generation': 'Generated content',
    'post_combination': 'Combined post',
    'social_posts': 'Created social posts'
  };

  const actionIcons: Record<string, string> = {
    'image_generation': '🖼️',
    'image_editing': '✏️',
    'content_generation': '📝',
    'post_combination': '🔗',
    'social_posts': '📱'
  };

  if (entries.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center">
        <Clock className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">No recent activity</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {entries.slice(0, 10).map((entry, index) => (
        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center space-x-3">
            <span className="text-lg">
              {actionIcons[entry.action_type] || '⚡'}
            </span>
            <div>
              <div className="text-sm font-medium text-gray-900">
                {actionLabels[entry.action_type] || entry.action_type}
              </div>
              <div className="text-xs text-gray-500">
                {new Date(entry.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-gray-900">
              {entry.credits_used > 0 ? '-' : '+'}{Math.abs(entry.credits_used)} credits
            </div>
            {entry.credits_used < 0 && (
              <div className="text-xs text-green-600">Refunded</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// Main Usage Dashboard Component
export default function UsageDashboard() {
  const [creditStatus, setCreditStatus] = useState<CreditStatus | null>(null);
  const [usageHistory, setUsageHistory] = useState<UsageHistory | null>(null);
  const [pricing, setPricing] = useState<CreditPricing | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'pricing'>('overview');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, historyRes, pricingRes] = await Promise.all([
          fetch('/api/credits/status'),
          fetch('/api/credits/usage?days=30'),
          fetch('/api/credits/pricing')
        ]);

        if (statusRes.ok) {
          const statusData: CreditStatus = await statusRes.json();
          setCreditStatus(statusData);
        }

        if (historyRes.ok) {
          const historyData: UsageHistory = await historyRes.json();
          setUsageHistory(historyData);
        }

        if (pricingRes.ok) {
          const pricingData: CreditPricing = await pricingRes.json();
          setPricing(pricingData);
        }
      } catch (error) {
        console.error('Failed to fetch usage data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  const periodEnd = creditStatus ? new Date(creditStatus.period_end) : new Date();
  const daysUntilReset = Math.ceil((periodEnd.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Usage Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Monitor your credit usage and track AI operation consumption
        </p>
      </div>

      {/* Credit Status Cards */}
      {creditStatus && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white border rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Available Credits</p>
                <p className="text-2xl font-bold text-gray-900">{creditStatus.available_credits}</p>
              </div>
              <CreditCard className="h-8 w-8 text-blue-500" />
            </div>
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Used: {creditStatus.used_this_period}</span>
                <span>Limit: {creditStatus.plan_limit}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
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
            </div>
          </div>

          <div className="bg-white border rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Current Plan</p>
                <p className="text-2xl font-bold text-gray-900 capitalize">{creditStatus.plan}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-500" />
            </div>
            <div className="mt-4">
              <p className="text-sm text-gray-600">
                {creditStatus.plan_limit} credits per month
              </p>
              <p className="text-xs text-blue-600 mt-1">
                Upgrade for more credits
              </p>
            </div>
          </div>

          <div className="bg-white border rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Resets In</p>
                <p className="text-2xl font-bold text-gray-900">{daysUntilReset} days</p>
              </div>
              <Calendar className="h-8 w-8 text-purple-500" />
            </div>
            <div className="mt-4">
              <p className="text-sm text-gray-600">
                {periodEnd.toLocaleDateString()}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Credits reset monthly
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'history', label: 'Recent Activity', icon: Clock },
            { id: 'pricing', label: 'Pricing', icon: Info }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white border rounded-lg p-6">
        {activeTab === 'overview' && creditStatus && (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Usage Breakdown</h3>
            <UsageChart 
              usageBreakdown={creditStatus.usage_breakdown} 
              costs={creditStatus.costs}
            />
          </div>
        )}

        {activeTab === 'history' && usageHistory && (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
            <RecentActivity entries={usageHistory.entries} />
            {usageHistory.entries.length > 10 && (
              <div className="text-center mt-6">
                <button className="text-blue-600 hover:text-blue-800 text-sm">
                  View all activity →
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'pricing' && pricing && (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Credit Pricing</h3>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Action Costs</h4>
                <div className="space-y-2">
                  {Object.entries(pricing.action_costs).map(([action, cost]) => (
                    <div key={action} className="flex justify-between items-center py-2 px-3 bg-gray-50 rounded">
                      <span className="text-sm text-gray-900 capitalize">
                        {action.replace('_', ' ')}
                      </span>
                      <span className="text-sm font-medium text-gray-900">
                        {cost} credit{cost !== 1 ? 's' : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Plan Limits</h4>
                <div className="space-y-2">
                  {Object.entries(pricing.plan_limits).map(([plan, limit]) => (
                    <div key={plan} className="flex justify-between items-center py-2 px-3 bg-gray-50 rounded">
                      <span className="text-sm text-gray-900 capitalize font-medium">
                        {plan} Plan
                      </span>
                      <span className="text-sm text-gray-900">
                        {limit} credits/month
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}