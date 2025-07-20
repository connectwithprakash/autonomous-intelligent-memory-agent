import { useState, useEffect } from 'react';
import { Database, HardDrive, Zap, Snowflake } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { endpoints } from '../lib/api';
import type { MemoryStats, BlockInfo } from '../lib/api';
import { cn, formatBytes, formatTimestamp, getRelevanceColor, getTierColor } from '../lib/utils';

export function Memory() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [blocks, setBlocks] = useState<BlockInfo[]>([]);
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [selectedTier]);

  const fetchData = async () => {
    try {
      const [statsRes, blocksRes] = await Promise.all([
        endpoints.getMemoryStats(),
        endpoints.listBlocks({ tier: selectedTier || undefined, limit: 20 }),
      ]);
      setStats(statsRes.data);
      setBlocks(blocksRes.data);
    } catch (error) {
      console.error('Failed to fetch memory data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !stats) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-500">Loading memory statistics...</div>
      </div>
    );
  }

  const tierData = Object.entries(stats.tier_breakdown).map(([tier, data]) => ({
    name: tier,
    blocks: data.blocks,
    size: data.size_bytes,
    color: getTierColor(tier),
  }));

  const tierIcons = {
    HOT: Zap,
    WARM: HardDrive,
    COLD: Snowflake,
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Blocks</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {stats.total_blocks.toLocaleString()}
                </p>
              </div>
              <Database className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Size</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {formatBytes(stats.total_size_bytes)}
                </p>
              </div>
              <HardDrive className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Compression</p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {stats.compression_ratio.toFixed(1)}x
                </p>
              </div>
              <Zap className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Age Range</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">
                  {stats.oldest_block && stats.newest_block
                    ? `${new Date(stats.oldest_block).toLocaleDateString()} - ${new Date(stats.newest_block).toLocaleDateString()}`
                    : 'N/A'}
                </p>
              </div>
              <Snowflake className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        {/* Tier Distribution */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Storage Distribution
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={tierData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, blocks }) => `${name}: ${blocks}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="blocks"
                >
                  {tierData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Size by Tier
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={tierData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis tickFormatter={(value) => formatBytes(value)} />
                <Tooltip formatter={(value: number) => formatBytes(value)} />
                <Bar dataKey="size" fill="#8884d8">
                  {tierData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tier Selector */}
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Filter by tier:
            </span>
            <div className="flex space-x-2">
              <button
                onClick={() => setSelectedTier(null)}
                className={cn(
                  'px-3 py-1 rounded-md text-sm font-medium transition-colors',
                  selectedTier === null
                    ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200'
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                )}
              >
                All
              </button>
              {Object.keys(stats.tier_breakdown).map((tier) => {
                const Icon = tierIcons[tier as keyof typeof tierIcons] || Database;
                return (
                  <button
                    key={tier}
                    onClick={() => setSelectedTier(tier)}
                    className={cn(
                      'px-3 py-1 rounded-md text-sm font-medium transition-colors flex items-center space-x-1',
                      selectedTier === tier
                        ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200'
                        : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{tier}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Recent Blocks */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Memory Blocks
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Block ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tier
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Relevance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Accesses
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {blocks.map((block) => (
                  <tr key={block.block_id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {block.block_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs font-medium text-white',
                          getTierColor(block.memory_tier)
                        )}
                      >
                        {block.memory_tier}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={cn('font-medium', getRelevanceColor(block.relevance_score))}>
                        {(block.relevance_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatBytes(block.size_bytes)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatTimestamp(block.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {block.access_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}