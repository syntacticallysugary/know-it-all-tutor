import { Link } from 'react-router-dom'
import { User, LogOut } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const Navbar = () => {
  const { user, signOut } = useAuth()

  const handleSignOut = async () => {
    await signOut()
  }

  return (
    <nav className="border-b px-6 py-4" style={{ backgroundColor: '#111827', borderColor: '#1E2940' }}>
      <div className="flex items-center justify-between">
        <Link to="/app/dashboard" className="text-xl font-bold text-primary-600">
          Know-It-All Tutor
        </Link>

        <div className="flex items-center space-x-4">
          <span className="text-sm" style={{ color: '#94A3B8' }}>
            Welcome, {user?.username || user?.email || 'User'}
          </span>

          <Link
            to="/app/profile"
            className="p-2 hover:text-primary-400 transition-colors"
            style={{ color: '#94A3B8' }}
          >
            <User size={20} />
          </Link>

          <button
            onClick={handleSignOut}
            className="p-2 hover:text-error-400 transition-colors"
            style={{ color: '#94A3B8' }}
          >
            <LogOut size={20} />
          </button>
        </div>
      </div>
    </nav>
  )
}

export default Navbar