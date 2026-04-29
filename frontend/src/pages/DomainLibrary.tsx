import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiClient, Domain } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

function subjectOf(name: string): string {
  const sep = name.indexOf(' — ')
  return sep !== -1 ? name.slice(0, sep) : name
}

interface SubjectGroup {
  subject: string
  domains: Domain[]
  totalTerms: number
}

function groupDomains(domains: Domain[]): SubjectGroup[] {
  const map = new Map<string, Domain[]>()
  for (const d of domains) {
    const s = subjectOf(d.name)
    if (!map.has(s)) map.set(s, [])
    map.get(s)!.push(d)
  }
  return Array.from(map.entries()).map(([subject, doms]) => ({
    subject,
    domains: doms,
    totalTerms: doms.reduce((sum, d) => sum + d.term_count, 0),
  }))
}

const DomainLibrary = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [groups, setGroups] = useState<SubjectGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    const fetch = async () => {
      try {
        setLoading(true)
        const data = await apiClient.getDomains()
        setGroups(groupDomains(data))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load domains')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [user])

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
          <button onClick={() => window.location.reload()} className="btn btn-primary mt-4">Retry</button>
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
            <p className="page-subtitle">Select a domain to explore its topics.</p>
          </div>
          <Link to="/app/domains/create" className="btn btn-primary">
            Create Domain
          </Link>
        </div>
      </div>

      {groups.length === 0 ? (
        <div className="card p-6">
          <div className="text-center py-12">
            <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No domains yet</h3>
            <p className="text-gray-500 mb-6">
              Create your first knowledge domain to start learning.
            </p>
            <Link to="/app/domains/create" className="btn btn-primary">
              Create Your First Domain
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {groups.map(({ subject, domains, totalTerms }) => (
            <div key={subject} className="card p-6 flex flex-col">
              <h3 className="text-xl font-semibold text-gray-900 mb-1">{subject}</h3>
              <p className="text-sm text-gray-500 mb-6">
                {domains.length} topic{domains.length !== 1 ? 's' : ''} · {totalTerms} term{totalTerms !== 1 ? 's' : ''}
              </p>
              <div className="mt-auto">
                <button
                  onClick={() => navigate(`/app/domains/detail/${encodeURIComponent(subject)}`)}
                  className="btn btn-primary w-full"
                >
                  Select Topic
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DomainLibrary
