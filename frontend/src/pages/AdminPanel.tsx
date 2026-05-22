import { useState } from 'react'
import { Tab } from '@headlessui/react'
import {
  CloudArrowUpIcon,
  ClockIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline'
import BatchUpload from '../components/Admin/BatchUpload'
import UploadHistory from '../components/Admin/UploadHistory'
import PendingUsers from '../components/Admin/PendingUsers'

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

const AdminPanel = () => {
  const [selectedIndex, setSelectedIndex] = useState(0)

  const tabs = [
    { name: 'Pending Users',  icon: UserGroupIcon,    render: () => <PendingUsers /> },
    { name: 'Batch Upload',   icon: CloudArrowUpIcon, render: () => <BatchUpload /> },
    { name: 'Upload History', icon: ClockIcon,        render: () => <UploadHistory /> },
  ]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Admin Panel</h1>
        <p className="page-subtitle">
          Manage batch uploads, system administration, and domain generation.
        </p>
      </div>

      <div className="card p-0">
        <Tab.Group selectedIndex={selectedIndex} onChange={setSelectedIndex}>
          <Tab.List className="flex flex-wrap gap-1 rounded-t-xl bg-blue-900/20 p-1">
            {tabs.map(tab => (
              <Tab
                key={tab.name}
                className={({ selected }) =>
                  classNames(
                    'rounded-lg py-2.5 px-3 text-sm font-medium leading-5',
                    'ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
                    selected
                      ? 'bg-white text-blue-700 shadow'
                      : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
                  )
                }
              >
                <div className="flex items-center gap-1.5">
                  <tab.icon className="h-4 w-4" />
                  <span>{tab.name}</span>
                </div>
              </Tab>
            ))}
          </Tab.List>
          <Tab.Panels className="mt-0">
            {tabs.map((tab, i) => (
              <Tab.Panel
                key={i}
                className="rounded-b-xl bg-white p-6 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2"
              >
                {tab.render()}
              </Tab.Panel>
            ))}
          </Tab.Panels>
        </Tab.Group>
      </div>
    </div>
  )
}

export default AdminPanel
