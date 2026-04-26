import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiClient, Domain } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const DomainLibrary = () => {
  const { user } = useAuth()
  const [domains, setDomains] = useState<Domain[]>([])
  const [filteredDomains, setFilteredDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'name' | 'created_at' | 'term_count'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    const fetchDomains = async () => {
      try {
        setLoading(true)
        const data = await apiClient.getDomains()
        setDomains(data)
        setFilteredDomains(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load domains')
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      fetchDomains()
    }
  }, [user])

  // Filter and sort domains
  useEffect(() => {
    let filtered = domains.filter(domain =>
      domain.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      domain.description.toLowerCase().includes(searchTerm.toLowerCase())
    )

    // Sort domains
    filtered.sort((a, b) => {
      let aValue: any, bValue: any

      switch (sortBy) {
        case 'name':
          aValue = a.name.toLowerCase()
          bValue = b.name.toLowerCase()
          break
        case 'created_at':
          aValue = new Date(a.created_at || 0)
          bValue = new Date(b.created_at || 0)
          break
        case 'term_count':
          aValue = a.term_count
          bValue = b.term_count
          break
        default:
          return 0
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

    setFilteredDomains(filtered)
  }, [domains, searchTerm, sortBy, sortOrder])

  const handleDeleteDomain = async (domainId: string) => {
    if (!confirm('Are you sure you want to delete this domain? This action cannot be undone.')) {
      return
    }

    try {
      await apiClient.deleteDomain(domainId)
      setDomains(domains.filter(d => d.id !== domainId))
    } catch (err) {
      alert('Failed to delete domain: ' + (err instanceof Error ? err.message : 'Unknown error'))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6">
        <div className="text-center text-red-600">
          <p className="font-semibold">Error loading domains</p>
          <p className="text-sm mt-1">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="btn btn-primary mt-4"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">Domain Library</h1>
            <p className="page-subtitle">
              Browse and manage your knowledge domains.
            </p>
          </div>
          <Link to="/app/domains/create" className="btn btn-primary">
            Create Domain
          </Link>
        </div>
      </div>
      
      {domains.length > 0 ? (
        <>
          {/* Search and Filter Controls */}
          <div className="card p-6 mb-6">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="flex-1">
                <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
                  Search domains
                </label>
                <input
                  type="text"
                  id="search"
                  placeholder="Search by name or description..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input w-full"
                />
              </div>

              {/* Sort By */}
              <div className="sm:w-48">
                <label htmlFor="sortBy" className="block text-sm font-medium text-gray-700 mb-1">
                  Sort by
                </label>
                <select
                  id="sortBy"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="input w-full"
                >
                  <option value="created_at">Date Created</option>
                  <option value="name">Name</option>
                  <option value="term_count">Term Count</option>
                </select>
              </div>

              {/* Sort Order */}
              <div className="sm:w-32">
                <label htmlFor="sortOrder" className="block text-sm font-medium text-gray-700 mb-1">
                  Order
                </label>
                <select
                  id="sortOrder"
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value as any)}
                  className="input w-full"
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>

            {/* Results Summary */}
            <div className="mt-4 text-sm text-gray-600">
              Showing {filteredDomains.length} of {domains.length} domains
              {searchTerm && (
                <span> matching "{searchTerm}"</span>
              )}
            </div>
          </div>

          {/* Domain Grid */}
          {filteredDomains.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredDomains.map((domain) => (
                <DomainCard 
                  key={domain.id} 
                  domain={domain} 
                  onDelete={handleDeleteDomain}
                />
              ))}
            </div>
          ) : (
            <div className="card p-6">
              <div className="text-center py-8">
                <p className="text-gray-500 mb-2">No domains found</p>
                {searchTerm ? (
                  <p className="text-sm text-gray-400">
                    Try adjusting your search terms or{' '}
                    <button 
                      onClick={() => setSearchTerm('')}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      clear the search
                    </button>
                  </p>
                ) : (
                  <Link to="/app/domains/create" className="btn btn-primary">
                    Create Your First Domain
                  </Link>
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="card p-6">
          <div className="text-center py-12">
            <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No domains yet</h3>
            <p className="text-gray-500 mb-6">
              Create your first knowledge domain to start learning and tracking your progress.
            </p>
            <Link to="/app/domains/create" className="btn btn-primary">
              Create Your First Domain
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

interface DomainCardProps {
  domain: Domain
  onDelete: (domainId: string) => void
}

const DomainCard = ({ domain, onDelete }: DomainCardProps) => {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <div className="card p-6 relative">
      {/* Menu Button */}
      <div className="absolute top-4 right-4">
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="p-1 text-gray-400 hover:text-gray-600 rounded"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </button>
        
        {showMenu && (
          <div className="absolute right-0 mt-1 w-52 bg-white rounded-md shadow-lg border border-gray-200 z-10">
            <Link
              to={`/app/quiz/${domain.id}?mode=forward`}
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setShowMenu(false)}
            >
              Quiz: Define Terms
            </Link>
            <Link
              to={`/app/quiz/${domain.id}?mode=reverse`}
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setShowMenu(false)}
            >
              Quiz: Name Terms
            </Link>
            <Link
              to={`/app/domains/${domain.id}/edit`}
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setShowMenu(false)}
            >
              Edit Domain
            </Link>
            <button
              onClick={() => {
                setShowMenu(false)
                onDelete(domain.id)
              }}
              className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              Delete Domain
            </button>
          </div>
        )}
      </div>

      {/* Domain Content */}
      <div className="pr-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{domain.name}</h3>
        <p className="text-gray-600 text-sm mb-4 line-clamp-3">{domain.description}</p>
        
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{domain.term_count} terms</span>
          {domain.created_at && (
            <span>
              Created {new Date(domain.created_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-4 pt-4 border-t border-gray-100 flex gap-2">
        <Link
          to={`/app/quiz/${domain.id}?mode=forward`}
          className="btn btn-primary btn-sm flex-1"
        >
          Define Terms
        </Link>
        <Link
          to={`/app/quiz/${domain.id}?mode=reverse`}
          className="btn btn-secondary btn-sm flex-1"
        >
          Name Terms
        </Link>
      </div>
    </div>
  )
}

export default DomainLibrary