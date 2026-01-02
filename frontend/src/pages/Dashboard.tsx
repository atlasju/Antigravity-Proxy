/**
 * Dashboard Page
 * 
 * Overview of accounts and quota status
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Sparkles, Bot, AlertTriangle, RefreshCw, Plus, Battery, Clock, Loader2 } from 'lucide-react';
import { useAccountStore } from '../stores/useAccountStore';
import api from '../services/api';

function QuotaMatrix() {
    const [matrix, setMatrix] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchMatrix = () => {
        setLoading(true);
        api.getQuotaMatrix()
            .then(setMatrix)
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchMatrix();
    }, []);

    const groups = [
        { key: 'claude_gpt', label: 'Claude / GPT-OSS', icon: '🧠' },
        { key: 'gemini_pro', label: 'Gemini Pro (High/Low)', icon: '💎' },
        { key: 'gemini_flash', label: 'Gemini Flash', icon: '⚡' },
    ];

    if (loading) return (
        <div className="bg-white dark:bg-gray-800 p-8 rounded-xl border border-gray-100 dark:border-gray-700 flex justify-center items-center h-48">
            <div className="flex flex-col items-center gap-2 text-gray-500 text-sm">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span>Scanning account quotas...</span>
            </div>
        </div>
    );

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
            <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800/50">
                <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                    <Battery className="w-4 h-4 text-indigo-500" />
                    Quota Matrix
                </h3>
                <button
                    onClick={fetchMatrix}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition-colors"
                    title="Refresh Matrix"
                >
                    <RefreshCw className="w-4 h-4 text-gray-500" />
                </button>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-gray-50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-700">
                            <th className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400 w-1/4">Account</th>
                            {groups.map(g => (
                                <th key={g.key} className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">
                                    <span className="flex items-center gap-1">
                                        <span>{g.icon}</span> {g.label}
                                    </span>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                        {matrix.map((acc) => (
                            <tr key={acc.email} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                <td className="px-4 py-3">
                                    <div className="font-medium text-gray-900 dark:text-white truncate max-w-[180px]" title={acc.email}>
                                        {acc.email}
                                    </div>
                                    <div className="text-xs font-mono text-gray-400 truncate max-w-[180px]">
                                        {acc.project_id}
                                    </div>
                                    {acc.error && (
                                        <div className="text-xs text-red-500 mt-1 flex items-center gap-1">
                                            <AlertTriangle className="w-3 h-3" /> Error
                                        </div>
                                    )}
                                </td>
                                {groups.map(g => {
                                    const quota = acc.quotas?.[g.key];
                                    if (!quota || !quota.available) return (
                                        <td key={g.key} className="px-4 py-3 text-gray-300 dark:text-gray-600">-</td>
                                    );

                                    const pct = Math.round((quota.remaining_fraction || 0) * 100);
                                    let color = 'bg-blue-500';
                                    if (pct > 50) color = 'bg-green-500';
                                    else if (pct > 20) color = 'bg-yellow-500';
                                    else color = 'bg-red-500';

                                    return (
                                        <td key={g.key} className="px-4 py-3">
                                            <div className="flex items-center gap-2 mb-1">
                                                <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
                                                </div>
                                                <span className={`text-xs font-mono font-medium ${pct === 0 ? 'text-red-500' : 'text-gray-600 dark:text-gray-300'}`}>
                                                    {pct}%
                                                </span>
                                            </div>
                                            {quota.reset_time && (
                                                <div className="text-[10px] text-gray-400 flex items-center gap-1" title="Reset Time">
                                                    <Clock className="w-3 h-3" />
                                                    {new Date(quota.reset_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </div>
                                            )}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                        {matrix.length === 0 && !loading && (
                            <tr>
                                <td colSpan={4} className="px-4 py-8 text-center text-gray-400 italic">
                                    No accounts connected. Add an account to see quotas.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default function Dashboard() {
    const navigate = useNavigate();
    const { accounts, poolStatus, fetchAccounts, fetchPoolStatus, fetchAvailableModels, reloadPool } = useAccountStore();
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [health, setHealth] = useState<{ status: string; accounts_loaded: number } | null>(null);
    const [bestAccount, setBestAccount] = useState<{
        best_account: { email: string; project_id: string; average_quota: number } | null;
        overall_average: number;
    } | null>(null);

    const fetchBestAccount = async () => {
        try {
            const data = await api.getBestAccount();
            setBestAccount(data);
        } catch (e) {
            console.error('Failed to fetch best account:', e);
        }
    };

    useEffect(() => {
        fetchAccounts();
        fetchPoolStatus();
        fetchAvailableModels();
        api.health().then(setHealth).catch(console.error);
        fetchBestAccount();
    }, []);

    const stats = useMemo(() => {
        return {
            total: accounts.length,
            poolSize: poolStatus?.pool_size || 0,
            expiringSoon: poolStatus?.accounts.filter(a => a.expires_in_seconds < 300).length || 0,
        };
    }, [accounts, poolStatus]);

    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            await reloadPool();
            await fetchAccounts();
            await fetchPoolStatus();
            const h = await api.health();
            setHealth(h);
        } finally {
            setIsRefreshing(false);
        }
    };

    return (
        <div className="p-6 max-w-[95%] mx-auto">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        {health ? `Backend: ${health.status} | Pool: ${health.accounts_loaded} accounts` : 'Loading...'}
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => navigate('/accounts')}
                        className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" />
                        Add Account
                    </button>
                    <button
                        onClick={handleRefresh}
                        disabled={isRefreshing}
                        className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2 disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                            <Users className="w-5 h-5 text-blue-500" />
                        </div>
                        <span className="text-sm text-gray-500 dark:text-gray-400">Total Accounts</span>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 dark:text-white">{stats.total}</div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-green-50 dark:bg-green-900/30 rounded-lg">
                            <Sparkles className="w-5 h-5 text-green-500" />
                        </div>
                        <span className="text-sm text-gray-500 dark:text-gray-400">Active in Pool</span>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 dark:text-white">{stats.poolSize}</div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-cyan-50 dark:bg-cyan-900/30 rounded-lg">
                            <Bot className="w-5 h-5 text-cyan-500" />
                        </div>
                        <span className="text-sm text-gray-500 dark:text-gray-400">API Status</span>
                    </div>
                    <div className="text-lg font-bold text-green-600 dark:text-green-400">
                        {health?.status === 'ok' ? '✓ Online' : '...'}
                    </div>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-orange-50 dark:bg-orange-900/30 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-orange-500" />
                        </div>
                        <span className="text-sm text-gray-500 dark:text-gray-400">Expiring Soon</span>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 dark:text-white">{stats.expiringSoon}</div>
                </div>
            </div>

            {/* Best Account Recommendation */}
            {bestAccount?.best_account && (
                <div className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 dark:from-indigo-900/30 dark:to-purple-900/30 rounded-xl p-5 shadow-sm border border-indigo-200 dark:border-indigo-800 mb-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-indigo-500 rounded-xl">
                                <Sparkles className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-indigo-600 dark:text-indigo-400 mb-1">
                                    🌟 Best Account Recommendation
                                </h3>
                                <p className="text-lg font-bold text-gray-900 dark:text-white">
                                    {bestAccount.best_account.email}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    Project: {bestAccount.best_account.project_id}
                                </p>
                            </div>
                        </div>
                        <div className="text-right">
                            <div className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">
                                {Math.round(bestAccount.best_account.average_quota * 100)}%
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                Avg Quota | Overall: {Math.round(bestAccount.overall_average * 100)}%
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Quota Matrix */}
            <div className="mb-6">
                <QuotaMatrix />
            </div>

            {/* Account Pool Table */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                <div className="p-4 border-b border-gray-100 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Account Pool</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 dark:bg-gray-700">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Email</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Project ID</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Token Expires</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                            {poolStatus?.accounts.map((acc) => (
                                <tr key={acc.account_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{acc.email}</td>
                                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 font-mono">{acc.project_id || '-'}</td>
                                    <td className="px-4 py-3 text-sm">
                                        <span className={`${acc.expires_in_seconds < 300 ? 'text-orange-500' : 'text-green-500'}`}>
                                            {Math.round(acc.expires_in_seconds / 60)} min
                                        </span>
                                    </td>
                                </tr>
                            ))}
                            {!poolStatus?.accounts.length && (
                                <tr>
                                    <td colSpan={3} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                                        No accounts in pool. Add an account to get started.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
