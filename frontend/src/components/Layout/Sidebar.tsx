import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  BookOpen,
  Plus,
  Settings,
  Shield,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const baseNavigation = [
  { name: 'Dashboard',       href: '/app/dashboard', icon: LayoutDashboard },
  { name: 'Domain Library',  href: '/app/domains',   icon: BookOpen },
  { name: 'Create Domain',   href: '/app/domains/create', icon: Plus },
  { name: 'Generate Domain', href: '/app/generate',  icon: Sparkles },
  { name: 'Profile',         href: '/app/profile',   icon: Settings },
]

const adminNavigation = { name: 'Admin Panel', href: '/app/admin', icon: Shield }

const Sidebar = () => {
  const { user } = useAuth()
  const navigation = user?.isAdmin
    ? [...baseNavigation, adminNavigation]
    : baseNavigation

  return (
    <aside className="w-64 border-r min-h-screen" style={{ backgroundColor: '#111827', borderColor: '#1E2940' }}>
      <nav className="p-4 space-y-2">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'text-primary-400'
                  : 'hover:text-slate-100'
              }`
            }
            style={({ isActive }) => ({
              backgroundColor: isActive ? '#1E3A5F' : undefined,
              color: isActive ? '#60A5FA' : '#94A3B8',
            })}
          >
            <item.icon size={20} />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
