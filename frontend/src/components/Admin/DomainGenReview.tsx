import React, { useEffect, useState } from 'react'
import { DocumentTextIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { apiClient } from '../../services/api'
import type { DomainGenJob } from '../../services/api'

interface Props {
  jobId: string | null
}

const DomainGenReview: React.FC<Props> = ({ jobId }) => {
  const [job, setJob] = useState<DomainGenJob | null>(null)
  const [loading, setLoading] = useState(false)
  const [approving, setApproving] = useState(false)
  const [approveResult, setApproveResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) {
      setJob(null)
      setApproveResult(null)
      setError(null)
      return
    }
    setLoading(true)
    setApproveResult(null)
    setError(null)
    apiClient.getDomainGenJob(jobId)
      .then(setJob)
      .catch(e => setError(e.message || 'Failed to load job.'))
      .finally(() => setLoading(false))
  }, [jobId])

  const handleApprove = async () => {
    if (!job) return
    setApproving(true)
    setError(null)
    try {
      const result = await apiClient.approveDomainGenJob(job.id)
      setApproveResult(`Saved ${result.terms_saved} terms across ${result.domains_saved} domain(s) to your library.`)
      setJob(prev => prev ? { ...prev, status: 'approved' } : prev)
    } catch (e: any) {
      setError(e.message || 'Approval failed.')
    } finally {
      setApproving(false)
    }
  }

  if (!jobId) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <DocumentTextIcon className="h-12 w-12 mb-3" />
        <p className="text-base font-medium">No job selected</p>
        <p className="text-sm mt-1">Click "Review →" on a completed job in the Queue tab.</p>
      </div>
    )
  }

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-gray-500">Loading…</div>
  }

  if (error && !job) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
        {error}
      </div>
    )
  }

  if (!job) return null

  const output = job.output_json
  const totalTerms = output
    ? output.domains.reduce((sum, d) => sum + d.terms.length, 0)
    : 0

  return (
    <div className="max-w-xl">
      <div className="flex items-center gap-2 mb-1">
        <DocumentTextIcon className="h-5 w-5 text-primary-600" />
        <h2 className="text-lg font-semibold text-gray-900">Review: {job.topic}</h2>
      </div>
      <p className="text-sm text-gray-500 mb-5">
        {job.status === 'approved'
          ? 'This domain has already been saved to your library.'
          : 'Review the generated content, then approve to save it to your library.'}
      </p>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}
      {approveResult && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md text-sm flex items-center gap-2">
          <CheckCircleIcon className="h-4 w-4 shrink-0" />
          {approveResult}
        </div>
      )}

      <dl className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden mb-5">
        {[
          ['Topic', job.topic],
          ['Hints', job.hints || '—'],
          ['Completed', new Date(job.updated_at).toLocaleString()],
          ['Domains', output ? String(output.domains.length) : '—'],
          ['Terms', output ? String(totalTerms) : '—'],
        ].map(([label, value]) => (
          <div key={label} className="flex px-4 py-2.5 bg-white">
            <dt className="w-28 shrink-0 text-xs font-medium text-gray-500">{label}</dt>
            <dd className="text-sm text-gray-900">{value}</dd>
          </div>
        ))}
      </dl>

      {output && output.domains.length > 0 && (
        <div className="mb-5">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Subdomains</h3>
          <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden">
            {output.domains.map((domain, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-2.5 bg-white">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{domain.data.name}</p>
                  {domain.data.description && (
                    <p className="text-xs text-gray-500 truncate mt-0.5">{domain.data.description}</p>
                  )}
                </div>
                <span className="ml-4 shrink-0 text-xs text-gray-400">{domain.terms.length} terms</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {job.status !== 'approved' && (
        <button
          onClick={handleApprove}
          disabled={approving || !output}
          className="w-full py-2.5 px-4 rounded-md bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {approving ? 'Saving…' : 'Approve & Save to My Library'}
        </button>
      )}
    </div>
  )
}

export default DomainGenReview
