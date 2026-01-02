import { useEffect, useState } from 'react';
import { RefreshCw, Copy, Check, Server, Cpu, Settings as SettingsIcon, Key, Loader2, Trash2, Plus, Route } from 'lucide-react';
import { useAccountStore } from '../stores/useAccountStore';
import { useAuthStore } from '../stores/useAuthStore';
import { api } from '../services/api';

// --- Sub-Components ---

function ModelMappingSection() {
    const [mappings, setMappings] = useState<{ id: number; source_model: string; target_model: string; description: string }[]>([]);
    const [isLoadings, setIsLoadings] = useState(false);
    const [isAdding, setIsAdding] = useState(false);

    // Form state
    const [sourceModel, setSourceModel] = useState('');
    const [targetModel, setTargetModel] = useState('');
    const [description, setDescription] = useState('');

    useEffect(() => {
        fetchMappings();
    }, []);

    const fetchMappings = async () => {
        setIsLoadings(true);
        try {
            const data = await api.getMappings();
            setMappings(data);
        } catch (e) {
            console.error('Failed to fetch mappings', e);
        } finally {
            setIsLoadings(false);
        }
    };

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.createMapping(sourceModel, targetModel, description);
            setSourceModel('');
            setTargetModel('');
            setDescription('');
            setIsAdding(false);
            fetchMappings();
        } catch (e) {
            alert('Failed to create mapping');
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this mapping?')) return;
        try {
            await api.deleteMapping(id);
            fetchMappings();
        } catch (e) {
            alert('Failed to delete mapping');
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                        <Route className="w-5 h-5 text-blue-500" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Model Router</h2>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Map generic model names to specific models</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsAdding(!isAdding)}
                    className="px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-1"
                >
                    <Plus className="w-4 h-4" />
                    Add Mapping
                </button>
            </div>

            {/* Add Form */}
            {isAdding && (
                <form onSubmit={handleAdd} className="mb-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Incoming Model (Source)</label>
                            <input
                                type="text"
                                value={sourceModel}
                                onChange={e => setSourceModel(e.target.value)}
                                placeholder="e.g. gpt-4"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-sm"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Target Model (Destination)</label>
                            <input
                                type="text"
                                value={targetModel}
                                onChange={e => setTargetModel(e.target.value)}
                                placeholder="e.g. gemini-1.5-pro"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-sm"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Description (Optional)</label>
                            <input
                                type="text"
                                value={description}
                                onChange={e => setDescription(e.target.value)}
                                placeholder="Redirect GPT-4 to Gemini"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-sm"
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-2">
                        <button
                            type="button"
                            onClick={() => setIsAdding(false)}
                            className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-200 rounded"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
                        >
                            Save Mapping
                        </button>
                    </div>
                </form>
            )}

            {/* List */}
            <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Source</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Target</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Description</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Action</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {isLoadings ? (
                            <tr>
                                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                                    <div className="flex justify-center items-center gap-2">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span>Loading mappings...</span>
                                    </div>
                                </td>
                            </tr>
                        ) : mappings.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="px-4 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                                    No custom mappings defined.
                                </td>
                            </tr>
                        ) : (
                            mappings.map((m) => (
                                <tr key={m.id}>
                                    <td className="px-4 py-3 text-sm font-mono text-indigo-600 dark:text-indigo-400 font-medium">
                                        {m.source_model}
                                    </td>
                                    <td className="px-4 py-3 text-sm font-mono text-gray-600 dark:text-gray-300">
                                        {m.target_model}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                                        {m.description || '-'}
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        <button
                                            onClick={() => handleDelete(m.id)}
                                            className="text-red-500 hover:text-red-700"
                                            title="Delete"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function ChangePasswordForm() {
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setMessage('');

        if (newPassword !== confirmPassword) {
            setStatus('error');
            setMessage('New passwords do not match');
            return;
        }

        if (newPassword.length < 6) {
            setStatus('error');
            setMessage('Password must be at least 6 characters');
            return;
        }

        setStatus('loading');
        try {
            await api.changePassword(currentPassword, newPassword);
            setStatus('success');
            setMessage('Password changed successfully');
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (e: any) {
            setStatus('error');
            setMessage(e.message || 'Failed to change password');
        }
    };

    return (
        <form onSubmit={handleSubmit} className="max-w-md space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Current Password</label>
                <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white"
                    required
                />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">New Password</label>
                    <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white"
                        required
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Confirm New</label>
                    <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white"
                        required
                    />
                </div>
            </div>

            {message && (
                <div className={`text-sm p-2 rounded ${status === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                    {message}
                </div>
            )}

            <button
                type="submit"
                disabled={status === 'loading'}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 flex items-center gap-2"
            >
                {status === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
                Change Password
            </button>
        </form>
    );
}

// --- Main Page Component ---

export default function Settings() {
    const [activeTab, setActiveTab] = useState<'general' | 'models' | 'security'>('general');

    const tabs = [
        { id: 'general', label: 'General', icon: SettingsIcon },
        { id: 'models', label: 'Models', icon: Cpu },
        { id: 'security', label: 'Security', icon: Key },
    ];

    return (
        <div className="flex h-[calc(100vh-4rem)]">
            {/* Sidebar */}
            <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
                <div className="p-6">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
                </div>

                <nav className="flex-1 px-4 space-y-1">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id
                                ? 'bg-indigo-50 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400'
                                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                                }`}
                        >
                            <tab.icon className="w-5 h-5" />
                            {tab.label}
                        </button>
                    ))}
                </nav>

                <div className="p-4 border-t border-gray-200 dark:border-gray-700 opacity-0 pointer-events-none">
                    {/* Placeholder to keep layout consistent if needed, or remove completely */}
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-8">
                {activeTab === 'general' && <SettingsGeneral />}
                {activeTab === 'models' && <SettingsModels />}
                {activeTab === 'security' && <SettingsSecurity />}
            </div>
        </div>
    );
}

function SettingsGeneral() {
    const { user, regenerateApiKey } = useAuthStore();
    // Default to current page origin (works in both dev and production)
    const [apiBase, setApiBase] = useState(window.location.origin);
    const [copied, setCopied] = useState<string | null>(null);
    const [isRegenerating, setIsRegenerating] = useState(false);

    const handleCopy = (text: string, key: string) => {
        navigator.clipboard.writeText(text);
        setCopied(key);
        setTimeout(() => setCopied(null), 2000);
    };

    const handleRegenerateApiKey = async () => {
        if (!confirm('Are you sure you want to regenerate your API key? The old key will stop working immediately.')) {
            return;
        }
        setIsRegenerating(true);
        try {
            await regenerateApiKey();
        } catch (e) {
            alert('Failed to regenerate API key');
        } finally {
            setIsRegenerating(false);
        }
    };

    return (
        <div className="max-w-[95%] space-y-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">General Settings</h2>

            {/* API Key Management */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-amber-50 dark:bg-amber-900/30 rounded-lg">
                        <Key className="w-5 h-5 text-amber-500" />
                    </div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">API Key</h2>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Your API Key (use this for external applications)
                        </label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={user?.api_key || ''}
                                readOnly
                                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                            />
                            <button
                                onClick={() => handleCopy(user?.api_key || '', 'apikey')}
                                className="px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
                                title="Copy API Key"
                            >
                                {copied === 'apikey' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-gray-500" />}
                            </button>
                        </div>
                    </div>

                    <button
                        onClick={handleRegenerateApiKey}
                        disabled={isRegenerating}
                        className="px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {isRegenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        Regenerate API Key
                    </button>

                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        Use this API key in the <code>Authorization: Bearer {'<api_key>'}</code> header when calling the proxy endpoints.
                    </p>
                </div>
            </div>

            {/* API Configuration */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-indigo-50 dark:bg-indigo-900/30 rounded-lg">
                        <Server className="w-5 h-5 text-indigo-500" />
                    </div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">API Configuration</h2>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            API Base URL
                        </label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={apiBase}
                                onChange={(e) => setApiBase(e.target.value)}
                                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                            />
                            <button
                                onClick={() => handleCopy(apiBase, 'base')}
                                className="px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
                            >
                                {copied === 'base' ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-gray-500" />}
                            </button>
                        </div>
                    </div>

                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">OpenAI-compatible Endpoint:</p>
                        <code className="text-sm text-indigo-600 dark:text-indigo-400 font-mono">
                            {apiBase}/v1/chat/completions
                        </code>
                    </div>

                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Claude-compatible Endpoint:</p>
                        <code className="text-sm text-indigo-600 dark:text-indigo-400 font-mono">
                            {apiBase}/v1/messages
                        </code>
                    </div>

                    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Gemini-compatible Endpoint (Native):</p>
                        <code className="text-sm text-indigo-600 dark:text-indigo-400 font-mono">
                            {apiBase}/v1beta
                        </code>
                    </div>
                </div>
            </div>


        </div>
    );
}

function SettingsModels() {
    const { availableModels, fetchAvailableModels } = useAccountStore();
    const [isRefreshing, setIsRefreshing] = useState(false);

    useEffect(() => {
        fetchAvailableModels();
    }, []);

    const handleRefreshModels = async () => {
        setIsRefreshing(true);
        try {
            await fetchAvailableModels();
        } finally {
            setIsRefreshing(false);
        }
    };

    // User's preferred models
    const preferredModels = [
        'claude-opus-4-5-thinking',
        'claude-sonnet-4-5-thinking',
        'gemini-3-flash',
        'gemini-3-pro-high',
        'gemini-3-pro-low',
        'gpt-oss-120b-medium',
    ];

    return (
        <div className="max-w-[95%] space-y-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Model Configuration</h2>

            <ModelMappingSection />

            {/* Available Models */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
                            <Cpu className="w-5 h-5 text-purple-500" />
                        </div>
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Available Models</h2>
                    </div>
                    <button
                        onClick={handleRefreshModels}
                        disabled={isRefreshing}
                        className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg flex items-center gap-1"
                    >
                        <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>

                <div className="mb-4">
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Preferred Models:</p>
                    <div className="flex flex-wrap gap-2">
                        {preferredModels.map((model) => (
                            <span
                                key={model}
                                className="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full text-sm font-medium"
                            >
                                {model}
                            </span>
                        ))}
                    </div>
                </div>

                {availableModels.length > 0 && (
                    <div>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">All Available ({availableModels.length}):</p>
                        <div className="flex flex-wrap gap-2">
                            {availableModels.map((model) => (
                                <span
                                    key={model}
                                    className={`px-3 py-1 rounded-full text-sm ${preferredModels.includes(model)
                                        ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                                        }`}
                                >
                                    {model}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

function SettingsSecurity() {
    return (
        <div className="max-w-[95%] space-y-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Security Settings</h2>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-red-50 dark:bg-red-900/30 rounded-lg">
                        <Key className="w-5 h-5 text-red-500" />
                    </div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Account Security</h2>
                </div>

                <ChangePasswordForm />
            </div>
        </div>
    );
}
