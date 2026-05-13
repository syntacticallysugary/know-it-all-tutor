import React, { useEffect, useState } from 'react'
import { CheckIcon, XMarkIcon, UserGroupIcon } from '@heroicons/react/24/outline'
import { adminApiClient, PendingUser } from '../../services/api'

type ActionState = { type: 'approving' | 'denying'; username: string } | null

const PendingUsers: React.FC = () => {
  const [users, setUsers] = useState<PendingUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState<ActionState>(null)
  const [denyReason, setDenyReason] = useState('')
  const [denyTarget, setDenyTarget] = useState<PendingUser | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      setUsers(await adminApiClient.getPendingUsers())
    } catch (e: any) {
      setError(e.message || 'Failed to load pending users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleApprove = async (user: PendingUser) => {
    setAction({ type: 'approving', username: user.username })
    try {
      await adminApiClient.approveUser(user.username)
      setUsers(prev => prev.filter(u => u.username !== user.username))
    } catch (e: any) {
      setError(e.message || 'Failed to approve user')
    } finally {
      setAction(null)
    }
  }

  const handleDenyConfirm = async () => {
    if (!denyTarget) return
    setAction({ type: 'denying', username: denyTarget.username })
    try {
      await adminApiClient.denyUser(denyTarget.username, denyReason)
      setUsers(prev => prev.filter(u => u.username !== denyTarget.username))
    } catch (e: any) {
      setError(e.message || 'Failed to deny user')
    } finally {
      setAction(null)
      setDenyTarget(null)
      setDenyReason('')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500">
        Loading pending registrations…
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Pending Registrations</h2>
        <button onClick={load} className="text-sm text-primary-600 hover:text-primary-500">
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {users.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <UserGroupIcon className="h-12 w-12 mb-3" />
          <p className="text-base font-medium">No pending registrations</p>
          <p className="text-sm mt-1">New sign-ups will appear here awaiting your approval.</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden">
          {users.map(user => {
            const busy = action?.username === user.username
            const displayName =
              [user.given_name, user.family_name].filter(Boolean).join(' ') || '—'
            const date = new Date(user.created_at).toLocaleDateString(undefined, {
              year: 'numeric', month: 'short', day: 'numeric',
            })
            return (
              <div key={user.username} className="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{user.email}</p>
                  <p className="text-xs text-gray-500">
                    {displayName} · Registered {date}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4 shrink-0">
                  <button
                    onClick={() => handleApprove(user)}
                    disabled={!!action}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-50"
                  >
                    <CheckIcon className="h-3.5 w-3.5" />
                    {busy && action?.type === 'approving' ? 'Approving…' : 'Approve'}
                  </button>
                  <button
                    onClick={() => setDenyTarget(user)}
                    disabled={!!action}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-50"
                  >
                    <XMarkIcon className="h-3.5 w-3.5" />
                    Deny
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Deny confirmation dialog */}
      {denyTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="text-base font-semibold text-gray-900 mb-1">Deny registration</h3>
            <p className="text-sm text-gray-600 mb-4">
              Deny <span className="font-medium">{denyTarget.email}</span>? They will receive a notification.
            </p>
            <textarea
              value={denyReason}
              onChange={e => setDenyReason(e.target.value)}
              placeholder="Optional reason (included in the email)"
              rows={3}
              className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400 mb-4 resize-none"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setDenyTarget(null); setDenyReason('') }}
                className="px-4 py-2 text-sm rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDenyConfirm}
                disabled={!!action}
                className="px-4 py-2 text-sm rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {action?.type === 'denying' ? 'Denying…' : 'Confirm Deny'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PendingUsers
