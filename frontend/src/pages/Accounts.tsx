import { useEffect, useState, useRef } from 'react';
import { Trash2, RefreshCw, Plus, ExternalLink, Copy, Check, Upload, Download, LayoutGrid, List } from 'lucide-react';
import { useAccountStore } from '../stores/useAccountStore';
import api from '../services/api';

export default function Accounts() {
    const { accounts, fetchAccounts, deleteAccount, reloadPool } = useAccountStore();
    const [showAddDialog, setShowAddDialog] = useState(false);
    const [newEmail, setNewEmail] = useState('');
    const [newRefreshToken, setNewRefreshToken] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchAccounts();
    }, []);

    const handleAddAccount = async () => {
        if (!newEmail || !newRefreshToken) return;

        setIsSubmitting(true);
        try {
            await api.importToken({ email: newEmail, refresh_token: newRefreshToken });
            await fetchAccounts();
            await reloadPool();
            setShowAddDialog(false);
            setNewEmail('');
            setNewRefreshToken('');
        } catch (e) {
            alert(`Error: ${e}`);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (id: string, email: string) => {
        if (!confirm(`Delete account ${email}?`)) return;
        try {
            await deleteAccount(id);
        } catch (e) {
            alert(`Error: ${e}`);
        }
    };

    const handleStartOAuth = async () => {
        try {
            const { auth_url } = await api.startOAuth();
            window.open(auth_url, '_blank');
        } catch (e) {
            alert(`Error: ${e}`);
        }
    };

    const handleStartOAuthRelay = async () => {
        // Relay mode: for production environments where OAuth redirect_uri is localhost
        // User must run oauth_relay.py locally before using this
        try {
            const { auth_url } = await api.startOAuthRelay();
            window.open(auth_url, '_blank');
        } catch (e) {
            alert(`Error: ${e}`);
        }
    };

    const handleCopy = (text: string, id: string) => {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    const handleExport = () => {
        const data = JSON.stringify({ accounts }, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `antigravity_accounts_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleImportClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            await api.importJsonFile(file);
            await fetchAccounts();
            await reloadPool();
            alert('Accounts imported successfully!');
        } catch (e) {
            alert(`Import failed: ${e}`);
        }

        // Reset input
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div className="p-6 max-w-[95%] mx-auto">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Accounts</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Manage your Google accounts for API proxy
                    </p>
                </div>
                <div className="flex gap-2 items-center">
                    {/* View Toggle */}
                    <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                        <button
                            onClick={() => setViewMode('list')}
                            className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-white dark:bg-gray-600 shadow-sm' : 'text-gray-500'}`}
                            title="List View"
                        >
                            <List className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setViewMode('grid')}
                            className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-white dark:bg-gray-600 shadow-sm' : 'text-gray-500'}`}
                            title="Grid View"
                        >
                            <LayoutGrid className="w-4 h-4" />
                        </button>
                    </div>
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept=".json"
                        className="hidden"
                    />
                    <button
                        onClick={handleImportClick}
                        className="px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2"
                        title="Import JSON"
                    >
                        <Upload className="w-4 h-4" />
                        Import
                    </button>
                    <button
                        onClick={handleExport}
                        className="px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2"
                        title="Export JSON"
                    >
                        <Download className="w-4 h-4" />
                        Export
                    </button>
                    <button
                        onClick={handleStartOAuth}
                        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2"
                        title="Direct OAuth (for local/dev)"
                    >
                        <ExternalLink className="w-4 h-4" />
                        Login with Google
                    </button>
                    <button
                        onClick={handleStartOAuthRelay}
                        className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 flex items-center gap-2"
                        title="Relay OAuth (run oauth_relay.py locally first)"
                    >
                        <ExternalLink className="w-4 h-4" />
                        Relay Login
                    </button>
                    <button
                        onClick={() => setShowAddDialog(true)}
                        className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" />
                        Add Token
                    </button>
                </div>
            </div>

            {/* Accounts View */}
            {viewMode === 'list' ? (
                /* List View (Table) */
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Email</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tier</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Project ID</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Token Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                                {accounts.map((acc) => {
                                    const expiresIn = acc.token.expiry_timestamp - Math.floor(Date.now() / 1000);
                                    const isExpired = expiresIn < 0;
                                    const isExpiringSoon = expiresIn < 300 && !isExpired;

                                    return (
                                        <tr key={acc.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                            <td className="px-4 py-3">
                                                <div className="text-sm font-medium text-gray-900 dark:text-white">{acc.email}</div>
                                                <div className="text-xs text-gray-500 dark:text-gray-400">{acc.name || acc.id}</div>
                                            </td>
                                            <td className="px-4 py-3">
                                                {acc.token.subscription_tier ? (
                                                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${acc.token.subscription_tier.toLowerCase().includes('ultra')
                                                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                                                        : acc.token.subscription_tier.toLowerCase().includes('pro')
                                                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                                            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                                                        }`}>
                                                        {acc.token.subscription_tier.toUpperCase()}
                                                    </span>
                                                ) : (
                                                    <span className="text-xs text-gray-400">—</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-1">
                                                    <span className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                                                        {acc.token.project_id || '-'}
                                                    </span>
                                                    {acc.token.project_id && (
                                                        <button
                                                            onClick={() => handleCopy(acc.token.project_id!, acc.id)}
                                                            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded"
                                                        >
                                                            {copiedId === acc.id ? (
                                                                <Check className="w-3 h-3 text-green-500" />
                                                            ) : (
                                                                <Copy className="w-3 h-3 text-gray-400" />
                                                            )}
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${isExpired
                                                    ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                                    : isExpiringSoon
                                                        ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                                                        : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                                    }`}>
                                                    {isExpired ? 'Expired' : isExpiringSoon ? 'Expiring' : 'Valid'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <button
                                                    onClick={() => handleDelete(acc.id, acc.email)}
                                                    className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
                                                    title="Delete"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                                {!accounts.length && (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">
                                            No accounts yet. Click "Login with Google" or "Add Token" to get started.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                /* Grid View (Cards) */
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {accounts.map((acc) => {
                        const expiresIn = acc.token.expiry_timestamp - Math.floor(Date.now() / 1000);
                        const isExpired = expiresIn < 0;
                        const isExpiringSoon = expiresIn < 300 && !isExpired;

                        return (
                            <div key={acc.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4 hover:shadow-md transition-shadow">
                                <div className="flex justify-between items-start mb-3">
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm font-semibold text-gray-900 dark:text-white truncate">{acc.email}</div>
                                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate font-mono mt-0.5">
                                            {acc.token.project_id || 'No project ID'}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleDelete(acc.id, acc.email)}
                                        className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg shrink-0 ml-2"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>

                                <div className="flex items-center gap-2">
                                    {acc.token.subscription_tier ? (
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${acc.token.subscription_tier.toLowerCase().includes('ultra')
                                            ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                                            : acc.token.subscription_tier.toLowerCase().includes('pro')
                                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                                            }`}>
                                            {acc.token.subscription_tier.toUpperCase()}
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                                            UNKNOWN
                                        </span>
                                    )}
                                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${isExpired
                                        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                        : isExpiringSoon
                                            ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                                            : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                        }`}>
                                        {isExpired ? 'Expired' : isExpiringSoon ? 'Expiring' : 'Valid'}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                    {!accounts.length && (
                        <div className="col-span-full bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-12 text-center text-gray-500 dark:text-gray-400">
                            No accounts yet. Click "Login with Google" or "Add Token" to get started.
                        </div>
                    )}
                </div>
            )}

            {/* Add Token Dialog */}
            {showAddDialog && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md p-6">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Add Account Token</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
                                <input
                                    type="email"
                                    value={newEmail}
                                    onChange={(e) => setNewEmail(e.target.value)}
                                    placeholder="user@gmail.com"
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Refresh Token</label>
                                <textarea
                                    value={newRefreshToken}
                                    onChange={(e) => setNewRefreshToken(e.target.value)}
                                    placeholder="1//..."
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-2 mt-6">
                            <button
                                onClick={() => setShowAddDialog(false)}
                                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAddAccount}
                                disabled={isSubmitting || !newEmail || !newRefreshToken}
                                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
                            >
                                {isSubmitting && <RefreshCw className="w-4 h-4 animate-spin" />}
                                Add
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
