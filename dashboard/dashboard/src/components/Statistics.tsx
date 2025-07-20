import { useState, useEffect } from 'react';
import { Activity, Users, MessageSquare, Brain, TrendingUp } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import useWebSocket from 'react-use-websocket';
import { endpoints, WS_URL } from '../lib/api';
import type { AgentStats } from '../lib/api';
import type { WebSocketEvent, StatsEvent } from '../lib/websocket';
import { cn } from '../lib/utils';

export function Statistics() {
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [timeSeriesData, setTimeSeriesData] = useState<any[]>([]);
  const [wsStats, setWsStats] = useState<StatsEvent | null>(null);
  const [loading, setLoading] = useState(true);

  const { lastMessage } = useWebSocket(`${WS_URL}/ws/dashboard`, {
    onOpen: () => console.log('WebSocket connected'),
    onClose: () => console.log('WebSocket disconnected'),
    shouldReconnect: () => true,
  });

  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const event: WebSocketEvent = JSON.parse(lastMessage.data);
        if (event.type === 'stats') {
          setWsStats(event.data as StatsEvent);
          // Add to time series
          setTimeSeriesData(prev => {
            const newData = [...prev, {
              time: new Date(event.timestamp).toLocaleTimeString(),
              messages: event.data.messages_per_minute,
              relevance: event.data.avg_relevance_score * 100,
              memory: event.data.memory_usage_mb,
            }];
            // Keep only last 20 data points
            return newData.slice(-20);
          });
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await endpoints.getAgentStats();
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !stats) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-500">Loading statistics...</div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Active Sessions',
      value: wsStats?.active_sessions || stats.active_sessions,
      icon: Users,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900',
    },
    {
      title: 'Total Messages',
      value: stats.total_messages.toLocaleString(),
      icon: MessageSquare,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-100 dark:bg-green-900',
    },
    {
      title: 'Corrections Made',
      value: stats.total_corrections,
      icon: Brain,
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-100 dark:bg-purple-900',
    },
    {
      title: 'Avg Relevance',
      value: `${(wsStats?.avg_relevance_score || stats.avg_relevance_score * 100).toFixed(1)}%`,
      icon: TrendingUp,
      color: 'text-orange-600 dark:text-orange-400',
      bgColor: 'bg-orange-100 dark:bg-orange-900',
    },
    {
      title: 'Memory Usage',
      value: `${(wsStats?.memory_usage_mb || stats.memory_usage_mb).toFixed(1)} MB`,
      icon: Activity,
      color: 'text-indigo-600 dark:text-indigo-400',
      bgColor: 'bg-indigo-100 dark:bg-indigo-900',
    },
    {
      title: 'Messages/min',
      value: wsStats?.messages_per_minute || '0',
      icon: Activity,
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-100 dark:bg-red-900',
    },
  ];

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Real-time Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {statCards.map((stat) => (
            <div key={stat.title} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{stat.title}</p>
                  <p className="text-2xl font-semibold text-gray-900 dark:text-white mt-1">
                    {stat.value}
                  </p>
                </div>
                <div className={cn('p-3 rounded-lg', stat.bgColor)}>
                  <stat.icon className={cn('h-6 w-6', stat.color)} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Time Series Charts */}
        {timeSeriesData.length > 0 && (
          <>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Messages per Minute
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={timeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="messages"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Relevance Score Trend
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={timeSeriesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip formatter={(value) => `${value}%`} />
                    <Line
                      type="monotone"
                      dataKey="relevance"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Memory Usage
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={timeSeriesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip formatter={(value) => `${value} MB`} />
                    <Line
                      type="monotone"
                      dataKey="memory"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}

        {/* Connection Status */}
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div
                className={cn(
                  'h-3 w-3 rounded-full',
                  wsStats ? 'bg-green-500' : 'bg-red-500'
                )}
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                WebSocket {wsStats ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {wsStats && (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Active Connections: {wsStats.active_connections}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}