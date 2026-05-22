import React, { useState } from 'react'
import { Tab } from '@headlessui/react'
import { SparklesIcon, QueueListIcon, DocumentTextIcon } from '@heroicons/react/24/outline'
import DomainGenDefine from '../components/Admin/DomainGenDefine'
import DomainGenQueue from '../components/Admin/DomainGenQueue'
import DomainGenReview from '../components/Admin/DomainGenReview'
import type { DomainGenJob } from '../services/api'

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

const GenerateDomain = () => {
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [latestJob, setLatestJob] = useState<DomainGenJob | null>(null)
  const [reviewJobId, setReviewJobId] = useState<string | null>(null)

  const handleJobCreated = (job: DomainGenJob) => {
    setLatestJob(job)
    setSelectedIndex(1)
  }

  const handleSelectReview = (jobId: string) => {
    setReviewJobId(jobId)
    setSelectedIndex(2)
  }

  const tabs = [
    { name: 'Define',  icon: SparklesIcon,      render: () => <DomainGenDefine onJobCreated={handleJobCreated} /> },
    { name: 'Queue',   icon: QueueListIcon,      render: () => <DomainGenQueue newJob={latestJob} onSelectJob={handleSelectReview} /> },
    { name: 'Review',  icon: DocumentTextIcon,   render: () => <DomainGenReview jobId={reviewJobId} /> },
  ]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Generate Domain</h1>
        <p className="page-subtitle">
          Request a new quiz domain. The LAN worker researches and generates terms overnight.
        </p>
      </div>

      <div className="card p-0">
        <Tab.Group selectedIndex={selectedIndex} onChange={setSelectedIndex}>
          <Tab.List className="flex gap-1 rounded-t-xl bg-blue-900/20 p-1">
            {tabs.map(tab => (
              <Tab
                key={tab.name}
                className={({ selected }) =>
                  classNames(
                    'rounded-lg py-2.5 px-4 text-sm font-medium leading-5',
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
          <Tab.Panels>
            {tabs.map((tab, i) => (
              <Tab.Panel
                key={i}
                className="rounded-b-xl bg-white p-6 focus:outline-none"
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

export default GenerateDomain
