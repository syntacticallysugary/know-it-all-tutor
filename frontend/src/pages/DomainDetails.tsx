import { useState, useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { apiClient, Domain } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

function subjectOf(name: string): string {
  const sep = name.indexOf(' — ')
  return sep !== -1 ? name.slice(0, sep) : name
}

function labelOf(name: string): string {
  const sep = name.indexOf(' — ')
  return sep !== -1 ? name.slice(sep + 3) : name
}

const DomainDetails = () => {
  const { subject } = useParams<{ subject: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [subDomains, setSubDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user || !subject) return
    const fetch = async () => {
      try {
        setLoading(true)
        const all = await apiClient.getDomains()
        setSubDomains(all.filter(d => subjectOf(d.name) === subject))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [user, subject])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6 text-center text-red-600">
        <p className="font-semibold">Error loading topics</p>
        <p className="text-sm mt-1">{error}</p>
        <button onClick={() => window.location.reload()} className="btn btn-primary mt-4">Retry</button>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/app/domains')}
            className="text-gray-500 hover:text-gray-700 flex items-center gap-1 text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Domain Library
          </button>
        </div>
        <h1 className="page-title mt-2">{subject}</h1>
        <p className="page-subtitle">
          {subDomains.length} topic{subDomains.length !== 1 ? 's' : ''}
        </p>
      </div>

      {subDomains.length === 0 ? (
        <div className="card p-6 text-center py-12 text-gray-500">
          No topics found for this domain.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {subDomains.map(domain => (
            <div key={domain.id} className="card p-6 flex flex-col">
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                {labelOf(domain.name)}
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                {domain.term_count} term{domain.term_count !== 1 ? 's' : ''}
              </p>

              <div className="mt-auto flex gap-2">
                <Link
                  to={`/app/quiz/${domain.id}?mode=reverse`}
                  className="btn btn-primary btn-sm flex-1"
                >
                  Name Terms
                </Link>
                <Link
                  to={`/app/quiz/${domain.id}?mode=forward`}
                  className="btn btn-secondary btn-sm flex-1"
                >
                  Define Terms
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DomainDetails
