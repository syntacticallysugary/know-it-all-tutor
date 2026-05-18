import React, { useState } from 'react'
import { SparklesIcon } from '@heroicons/react/24/outline'
import { adminApiClient, DomainGenJob } from '../../services/api'

interface Props {
  onJobCreated: (job: DomainGenJob) => void
}

const DomainGenDefine: React.FC<Props> = ({ onJobCreated }) => {
  const [topic, setTopic] = useState('')
  const [hints, setHints] = useState('')
  const [totalTerms, setTotalTerms] = useState(50)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    if (!topic.trim()) {
      setError('Topic is required.')
      return
    }
    setSubmitting(true)
    try {
      const job = await adminApiClient.createDomainGenJob({
        topic: topic.trim(),
        hints: hints.trim() || undefined,
        total_terms: totalTerms,
      })
      setSuccess(`Job #${job.id} queued for "${job.topic}". Switch to the Queue tab to monitor progress.`)
      onJobCreated(job)
      setTopic('')
      setHints('')
      setTotalTerms(50)
    } catch (e: any) {
      setError(e.message || 'Failed to create job.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-lg">
      <div className="flex items-center gap-2 mb-1">
        <SparklesIcon className="h-5 w-5 text-primary-600" />
        <h2 className="text-lg font-semibold text-gray-900">Generate Domain</h2>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        The local LAN worker will research and generate quiz terms overnight using web search and Qwen.
      </p>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md text-sm">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Topic <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="e.g. Rust Programming, Roman History, Networking"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Focus hints <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <textarea
            value={hints}
            onChange={e => setHints(e.target.value)}
            placeholder="e.g. focus on the Republic era, emphasize ownership and lifetimes"
            rows={3}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Target term count
          </label>
          <input
            type="number"
            min={10}
            max={200}
            value={totalTerms}
            onChange={e => setTotalTerms(Number(e.target.value))}
            className="w-32 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
          <p className="text-xs text-gray-400 mt-1">Distributed evenly across subdomains (10–200).</p>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 px-4 rounded-md bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Queuing…' : 'Queue Generation Job'}
        </button>
      </form>
    </div>
  )
}

export default DomainGenDefine
