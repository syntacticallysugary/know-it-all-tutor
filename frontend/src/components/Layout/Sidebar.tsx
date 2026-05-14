import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  BookOpen,
  Plus,
  Settings,
  Shield
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const baseNavigation = [
  { name: 'Dashboard', href: '/app/dashboard', icon: LayoutDashboard },
  { name: 'Domain Library', href: '/app/domains', icon: BookOpen },
  { name: 'Create Domain', href: '/app/domains/create', icon: Plus },
  { name: 'Profile', href: '/app/profile', icon: Settings },
]

const adminNavigation = { name: 'Admin Panel', href: '/app/admin', icon: Shield }

const Sidebar = () => {
  const { user } = useAuth()
  const navigation = user?.isAdmin
    ? [...baseNavigation, adminNavigation]
    : baseNavigation

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen">
      <nav className="p-4 space-y-2">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
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
