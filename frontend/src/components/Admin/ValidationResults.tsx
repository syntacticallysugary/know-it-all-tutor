import React from 'react'
import { CheckCircleIcon, ExclamationTriangleIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import { BatchValidationResult } from '../../services/api'

interface ValidationResultsProps {
  results: BatchValidationResult
  onProceed: () => void
  onCancel: () => void
  isProcessing?: boolean
  overwrite?: boolean
  onOverwriteChange?: (value: boolean) => void
}

const ValidationResults: React.FC<ValidationResultsProps> = ({
  results,
  onProceed,
  onCancel,
  isProcessing = false,
  overwrite = false,
  onOverwriteChange,
}) => {
  return (
    <div className="space-y-6">
      {/* Validation Status */}
      <div className="flex items-center space-x-3">
        <CheckCircleIcon className="h-8 w-8 text-green-500" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Validation Successful</h3>
          <p className="text-sm text-gray-600">Your file has been validated and is ready for upload.</p>
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-blue-600">{results.total_domains}</span>
              </div>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-blue-900">Domains</p>
              <p className="text-xs text-blue-600">Will be created</p>
            </div>
          </div>
        </div>

        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-green-600">{results.total_terms}</span>
              </div>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-green-900">Terms</p>
              <p className="text-xs text-green-600">Will be created</p>
            </div>
          </div>
        </div>
      </div>

      {/* Warnings */}
      {results.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
            <div className="ml-3">
              <h4 className="text-sm font-medium text-yellow-800">Warnings</h4>
              <div className="mt-2 text-sm text-yellow-700">
                <ul className="list-disc list-inside space-y-1">
                  {results.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Existing Duplicates */}
      {results.existing_duplicates.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex">
            <InformationCircleIcon className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="ml-3 w-full">
              <h4 className="text-sm font-medium text-blue-800">Existing Domains</h4>
              <p className="mt-1 text-sm text-blue-700">
                The following {results.existing_duplicates.length} domain{results.existing_duplicates.length !== 1 ? 's' : ''} already exist:
              </p>
              <div className="mt-2">
                <ul className="text-sm text-blue-700 space-y-1">
                  {results.existing_duplicates.map((domain, index) => (
                    <li key={index} className="flex items-center">
                      <span className="w-2 h-2 bg-blue-400 rounded-full mr-2 flex-shrink-0"></span>
                      {domain}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Overwrite toggle */}
              <div className="mt-4 pt-3 border-t border-blue-200">
                <label className="flex items-start gap-3 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={overwrite}
                    onChange={(e) => onOverwriteChange?.(e.target.checked)}
                    disabled={isProcessing}
                    className="mt-0.5 h-4 w-4 rounded border-blue-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                  />
                  <span className="text-sm text-blue-800">
                    <span className="font-medium">Overwrite existing terms</span>
                    <span className="block text-blue-600 font-normal">
                      {overwrite
                        ? 'Existing term definitions will be replaced. New terms will be added.'
                        : 'Existing terms will be skipped. Only new terms will be added.'}
                    </span>
                  </span>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          onClick={onCancel}
          disabled={isProcessing}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={onProceed}
          disabled={isProcessing}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center"
        >
          {isProcessing ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </>
          ) : (
            overwrite && results.existing_duplicates.length > 0
              ? 'Proceed with Overwrite'
              : 'Proceed with Upload'
          )}
        </button>
      </div>
    </div>
  )
}

export default ValidationResults