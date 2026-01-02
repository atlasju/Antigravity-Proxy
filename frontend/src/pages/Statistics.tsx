import { useEffect, useState } from 'react';
import { RefreshCw, TrendingUp, Clock, CheckCircle, Activity, BarChart3 } from 'lucide-react';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend
} from 'recharts';
import api from '../services/api';

// Chart colors
const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

interface StatsOverview {
    total_requests: number;
    success_rate: number;
    avg_response_time_ms: number;
    today_requests: number;
}

interface ProtocolData {
    name: string;
    value: number;
    [key: string]: any;
}

interface DailyData {
    date: string;
    requests: number;
    [key: string]: any;
}

interface ModelData {
    model: string;
    count: number;
    percentage: number;
}

interface QuotaData {
    email: string;
    tier: string;
    quota: number;
}

// Animated counter component
function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
    const [display, setDisplay] = useState(0);

    useEffect(() => {
        const duration = 1000;
        const steps = 30;
        const increment = value / steps;
        let current = 0;

        const timer = setInterval(() => {
            current += increment;
            if (current >= value) {
                setDisplay(value);
                clearInterval(timer);
            } else {
                setDisplay(Math.floor(current));
            }
        }, duration / steps);

        return () => clearInterval(timer);
    }, [value]);

    return <span>{display.toLocaleString()}{suffix}</span>;
}

export default function Statistics() {
    const [loading, setLoading] = useState(true);
    const [overview, setOverview] = useState<StatsOverview | null>(null);
    const [protocols, setProtocols] = useState<ProtocolData[]>([]);
    const [daily, setDaily] = useState<DailyData[]>([]);
    const [models, setModels] = useState<ModelData[]>([]);
    const [quotas, setQuotas] = useState<QuotaData[]>([]);

    const fetchStats = async () => {
        setLoading(true);
        try {
            const [overviewData, protocolData, dailyData, modelData, quotaData] = await Promise.all([
                api.getStatsOverview(),
                api.getStatsProtocols(),
                api.getStatsDaily(),
                api.getStatsModels(),
                api.getStatsQuotas(),
            ]);
            setOverview(overviewData);
            setProtocols(protocolData);
            setDaily(dailyData);
            setModels(modelData);
            setQuotas(quotaData);
        } catch (e) {
            console.error('Failed to fetch stats:', e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
    }, []);

    const getTierColor = (tier: string) => {
        if (tier.toLowerCase().includes('ultra')) return 'bg-purple-500';
        if (tier.toLowerCase().includes('pro')) return 'bg-blue-500';
        return 'bg-gray-500';
    };

    return (
        <div className="p-6 max-w-[95%] mx-auto space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <BarChart3 className="w-7 h-7 text-indigo-500" />
                        Usage Statistics
                    </h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Monitor API usage and system performance
                    </p>
                </div>
                <button
                    onClick={fetchStats}
                    disabled={loading}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2 disabled:opacity-50"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </button>
            </div>

            {/* Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Total Requests */}
                <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-5 text-white shadow-lg">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-white/20 rounded-lg">
                            <Activity className="w-5 h-5" />
                        </div>
                        <span className="text-white/90 text-sm font-medium">Total Requests</span>
                    </div>
                    <div className="text-3xl font-bold">
                        {overview ? <AnimatedNumber value={overview.total_requests} /> : '—'}
                    </div>
                    <div className="text-white/70 text-sm mt-1">
                        Today: {overview?.today_requests || 0}
                    </div>
                </div>

                {/* Success Rate */}
                <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl p-5 text-white shadow-lg">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-white/20 rounded-lg">
                            <CheckCircle className="w-5 h-5" />
                        </div>
                        <span className="text-white/90 text-sm font-medium">Success Rate</span>
                    </div>
                    <div className="text-3xl font-bold">
                        {overview ? <AnimatedNumber value={overview.success_rate} suffix="%" /> : '—'}
                    </div>
                    <div className="text-white/70 text-sm mt-1">
                        Request completion
                    </div>
                </div>

                {/* Avg Response Time */}
                <div className="bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl p-5 text-white shadow-lg">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-white/20 rounded-lg">
                            <Clock className="w-5 h-5" />
                        </div>
                        <span className="text-white/90 text-sm font-medium">Avg Response</span>
                    </div>
                    <div className="text-3xl font-bold">
                        {overview ? <AnimatedNumber value={overview.avg_response_time_ms} suffix="ms" /> : '—'}
                    </div>
                    <div className="text-white/70 text-sm mt-1">
                        Average latency
                    </div>
                </div>

                {/* Accounts Active */}
                <div className="bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl p-5 text-white shadow-lg">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-white/20 rounded-lg">
                            <TrendingUp className="w-5 h-5" />
                        </div>
                        <span className="text-white/90 text-sm font-medium">Active Accounts</span>
                    </div>
                    <div className="text-3xl font-bold">
                        {quotas.length > 0 ? <AnimatedNumber value={quotas.length} /> : '—'}
                    </div>
                    <div className="text-white/70 text-sm mt-1">
                        In rotation pool
                    </div>
                </div>
            </div>

            {/* Charts Row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Daily Trend */}
                <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        Request Trend (7 Days)
                    </h3>
                    <div className="h-64" style={{ minWidth: 0 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={daily}>
                                <defs>
                                    <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                                <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
                                <YAxis stroke="#9ca3af" fontSize={12} />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: '#1f2937',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: '#fff'
                                    }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="requests"
                                    stroke="#6366f1"
                                    strokeWidth={2}
                                    fill="url(#colorRequests)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Protocol Distribution */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        Protocol Usage
                    </h3>
                    <div className="h-64" style={{ minWidth: 0 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={protocols}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={50}
                                    outerRadius={80}
                                    paddingAngle={4}
                                    dataKey="value"
                                >
                                    {protocols.map((_, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: '#1f2937',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: '#fff'
                                    }}
                                />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Charts Row 2 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Models */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        Top Models
                    </h3>
                    <div className="space-y-3">
                        {models.length > 0 ? models.slice(0, 6).map((m, i) => (
                            <div key={m.model} className="flex items-center gap-3">
                                <span className="w-5 text-sm text-gray-500 dark:text-gray-400 font-mono">
                                    #{i + 1}
                                </span>
                                <div className="flex-1">
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-gray-900 dark:text-white font-medium truncate max-w-[180px]">
                                            {m.model}
                                        </span>
                                        <span className="text-gray-500 dark:text-gray-400">
                                            {m.count}
                                        </span>
                                    </div>
                                    <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                                            style={{ width: `${m.percentage}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        )) : (
                            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                                No model data yet
                            </div>
                        )}
                    </div>
                </div>

                {/* Account Quotas */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-5">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        Account Quotas
                    </h3>
                    <div className="space-y-3">
                        {quotas.length > 0 ? quotas.slice(0, 6).map((q) => (
                            <div key={q.email} className="flex items-center gap-3">
                                <div className={`w-2 h-2 rounded-full ${getTierColor(q.tier)}`} />
                                <div className="flex-1">
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-gray-900 dark:text-white font-medium truncate max-w-[200px]">
                                            {q.email}
                                        </span>
                                        <span className="text-gray-500 dark:text-gray-400">
                                            {q.quota}%
                                        </span>
                                    </div>
                                    <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full transition-all duration-500 ${q.quota > 50 ? 'bg-green-500' :
                                                q.quota > 20 ? 'bg-amber-500' : 'bg-red-500'
                                                }`}
                                            style={{ width: `${q.quota}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        )) : (
                            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                                No quota data yet
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
