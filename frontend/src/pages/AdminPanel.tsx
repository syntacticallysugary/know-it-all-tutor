import React, { useState } from 'react'
import { Tab } from '@headlessui/react'
import { CloudArrowUpIcon, ClockIcon, UserGroupIcon } from '@heroicons/react/24/outline'
import BatchUpload from '../components/Admin/BatchUpload'
import UploadHistory from '../components/Admin/UploadHistory'
import PendingUsers from '../components/Admin/PendingUsers'

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

const AdminPanel = () => {
  const [selectedIndex, setSelectedIndex] = useState(0)

  const tabs = [
    {
      name: 'Pending Registrations',
      icon: UserGroupIcon,
      component: PendingUsers,
    },
    {
      name: 'Batch Upload',
      icon: CloudArrowUpIcon,
      component: BatchUpload,
    },
    {
      name: 'Upload History',
      icon: ClockIcon,
      component: UploadHistory,
    },
  ]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Admin Panel</h1>
        <p className="page-subtitle">
          Manage batch uploads and system administration.
        </p>
      </div>
      
      <div className="card p-0">
        <Tab.Group selectedIndex={selectedIndex} onChange={setSelectedIndex}>
          <Tab.List className="flex space-x-1 rounded-t-xl bg-blue-900/20 p-1">
            {tabs.map((tab, index) => (
              <Tab
                key={tab.name}
                className={({ selected }) =>
                  classNames(
                    'w-full rounded-lg py-2.5 text-sm font-medium leading-5',
                    'ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
                    selected
                      ? 'bg-white text-blue-700 shadow'
                      : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
                  )
                }
              >
                <div className="flex items-center justify-center space-x-2">
                  <tab.icon className="h-5 w-5" />
                  <span>{tab.name}</span>
                </div>
              </Tab>
            ))}
          </Tab.List>
          <Tab.Panels className="mt-0">
            {tabs.map((tab, index) => (
              <Tab.Panel
                key={index}
                className="rounded-b-xl bg-white p-6 ring-white ring-opacity-60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2"
              >
                <tab.component />
              </Tab.Panel>
            ))}
          </Tab.Panels>
        </Tab.Group>
      </div>
    </div>
  )
}

export default AdminPanel
