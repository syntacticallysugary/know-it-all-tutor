import React, { useState } from 'react'
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import FileUpload from './FileUpload'
import ValidationResults from './ValidationResults'
import { apiClient, BatchValidationResult, BatchUploadResult } from '../../services/api'

type UploadStep = 'select' | 'validate' | 'upload' | 'complete' | 'error'

interface UploadState {
  step: UploadStep
  file: File | null
  validationResults: BatchValidationResult | null
  uploadResults: BatchUploadResult | null
  error: string | null
  isProcessing: boolean
  overwrite: boolean
}

const BatchUpload: React.FC = () => {
  const [state, setState] = useState<UploadState>({
    step: 'select',
    file: null,
    validationResults: null,
    uploadResults: null,
    error: null,
    isProcessing: false,
    overwrite: false,
  })

  const handleFileSelect = async (file: File) => {
    setState(prev => ({ ...prev, file, error: null }))
    
    try {
      // Parse and validate the JSON file
      const text = await file.text()
      const jsonData = JSON.parse(text)
      
      setState(prev => ({ ...prev, isProcessing: true, step: 'validate' }))
      
      // Validate with the backend
      const validationResults = await apiClient.validateBatchUpload(jsonData)
      
      setState(prev => ({
        ...prev,
        validationResults,
        isProcessing: false,
        step: 'validate'
      }))
    } catch (error) {
      let errorMessage = 'Failed to process file'
      
      if (error instanceof SyntaxError) {
        errorMessage = 'Invalid JSON file. Please check the file format.'
      } else if (error instanceof Error) {
        errorMessage = error.message
      }
      
      setState(prev => ({
        ...prev,
        error: errorMessage,
        step: 'error',
        isProcessing: false
      }))
    }
  }

  const handleFileRemove = () => {
    setState({
      step: 'select',
      file: null,
      validationResults: null,
      uploadResults: null,
      error: null,
      isProcessing: false,
      overwrite: false,
    })
  }

  const handleProceedWithUpload = async () => {
    if (!state.file || !state.validationResults) return
    
    try {
      setState(prev => ({ ...prev, isProcessing: true, step: 'upload' }))
      
      const text = await state.file.text()
      const jsonData = JSON.parse(text)
      
      const uploadResults = await apiClient.processBatchUpload(jsonData, state.overwrite)
      
      setState(prev => ({
        ...prev,
        uploadResults,
        isProcessing: false,
        step: 'complete'
      }))
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      setState(prev => ({
        ...prev,
        error: errorMessage,
        step: 'error',
        isProcessing: false
      }))
    }
  }

  const handleCancelValidation = () => {
    setState(prev => ({
      ...prev,
      step: 'select',
      validationResults: null,
      error: null
    }))
  }

  const handleStartOver = () => {
    setState({
      step: 'select',
      file: null,
      validationResults: null,
      uploadResults: null,
      error: null,
      isProcessing: false,
      overwrite: false,
    })
  }

  const renderStepIndicator = () => {
    const steps = [
      { id: 'select', name: 'Select File', completed: ['validate', 'upload', 'complete'].includes(state.step) },
      { id: 'validate', name: 'Validate', completed: ['upload', 'complete'].includes(state.step) },
      { id: 'upload', name: 'Upload', completed: state.step === 'complete' }
    ]

    return (
      <div className="mb-8">
        <nav aria-label="Progress">
          <ol className="flex items-center">
            {steps.map((step, stepIdx) => (
              <li key={step.id} className={`${stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''} relative`}>
                <div className="flex items-center">
                  <div className={`
                    flex h-8 w-8 items-center justify-center rounded-full border-2
                    ${step.completed 
                      ? 'border-blue-600 bg-blue-600' 
                      : state.step === step.id
                        ? 'border-blue-600 bg-white'
                        : 'border-gray-300 bg-white'
                    }
                  `}>
                    {step.completed ? (
                      <CheckCircleIcon className="h-5 w-5 text-white" />
                    ) : (
                      <span className={`text-sm font-medium ${
                        state.step === step.id ? 'text-blue-600' : 'text-gray-500'
                      }`}>
                        {stepIdx + 1}
                      </span>
                    )}
                  </div>
                  <span className={`ml-3 text-sm font-medium ${
                    step.completed || state.step === step.id ? 'text-gray-900' : 'text-gray-500'
                  }`}>
                    {step.name}
                  </span>
                </div>
                {stepIdx !== steps.length - 1 && (
                  <div className="absolute top-4 left-4 -ml-px mt-0.5 h-full w-0.5 bg-gray-300" />
                )}
              </li>
            ))}
          </ol>
        </nav>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Batch Upload</h2>
        <p className="mt-1 text-sm text-gray-600">
          Upload JSON files to add multiple domains and terms to the system.
        </p>
      </div>

      {renderStepIndicator()}

      <div className="bg-white shadow rounded-lg p-6">
        {state.step === 'select' && (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Select JSON File</h3>
            <FileUpload
              onFileSelect={handleFileSelect}
              selectedFile={state.file}
              onFileRemove={handleFileRemove}
              disabled={state.isProcessing}
            />
            
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
              <h4 className="text-sm font-medium text-blue-800">File Format Requirements</h4>
              <ul className="mt-2 text-sm text-blue-700 list-disc list-inside space-y-1">
                <li>File must be in JSON format</li>
                <li>Must include batch_metadata with filename, version, created_date, total_domains, and total_terms</li>
                <li>Must include domains array with at least one domain</li>
                <li>Each domain must have name, description, and terms array</li>
                <li>Each term must have term and definition fields</li>
              </ul>
            </div>
          </div>
        )}

        {state.step === 'validate' && state.validationResults && (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Validation Results</h3>
            <ValidationResults
              results={state.validationResults}
              onProceed={handleProceedWithUpload}
              onCancel={handleCancelValidation}
              isProcessing={state.isProcessing}
              overwrite={state.overwrite}
              onOverwriteChange={(v) => setState(prev => ({ ...prev, overwrite: v }))}
            />
          </div>
        )}

        {state.step === 'upload' && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <h3 className="mt-4 text-lg font-medium text-gray-900">Processing Upload</h3>
            <p className="mt-2 text-sm text-gray-600">
              Please wait while we process your batch upload...
            </p>
          </div>
        )}

        {state.step === 'complete' && state.uploadResults && (
          <div className="text-center py-8">
            <CheckCircleIcon className="mx-auto h-12 w-12 text-green-500" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Upload Complete!</h3>
            <div className="mt-4 space-y-2">
              {state.uploadResults.domains_created > 0 && (
                <p className="text-sm text-gray-600">
                  Created <strong>{state.uploadResults.domains_created}</strong> new domain{state.uploadResults.domains_created !== 1 ? 's' : ''}.
                </p>
              )}
              {state.uploadResults.terms_created > 0 && (
                <p className="text-sm text-gray-600">
                  Added <strong>{state.uploadResults.terms_created}</strong> new term{state.uploadResults.terms_created !== 1 ? 's' : ''}.
                </p>
              )}
              {state.uploadResults.terms_updated > 0 && (
                <p className="text-sm text-blue-600">
                  Updated <strong>{state.uploadResults.terms_updated}</strong> existing term{state.uploadResults.terms_updated !== 1 ? 's' : ''}.
                </p>
              )}
              {state.uploadResults.domains_skipped > 0 && !state.overwrite && (
                <p className="text-sm text-yellow-600">
                  Skipped <strong>{state.uploadResults.domains_skipped}</strong> existing domain{state.uploadResults.domains_skipped !== 1 ? 's' : ''} (no overwrite).
                </p>
              )}
            </div>
            <div className="mt-6">
              <button
                onClick={handleStartOver}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
              >
                Upload Another File
              </button>
            </div>
          </div>
        )}

        {state.step === 'error' && (
          <div className="text-center py-8">
            <XCircleIcon className="mx-auto h-12 w-12 text-red-500" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Upload Failed</h3>
            <p className="mt-2 text-sm text-red-600">{state.error}</p>
            <div className="mt-6">
              <button
                onClick={handleStartOver}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BatchUpload