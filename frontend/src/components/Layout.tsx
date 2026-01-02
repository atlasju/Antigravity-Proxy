import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { Home, Users, Settings, Zap, Network, LogOut, Image as ImageIcon, BarChart3 } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';

const navItems = [
    { to: '/', icon: Home, label: 'Dashboard' },
    { to: '/accounts', icon: Users, label: 'Accounts' },
    { to: '/proxy', icon: Network, label: 'API Proxy' },
    { to: '/image-gen', icon: ImageIcon, label: 'Image Gen' },
    { to: '/statistics', icon: BarChart3, label: 'Statistics' },
    { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout() {
    const { logout } = useAuthStore();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
            {/* Sidebar */}
            <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
                {/* Logo */}
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                            <Zap className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-bold text-gray-900 dark:text-white">Antigravity</span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">AI Gateway</p>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-1">
                    {navItems.map(({ to, icon: Icon, label }) => (
                        <NavLink
                            key={to}
                            to={to}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive
                                    ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400'
                                    : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-700'
                                }`
                            }
                        >
                            <Icon className="w-5 h-5" />
                            {label}
                        </NavLink>
                    ))}
                </nav>

                {/* Footer */}
                <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30 transition-colors"
                    >
                        <LogOut className="w-5 h-5" />
                        Logout
                    </button>
                    <div className="mt-4 text-xs text-center text-gray-500 dark:text-gray-400">
                        v0.1.0
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto">
                <Outlet />
            </main>
        </div>
    );
}
