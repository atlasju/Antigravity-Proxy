/**
 * Login Page
 * 
 * User authentication page
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Lock, User, Zap } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';

export default function Login() {
    const navigate = useNavigate();
    const { login } = useAuthStore();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await login(username, password);
            navigate('/');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl mb-4 shadow-lg">
                        <Zap className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-white">Antigravity Proxy</h1>
                    <p className="text-gray-400 mt-1">Sign in to continue</p>
                </div>

                {/* Login Form */}
                <form onSubmit={handleSubmit} className="bg-gray-800 rounded-2xl p-8 shadow-xl border border-gray-700">
                    {error && (
                        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <div className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Username
                            </label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                                    placeholder="Enter username"
                                    required
                                    autoFocus
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full pl-10 pr-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                                    placeholder="Enter password"
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium rounded-lg hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Signing in...
                                </>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </div>
                </form>

                <p className="text-center text-gray-500 text-sm mt-6">
                    Antigravity Proxy v0.1.0
                </p>
            </div >
        </div >
    );
}
