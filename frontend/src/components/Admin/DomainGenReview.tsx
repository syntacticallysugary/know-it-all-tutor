import React from 'react'
import { DocumentTextIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline'
import { DomainGenJob } from '../../services/api'

interface Props {
  job: DomainGenJob | null
}

const DomainGenReview: React.FC<Props> = ({ job }) => {
  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <DocumentTextIcon className="h-12 w-12 mb-3" />
        <p className="text-base font-medium">No job selected</p>
        <p className="text-sm mt-1">Click "Review →" on a completed job in the Queue tab.</p>
      </div>
    )
  }

  if (job.status !== 'complete') {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <DocumentTextIcon className="h-12 w-12 mb-3" />
        <p className="text-base font-medium">Job not complete</p>
        <p className="text-sm mt-1">This job has status <span className="font-medium text-gray-600">{job.status}</span>. Check back when it finishes.</p>
      </div>
    )
  }

  return (
    <div className="max-w-xl">
      <div className="flex items-center gap-2 mb-1">
        <DocumentTextIcon className="h-5 w-5 text-primary-600" />
        <h2 className="text-lg font-semibold text-gray-900">Review: {job.topic}</h2>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Job #{job.id} completed. Review the output file, then upload it via Batch Upload to publish the domain.
      </p>

      <dl className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden mb-6">
        {[
          ['Topic', job.topic],
          ['Hints', job.hints || '—'],
          ['Target terms', String(job.total_terms)],
          ['Completed', new Date(job.updated_at).toLocaleString()],
          ['Output file', job.output_path || '—'],
        ].map(([label, value]) => (
          <div key={label} className="flex px-4 py-3 bg-white">
            <dt className="w-32 shrink-0 text-xs font-medium text-gray-500">{label}</dt>
            <dd className="text-sm text-gray-900 break-all">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-4">
        <div className="flex items-start gap-3">
          <ArrowUpTrayIcon className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-blue-800">To publish this domain</p>
            <ol className="mt-2 text-sm text-blue-700 space-y-1 list-decimal list-inside">
              <li>Copy the output file from the LAN worker machine at the path above.</li>
              <li>Go to the <span className="font-medium">Batch Upload</span> tab.</li>
              <li>Upload the JSON file — it will be validated and imported into the domain library.</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DomainGenReview
