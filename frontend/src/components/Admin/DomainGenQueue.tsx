import React, { useEffect, useRef, useState } from 'react'
import { QueueListIcon } from '@heroicons/react/24/outline'
import { adminApiClient, DomainGenJob } from '../../services/api'

interface Props {
  newJob: DomainGenJob | null
  onSelectJob: (job: DomainGenJob) => void
}

const STATUS_STYLES: Record<DomainGenJob['status'], string> = {
  pending: 'bg-yellow-50 text-yellow-700 ring-yellow-200',
  running: 'bg-blue-50 text-blue-700 ring-blue-200',
  complete: 'bg-green-50 text-green-700 ring-green-200',
  failed: 'bg-red-50 text-red-700 ring-red-200',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

const DomainGenQueue: React.FC<Props> = ({ newJob, onSelectJob }) => {
  const [jobs, setJobs] = useState<DomainGenJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = async () => {
    try {
      setJobs(await adminApiClient.listDomainGenJobs())
      setError(null)
    } catch (e: any) {
      setError(e.message || 'Failed to load jobs.')
    } finally {
      setLoading(false)
    }
  }

  // Merge a newly created job immediately so the user sees it without waiting
  useEffect(() => {
    if (!newJob) return
    setJobs(prev => {
      if (prev.some(j => j.id === newJob.id)) return prev
      return [newJob, ...prev]
    })
  }, [newJob])

  // Poll every 20 seconds while any job is pending or running
  useEffect(() => {
    load()
    pollRef.current = setInterval(() => {
      const hasActive = jobs.some(j => j.status === 'pending' || j.status === 'running')
      if (hasActive) load()
    }, 20000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-gray-500">Loading jobs…</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Generation Queue</h2>
        <button onClick={load} className="text-sm text-primary-600 hover:text-primary-500">
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <QueueListIcon className="h-12 w-12 mb-3" />
          <p className="text-base font-medium">No jobs yet</p>
          <p className="text-sm mt-1">Use the Define tab to queue a generation job.</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden">
          {jobs.map(job => (
            <div
              key={job.id}
              className="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{job.topic}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  #{job.id} · {job.total_terms} terms · {formatDate(job.created_at)}
                  {job.hints && <span className="ml-1 italic">"{job.hints}"</span>}
                </p>
                {job.status === 'failed' && job.error_message && (
                  <p className="text-xs text-red-600 mt-0.5 truncate">{job.error_message}</p>
                )}
              </div>
              <div className="flex items-center gap-3 ml-4 shrink-0">
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[job.status]}`}>
                  {job.status === 'running' ? 'Running…' : job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                </span>
                {job.status === 'complete' && (
                  <button
                    onClick={() => onSelectJob(job)}
                    className="text-xs text-primary-600 hover:text-primary-500 font-medium"
                  >
                    Review →
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DomainGenQueue
